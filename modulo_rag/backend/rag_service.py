"""
RAG Service - Servicio de Retrieval Augmented Generation
Usa Langchain + Groq + ChromaDB para responder preguntas basadas en documentos
"""
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.documents import Document

# OCR imports
import easyocr
import fitz  # pymupdf - no external dependencies needed
import numpy as np
from PIL import Image
import io

load_dotenv()

# Configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHROMA_DIR = Path(__file__).parent / "chroma_db"

# Modelo de embeddings gratuito (local) - mejor modelo
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

# Modelo LLM en Groq - modelo disponible
LLM_MODEL = "llama-3.3-70b-versatile"

# OCR Reader (lazy load to avoid memory issues at startup)
_ocr_reader = None

def get_ocr_reader():
    """Lazy load OCR reader"""
    global _ocr_reader
    if _ocr_reader is None:
        print("🔄 Cargando EasyOCR (primera vez, puede tardar)...")
        _ocr_reader = easyocr.Reader(['es', 'en'], gpu=False)
        print("✅ EasyOCR cargado")
    return _ocr_reader


def extract_text_with_ocr(pdf_path: str) -> str:
    """Extract text from image-based PDF using OCR"""
    print(f"🔍 Aplicando OCR a: {pdf_path}")
    reader = get_ocr_reader()
    
    try:
        # Open PDF with pymupdf
        doc = fitz.open(pdf_path)
        all_text = []
        
        for i, page in enumerate(doc):
            print(f"  📄 Procesando página {i+1}/{len(doc)}...")
            # Render page to image
            mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image then to numpy array
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img_array = np.array(img)
            
            # Run OCR
            results = reader.readtext(img_array)
            # Extract text
            page_text = " ".join([result[1] for result in results])
            all_text.append(page_text)
        
        doc.close()
        full_text = "\n\n".join(all_text)
        print(f"✅ OCR completado: {len(full_text)} caracteres extraídos")
        return full_text
    except Exception as e:
        print(f"❌ Error en OCR: {e}")
        return ""


class RAGService:
    """Servicio RAG para procesar documentos y responder preguntas"""
    
    def __init__(self):
        print("🔄 Inicializando RAG Service...")
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        # Chunks más grandes para mejor contexto
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=400,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.vector_store: Optional[Chroma] = None
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=LLM_MODEL,
            temperature=0.2,  # Más determinístico
            max_tokens=2048,
        )
        self._load_existing_index()
        print("✅ RAG Service inicializado")
    
    def _load_existing_index(self):
        """Carga el índice existente si existe"""
        if CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir()):
            self.vector_store = Chroma(
                persist_directory=str(CHROMA_DIR),
                embedding_function=self.embeddings,
            )
            print(f"✓ Índice cargado desde {CHROMA_DIR}")
        else:
            print("⚠ No hay índice existente. Usa /api/index para crear uno.")
    
    def load_document(self, file_path: str) -> List:
        """Carga un documento según su extensión. Usa OCR si es un PDF de imagen."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            # Try normal text extraction first
            loader = PyPDFLoader(str(path))
            docs = loader.load()
            
            # Check if we got meaningful text
            total_text = "".join([doc.page_content for doc in docs])
            text_length = len(total_text.strip())
            
            # If very little text, probably an image-based PDF - use OCR
            if text_length < 100:
                print(f"⚠ PDF con poco texto ({text_length} chars), intentando OCR...")
                ocr_text = extract_text_with_ocr(str(path))
                if ocr_text:
                    # Create a document from OCR text
                    return [Document(
                        page_content=ocr_text,
                        metadata={"source": str(path), "ocr": True}
                    )]
            
            return docs
        elif ext in [".txt", ".md", ".py", ".js", ".ts", ".go", ".java", ".c", ".cpp", ".h"]:
            loader = TextLoader(str(path), encoding="utf-8")
        else:
            loader = TextLoader(str(path), encoding="utf-8")
        
        return loader.load()
    
    def index_documents(self, file_paths: List[str], subject_id: str) -> dict:
        """Indexa una lista de documentos para una asignatura"""
        all_documents = []
        errors = []
        
        for file_path in file_paths:
            try:
                docs = self.load_document(file_path)
                for doc in docs:
                    doc.metadata["subject_id"] = subject_id
                    doc.metadata["source_file"] = file_path
                all_documents.extend(docs)
            except Exception as e:
                errors.append({"file": file_path, "error": str(e)})
        
        if not all_documents:
            return {"status": "error", "message": "No se pudo cargar ningún documento", "errors": errors}
        
        chunks = self.text_splitter.split_documents(all_documents)
        
        # Borrar índice anterior si existe para reindexar limpio
        if self.vector_store is not None:
            try:
                # Borrar documentos de esta asignatura
                self.vector_store._collection.delete(
                    where={"subject_id": subject_id}
                )
            except:
                pass
        
        if self.vector_store is None:
            self.vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=str(CHROMA_DIR),
            )
        else:
            self.vector_store.add_documents(chunks)
        
        return {
            "status": "ok",
            "documents_processed": len(file_paths) - len(errors),
            "chunks_created": len(chunks),
            "errors": errors if errors else None,
        }
    
    def query(self, question: str, subject_id: Optional[str] = None) -> dict:
        """Responde una pregunta usando RAG"""
        if self.vector_store is None:
            return {
                "status": "error",
                "message": "No hay documentos indexados. Usa /api/index primero."
            }
        
        # Buscar más documentos relevantes
        search_kwargs = {"k": 8}  # Aumentado de 4 a 8
        if subject_id:
            search_kwargs["filter"] = {"subject_id": subject_id}
        
        docs = self.vector_store.similarity_search(question, **search_kwargs)
        
        if not docs:
            return {
                "status": "ok",
                "answer": "No encontré información relevante en el material disponible.",
                "sources": []
            }
        
        # Construir contexto con más información
        context_parts = []
        for i, doc in enumerate(docs, 1):
            context_parts.append(f"[Fragmento {i}]\n{doc.page_content}")
        context = "\n\n---\n\n".join(context_parts)
        
        # Prompt anti-alucinación con modos específicos
        prompt = f"""Eres un asistente académico especializado en responder usando EXCLUSIVAMENTE la información del contexto RAG (apuntes, PDFs o fragmentos entregados). 
