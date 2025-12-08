"""
Chatbot Backend - FastAPI service for chat interface
Handles: chat history, routing to RAG, light LLM for classification, authentication
"""
import os
from typing import Optional, List
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uvicorn
from langchain_groq import ChatGroq

import database as db
import auth

load_dotenv()

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://127.0.0.1:8001")
MATERIAL_SERVICE_URL = os.getenv("MATERIAL_SERVICE_URL", "http://127.0.0.1:8080")

# Light LLM for routing/classification (fast, small model)
router_llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model_name="llama-3.1-8b-instant",  # Fast model for routing
    temperature=0,
    max_tokens=100,
)

app = FastAPI(
    title="Chatbot Backend",
    description="Backend for educational chatbot with RAG integration",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    user_id: str = "anonymous"
    subject_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: int
    message: str
    sources: Optional[List[dict]] = None
    request_type: str  # "question", "generate_test", "generate_exercise", "general"


class ConversationCreate(BaseModel):
    user_id: str = "anonymous"
    subject_id: Optional[str] = None
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: int
    title: str
    subject_id: Optional[str]
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    sources: Optional[List[dict]]
    created_at: str


# --- Request Classification ---

def classify_request(message: str) -> str:
    """Classify user request using light LLM"""
    prompt = f"""Clasifica la siguiente petición del estudiante en una de estas categorías:
- "material_info": si pregunta qué material/asignaturas/temas hay disponibles
- "academic_summary": si pide RESUMIR un artículo, documento, tema o material de estudio
- "generate_questions": si pide generar PREGUNTAS de comprensión o análisis (no test de evaluación)
- "generate_test": si pide crear un TEST/EXAMEN con opciones múltiples para evaluarse
- "generate_exercise": si pide crear EJERCICIOS o PROBLEMAS para practicar
- "question": si hace una pregunta específica sobre el contenido o pide explicación
- "general": saludos, despedidas, o cosas no relacionadas con el estudio

Responde SOLO con la categoría, sin explicación.

Petición: "{message}"

Categoría:"""
    
    response = router_llm.invoke(prompt)
    category = response.content.strip().lower().replace('"', '')
    
    valid_categories = ["material_info", "academic_summary", "generate_questions", "generate_test", "generate_exercise", "question", "general"]
    if category not in valid_categories:
        category = "question"  # Default
    
    return category


# --- RAG Integration ---

async def forward_to_rag(question: str, subject_id: Optional[str] = None, conversation_history: Optional[List[dict]] = None) -> dict:
    """Forward question to RAG service with conversation history for context"""
    try:
        # Build context from conversation history (last 6 messages max for context)
        context_messages = []
        if conversation_history:
            recent_history = conversation_history[-6:]  # Last 6 messages
            for msg in recent_history:
                role = "Usuario" if msg.get("role") == "user" else "Asistente"
                context_messages.append(f"{role}: {msg.get('content', '')[:500]}")  # Limit each message
        
        # Create enhanced question with context
        if context_messages:
            context_str = "\n".join(context_messages)
            enhanced_question = f"""Historial de la conversación:
{context_str}

Pregunta actual del usuario: {question}

IMPORTANTE: Responde considerando el contexto de la conversación anterior. Si el usuario pide respuestas de un test que generaste antes, proporciónalas."""
        else:
            enhanced_question = question
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/api/chat",
                json={"question": enhanced_question, "subject_id": subject_id}
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "answer": "Error al conectar con el servicio RAG"}
    except Exception as e:
        return {"status": "error", "answer": f"Error de conexión: {str(e)}"}


async def get_material_info(subject_id: Optional[str] = None) -> dict:
    """Get actual material info from Material API"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{MATERIAL_SERVICE_URL}/api/material")
            if response.status_code == 200:
                materials = response.json()
                
                # Filter by subject if specified
                if subject_id:
                    materials = [m for m in materials if m.get("subject_id") == subject_id]
                
                if not materials:
                    if subject_id:
                        return {"answer": f"No hay materiales disponibles para la asignatura '{subject_id}'. Por favor, sube material primero."}
                    else:
                        return {"answer": "No hay materiales disponibles. Por favor, sube material desde el módulo de materiales."}
                
                # Build response with real material info
                subjects = {}
                for m in materials:
                    sid = m.get("subject_id", "sin_asignar")
                    if sid not in subjects:
                        subjects[sid] = []
                    subjects[sid].append(m.get("title", m.get("original_name", "Sin título")))
                
                response_text = "📚 **Material disponible:**\n\n"
                for sid, titles in subjects.items():
                    response_text += f"**{sid}:**\n"
                    for title in titles:
                        response_text += f"  • {title}\n"
                    response_text += "\n"
                
                return {"answer": response_text, "sources": None}
            else:
                return {"answer": "Error al obtener materiales del servidor."}
    except Exception as e:
        return {"answer": f"Error de conexión con el servidor de materiales: {str(e)}"}


async def request_test_generation(subject_id: str, topic: str, conversation_history: Optional[List[dict]] = None) -> dict:
    """Request RAG to generate a test"""
    question = f"""Genera un test de evaluación sobre "{topic}" con el siguiente formato:

