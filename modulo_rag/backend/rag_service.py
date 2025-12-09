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
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_groq import ChatGroq
from langchain_core.documents import Document

load_dotenv()

# Configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHROMA_DIR = Path(__file__).parent / "chroma_db"

# Modelo de embeddings gratuito (local)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Modelo LLM en Groq
LLM_MODEL = "llama-3.3-70b-versatile"


class RAGService:
    """Servicio RAG para procesar documentos y responder preguntas"""
    
    def __init__(self):
        print("🔄 Inicializando RAG Service...")
        self.embeddings = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)
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
            temperature=0.2,
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
        """Carga un documento según su extensión"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        
        ext = path.suffix.lower()
        
        if ext == ".pdf":
            loader = PyPDFLoader(str(path))
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
        
        if self.vector_store is not None:
            try:
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
        
        search_kwargs = {"k": 8}
        if subject_id:
            search_kwargs["filter"] = {"subject_id": subject_id}
        
        docs = self.vector_store.similarity_search(question, **search_kwargs)
        
        if not docs:
            return {
                "status": "ok",
                "answer": "No encontré información relevante en el material disponible.",
                "sources": []
            }
        
        context_parts = []
        for i, doc in enumerate(docs, 1):
            context_parts.append(f"[Fragmento {i}]\n{doc.page_content}")
        context = "\n\n---\n\n".join(context_parts)
        
        prompt = f"""Eres un asistente académico especializado en responder usando EXCLUSIVAMENTE la información del contexto RAG (apuntes, PDFs o fragmentos entregados). 
Está TERMINANTEMENTE PROHIBIDO inventar datos, expandir teoría que no aparece o usar conocimientos externos.

REGLAS:
1. Usa SOLO la información del contexto. Si algo no está, responde: "No aparece en los documentos proporcionados."
2. Mantén la terminología EXACTA del material original.
3. Si hay definiciones, listas, fórmulas o pasos, respétalos sin modificarlos.
4. Sé claro, ordenado y conciso.

CONTEXTO:
{context}

PREGUNTA: {question}

RESPUESTA:"""
        
        response = self.llm.invoke(prompt)
        
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
