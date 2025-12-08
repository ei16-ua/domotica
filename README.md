# 🎓 Sistema Educativo con RAG

Sistema modular para gestión de material educativo con chatbot inteligente basado en RAG.

## 📁 Estructura

```
domotica/
├── modulo_material/    # Gestión de archivos (PDFs, videos, etc.)
├── modulo_rag/         # Motor RAG con LLM (genera respuestas)
├── modulo_chatbot/     # Interfaz de chat + historial
└── shared/             # Recursos compartidos
```

---

## 🚀 Cómo Ejecutar

### Requisitos Previos
- Python 3.12+
- Go 1.21+ (con GCC/MinGW para CGO)
- Node.js 18+
- API Key de Groq (https://console.groq.com)

---

### 1️⃣ Módulo Material (Backend Go)

```powershell
cd C:\Users\ikaev\domotica\modulo_material\backend
.\backend.exe
```

**Puerto:** `http://127.0.0.1:8080`

**Funciones:**
- Subir archivos (PDFs, videos, código)
- Listar materiales por asignatura
- Servir metadatos al RAG

---

### 2️⃣ Módulo RAG (Backend Python)

```powershell
cd C:\Users\ikaev\domotica\modulo_rag\backend
.\venv\Scripts\activate
python main.py
```

**Puerto:** `http://127.0.0.1:8001`

**Funciones:**
- Indexar documentos en ChromaDB
- Responder preguntas basadas en material
- Generar tests y ejercicios

**Primera vez:** Crear entorno virtual
```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

---

### 3️⃣ Módulo Chatbot (Backend Python)

```powershell
cd C:\Users\ikaev\domotica\modulo_chatbot\backend
.\venv\Scripts\activate
python main.py
```

**Puerto:** `http://127.0.0.1:8002`

**Funciones:**
- Clasificar peticiones (pregunta/test/ejercicio)
- Guardar historial de conversaciones
- Coordinar con RAG

**Primera vez:** Crear entorno virtual
```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

---

### 4️⃣ Frontend Material (React)

```powershell
cd C:\Users\ikaev\domotica\modulo_material\frontend\app
npm run dev
```

**Puerto:** `http://localhost:5173`

---

### 5️⃣ Frontend Chatbot (React)

```powershell
cd C:\Users\ikaev\domotica\modulo_chatbot\frontend\app
npm run dev -- --port 5174
```

**Puerto:** `http://localhost:5174`

---

## ⚡ Script de Arranque Rápido

Ejecuta todos los servicios:

```powershell
# Terminal 1: Material Backend
cd C:\Users\ikaev\domotica\modulo_material\backend; .\backend.exe

# Terminal 2: RAG Backend
cd C:\Users\ikaev\domotica\modulo_rag\backend; .\venv\Scripts\python main.py

# Terminal 3: Chatbot Backend
cd C:\Users\ikaev\domotica\modulo_chatbot\backend; .\venv\Scripts\python main.py

# Terminal 4: Frontend Material
cd C:\Users\ikaev\domotica\modulo_material\frontend\app; npm run dev

# Terminal 5: Frontend Chatbot
cd C:\Users\ikaev\domotica\modulo_chatbot\frontend\app; npm run dev -- --port 5174
```

---

## 🔧 Configuración

### API Key de Groq
Edita los archivos `.env` en cada backend:
- `modulo_rag/backend/.env`
- `modulo_chatbot/backend/.env`

```
GROQ_API_KEY=gsk_tu_api_key_aqui
```

### JWT Secret (Chatbot)
Edita `modulo_chatbot/backend/.env`:
```
JWT_SECRET_KEY=una-clave-secreta-muy-larga-y-segura
```

---

## 🔐 Autenticación

El módulo chatbot tiene sistema de autenticación JWT:

1. **Registrar usuario**: `POST /api/auth/register`
2. **Iniciar sesión**: `POST /api/auth/login` → devuelve token
3. **Endpoints protegidos**: Usar header `Authorization: Bearer <token>`

---

## 📊 Puertos

| Servicio | Puerto | Tipo |
|----------|--------|------|
| Material Backend | 8080 | Go |
| RAG Backend | 8001 | Python |
| Chatbot Backend | 8002 | Python |
| Frontend Material | 5173 | React |
| Frontend Chatbot | 5174 | React |

---

## 🗄️ Bases de Datos

| BD | Ubicación | Contenido |
|----|-----------|-----------|
| materials.db | modulo_material/backend/ | Metadatos de archivos |
| predictions.db | modulo_rag/backend/ | Predicciones de alumnos |
| chat_history.db | modulo_chatbot/backend/ | Historial de chats |
| chroma_db/ | modulo_rag/backend/ | Índice vectorial (embeddings) |