Está TERMINANTEMENTE PROHIBIDO inventar datos, expandir teoría que no aparece o usar conocimientos externos.

---------------------------------------------------------
REGLAS GENERALES (siempre obligatorias)
---------------------------------------------------------
1. Usa SOLO la información del contexto. Si algo no está, responde literalmente: 
   "No aparece en los documentos proporcionados."
2. Mantén la terminología EXACTA del material original.
3. Si hay definiciones, listas, fórmulas o pasos, respétalos sin modificarlos.
4. Si el contexto es ambiguo, incompleto o contradictorio, indícalo explícitamente.
5. Sé claro, ordenado y conciso. Nada de texto genérico.
6. Justifica siempre usando frases del contexto cuando sea pertinente.

---------------------------------------------------------
MODOS DE RESPUESTA (según lo que pida el usuario)
---------------------------------------------------------

### 1) RESUMEN
Si el usuario pide "resumen", "sintetiza", "resume el tema X", etc.:
- Produce:
  - **Resumen principal** (6–10 líneas)
  - **Conceptos clave** (viñetas, cada una en su propia línea)
  - **Advertencias** (si falta info en el contexto)

### 2) EXPLICACIÓN DE CONCEPTOS
Si el usuario pide "explica", "qué es", "definición", etc.:
1. Definición EXACTA según los apuntes.
2. Interpretación / intuición **solo si aparece en el contexto**.
3. Puntos esenciales (solo los presentes en el texto).
4. Qué NO se menciona o queda ambiguo.

### 3) EJERCICIOS TIPO TEST
Si el usuario pide "resuelve este test", "pregunta tipo test", "respuestas", etc.:
1. Razonamiento paso a paso usando SOLO el contexto.
2. Si no se puede deducir, responde: "El contexto no ofrece suficiente información."
3. Formato final: RESPUESTA: X

### 4) CORRECCIÓN DE RESPUESTAS
Si el usuario pide "corrige", "compara", "evalúa", etc.:
- Indica si coincide con el contexto.
- Qué parte del texto lo confirma o contradice.
- Corrección mínima y fiel al documento.

### 5) CHULETAS / ESQUEMAS
Si el usuario pide "haz un esquema", "chuleta", "apuntes simplificados", etc.:
- Esquema breve con viñetas.
- Conceptos clave y definiciones cortas.
- NO añadas nada que no esté en el documento.

---------------------------------------------------------
REGLA CRÍTICA (ANTI-ALUCINACIÓN)
---------------------------------------------------------
Si la respuesta requiere información que el contexto NO contiene:
→ Indica claramente que NO se puede responder con los datos dados.
→ Nunca intentes completar lo que falta con conocimiento externo.

---------------------------------------------------------
FORMATO
---------------------------------------------------------
- Cada punto de lista en su PROPIA LÍNEA
- Usa guiones (-) para listas
- Usa **negritas** para términos clave
- Deja líneas en blanco entre secciones

---------------------------------------------------------
CONTEXTO (MATERIAL DEL ESTUDIANTE):
{context}
---------------------------------------------------------

PREGUNTA DEL ESTUDIANTE: {question}

RESPUESTA:"""
        
        # Llamar al LLM
        response = self.llm.invoke(prompt)
        
        # Extraer fuentes
        sources = []
        seen_files = set()
        for doc in docs:
            file = doc.metadata.get("source_file", "desconocido")
            if file not in seen_files:
                seen_files.add(file)
                sources.append({
                    "file": file,
                    "subject": doc.metadata.get("subject_id", "desconocido"),
                })
        
        return {
            "status": "ok",
            "answer": response.content,
            "sources": sources,
        }
    
    def get_stats(self) -> dict:
        """Devuelve estadísticas del índice"""
        if self.vector_store is None:
            return {"indexed": False, "count": 0}
        
        collection = self.vector_store._collection
        return {
            "indexed": True,
            "count": collection.count(),
        }


# Instancia global
rag_service = RAGService()