## 📝 TEST DE EVALUACIÓN

### Preguntas de Opción Múltiple

**Pregunta 1:** [Enunciado de la pregunta]

a) [Opción A]
b) [Opción B]
c) [Opción C]
d) [Opción D]

**Pregunta 2:** [Enunciado]

a) [Opción A]
b) [Opción B]
c) [Opción C]
d) [Opción D]

(Genera 5 preguntas de opción múltiple)

### Preguntas de Verdadero o Falso

**Pregunta 6:** [Afirmación] (V/F)

**Pregunta 7:** [Afirmación] (V/F)

### Pregunta de Desarrollo

**Pregunta 8:** [Pregunta abierta que requiera explicación breve]

---
*Las respuestas estarán disponibles cuando las solicites.*

IMPORTANTE: NO incluyas las respuestas en este test. El alumno quiere realizar el test primero. Solo proporciona las respuestas si el alumno lo pide explícitamente después."""
    
    return await forward_to_rag(question, subject_id, conversation_history)


async def request_exercise_generation(subject_id: str, topic: str, conversation_history: Optional[List[dict]] = None) -> dict:
    """Request RAG to generate exercises"""
    question = f"""Genera ejercicios prácticos sobre "{topic}" con las siguientes características:
- 3 ejercicios de dificultad progresiva (fácil, medio, difícil)
- Cada ejercicio debe incluir enunciado claro
- Incluye las soluciones al final

Los ejercicios deben ser similares a los que aparecen en el material."""
    
    return await forward_to_rag(question, subject_id, conversation_history)


async def request_academic_summary(subject_id: str, topic: str, conversation_history: Optional[List[dict]] = None) -> dict:
    """Request RAG to generate a study summary"""
    question = f"""Resume el material sobre "{topic}" como unos APUNTES DE CLASE claros y útiles para estudiar.

## 📖 Introducción
Explica brevemente de qué trata el tema (2-3 oraciones).

## 📝 Conceptos Clave

- **[Término 1]**: Definición clara y sencilla.

- **[Término 2]**: Definición clara y sencilla.

- **[Término 3]**: Definición clara y sencilla.

(Añade todos los conceptos importantes del material)

## 🔍 Ideas Principales

1. **[Idea 1]**: Explicación breve.

2. **[Idea 2]**: Explicación breve.

3. **[Idea 3]**: Explicación breve.

## 💡 Para recordar
Los puntos más importantes que hay que saber para el examen.

INSTRUCCIONES:
- Usa un lenguaje SENCILLO, como si explicaras a un compañero.
- Cada punto en su PROPIA LÍNEA.
- Usa **negritas** para términos clave.
- NO uses formato de TFG ni de artículo científico.
- El objetivo es ayudar a ESTUDIAR, no impresionar."""

    return await forward_to_rag(question, subject_id, conversation_history)


async def request_question_generation(subject_id: str, topic: str, conversation_history: Optional[List[dict]] = None) -> dict:
    """Request RAG to generate comprehension questions using structured reasoning"""
    question = f"""Analiza el material sobre "{topic}" y genera preguntas esenciales de comprensión.

## Instrucciones de Análisis
Usa técnicas de razonamiento estructurado:
✅ Cadena de Pensamiento - Desglosa las ideas en secuencia lógica
✅ Árbol de Pensamiento - Explora múltiples perspectivas
✅ Análisis Comparativo - Evalúa fortalezas y debilidades

## Genera 5 Preguntas Esenciales
Cada pregunta debe:
✅ Abordar el tema central
✅ Identificar ideas y evidencia clave
✅ Destacar hechos importantes
✅ Revelar el propósito del autor
✅ Explorar implicaciones y conclusiones

## Para cada pregunta, proporciona:

**Pregunta [N]: [Enunciado]**

