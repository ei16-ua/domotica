"""
RAG API - FastAPI para el módulo RAG
Puerto: 8001 (separado del backend de materiales en 8080)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx
import uvicorn

from rag_service import rag_service

# Configuración
MATERIAL_BACKEND_URL = "http://127.0.0.1:8080"

app = FastAPI(
    title="RAG Service",
    description="Servicio de Retrieval Augmented Generation para material educativo",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Modelos Pydantic ---

class ChatRequest(BaseModel):
    question: str
    subject_id: Optional[str] = None


class ChatResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    sources: Optional[List[dict]] = None
    message: Optional[str] = None


class IndexRequest(BaseModel):
    subject_id: str


class IndexResponse(BaseModel):
    status: str
    documents_processed: Optional[int] = None
    chunks_created: Optional[int] = None
    errors: Optional[List[dict]] = None
    message: Optional[str] = None


# --- Endpoints ---

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "RAG Service",
        "endpoints": ["/api/chat", "/api/index", "/api/stats"],
    }


@app.get("/api/stats")
def get_stats():
    """Obtiene estadísticas del índice vectorial"""
    return rag_service.get_stats()


@app.post("/api/index", response_model=IndexResponse)
async def index_subject(request: IndexRequest):
    """
    Indexa todos los documentos de una asignatura.
    Obtiene las rutas del backend de materiales y las indexa en ChromaDB.
    """
    subject_id = request.subject_id.strip()
    
    # Obtener rutas de archivos del backend de materiales
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MATERIAL_BACKEND_URL}/api/material/paths/{subject_id}"
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Error al obtener rutas del backend de materiales"
                )
            data = response.json()
            file_paths = data.get("paths", [])
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo conectar al backend de materiales: {str(e)}"
        )
    
    if not file_paths:
        return IndexResponse(
            status="error",
            message=f"No hay materiales para la asignatura '{subject_id}'"
        )
    
    # Convertir rutas relativas a absolutas (relativas al backend de materiales)
    from pathlib import Path
    backend_dir = Path(__file__).parent.parent.parent / "modulo_material" / "backend"
    absolute_paths = []
    for p in file_paths:
        path = Path(p)
        if not path.is_absolute():
            path = backend_dir / p
        absolute_paths.append(str(path))
    
    # Indexar documentos
    result = rag_service.index_documents(absolute_paths, subject_id)
    
    return IndexResponse(**result)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Responde una pregunta usando RAG.
    Opcionalmente filtra por asignatura.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")
    
    result = rag_service.query(
        question=request.question.strip(),
        subject_id=request.subject_id.strip() if request.subject_id else None
    )
    
    return ChatResponse(**result)


@app.post("/api/index/files")
def index_files(file_paths: List[str], subject_id: str):
    """
    Indexa archivos específicos manualmente (sin consultar el backend).
    Útil para testing.
    """
    if not file_paths:
        raise HTTPException(status_code=400, detail="Se requiere al menos un archivo")
    
    result = rag_service.index_documents(file_paths, subject_id)
    return result


if __name__ == "__main__":
    print("🚀 Iniciando RAG Service en http://127.0.0.1:8001")
    print("📚 Documentación: http://127.0.0.1:8001/docs")
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