**Respuesta con razonamiento estructurado:**
- Explicación paso a paso
- Múltiples perspectivas (si aplica)
- Ejemplos o casos prácticos
- Extractos relevantes del material

---

Genera las 5 preguntas con sus respuestas detalladas."""

    return await forward_to_rag(question, subject_id, conversation_history)


# --- Security ---

security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[str]:
    """Get current user from JWT token, returns None if not authenticated"""
    if credentials is None:
        return None
    token = credentials.credentials
    username = auth.verify_token(token)
    return username


async def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Require authentication, raises 401 if not authenticated"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="No autorizado")
    token = credentials.credentials
    username = auth.verify_token(token)
    if username is None:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return username


# --- Auth Endpoints ---

@app.post("/api/auth/register", response_model=auth.UserResponse)
def register(user: auth.UserCreate):
    """Register a new user"""
    user_id = auth.create_user(user.username, user.password, user.email)
    if user_id is None:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    user_data = auth.get_user_by_username(user.username)
    return user_data


@app.post("/api/auth/login", response_model=auth.Token)
def login(user: auth.UserLogin):
    """Login and get JWT token"""
    authenticated_user = auth.authenticate_user(user.username, user.password)
    if not authenticated_user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=auth.UserResponse)
def get_me(username: str = Depends(require_auth)):
    """Get current user info"""
    user = auth.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


# --- API Endpoints ---

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Chatbot Backend",
        "endpoints": ["/api/auth/register", "/api/auth/login", "/api/chat", "/api/conversations"]
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint - handles all user messages"""
    
    # Create or get conversation
    if request.conversation_id is None:
        conversation_id = db.create_conversation(
            user_id=request.user_id,
            subject_id=request.subject_id,
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message
        )
    else:
        conversation_id = request.conversation_id
        # Verify conversation exists
        conv = db.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    # Save user message
    db.add_message(conversation_id, "user", request.message)
    
    # Get conversation history for context
    conversation_history = db.get_messages(conversation_id)
    
    # Classify request type
    request_type = classify_request(request.message)
    
    # Process based on type
    if request_type == "material_info":
        result = await get_material_info(request.subject_id)
    elif request_type == "academic_summary":
        result = await request_academic_summary(
            request.subject_id or "general",
            request.message,
            conversation_history
        )
    elif request_type == "generate_questions":
        result = await request_question_generation(
            request.subject_id or "general",
            request.message,
            conversation_history
        )
    elif request_type == "generate_test":
        result = await request_test_generation(
            request.subject_id or "general",
            request.message,
            conversation_history
        )
    elif request_type == "generate_exercise":
        result = await request_exercise_generation(
            request.subject_id or "general", 
            request.message,
            conversation_history
        )
    elif request_type == "question":
        result = await forward_to_rag(request.message, request.subject_id, conversation_history)
    else:  # general
        # Handle with light LLM for general conversation
        response = router_llm.invoke(
            f"Eres un asistente educativo amable. Responde brevemente: {request.message}"
        )
        result = {"answer": response.content, "sources": None}
    
    # Save assistant response
    answer = result.get("answer", "No pude procesar tu solicitud")
    sources = result.get("sources")
    db.add_message(conversation_id, "assistant", answer, sources)
    
    return ChatResponse(
        conversation_id=conversation_id,
        message=answer,
        sources=sources,
        request_type=request_type
    )


@app.get("/api/conversations", response_model=List[ConversationResponse])
def get_conversations(user_id: str = "anonymous"):
    """Get all conversations for a user"""
    conversations = db.get_conversations(user_id)
    return conversations


@app.post("/api/conversations", response_model=ConversationResponse)
def create_conversation(request: ConversationCreate):
    """Create a new conversation"""
    conv_id = db.create_conversation(
        user_id=request.user_id,
        subject_id=request.subject_id,
        title=request.title or "Nueva conversación"
    )
    conv = db.get_conversation(conv_id)
    return conv


@app.get("/api/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def get_messages(conversation_id: int):
    """Get all messages in a conversation"""
    messages = db.get_messages(conversation_id)
    if not messages:
        conv = db.get_conversation(conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return messages


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(conversation_id: int):
    """Delete a conversation and its messages"""
    conv = db.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    db.delete_conversation(conversation_id)
    return {"status": "ok", "message": "Conversación eliminada"}


if __name__ == "__main__":
    print("🤖 Iniciando Chatbot Backend en http://127.0.0.1:8002")
    print("📚 Documentación: http://127.0.0.1:8002/docs")
    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True)
