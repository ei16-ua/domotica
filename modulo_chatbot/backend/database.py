"""
Database models and utilities for chat history
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json

DB_PATH = Path(__file__).parent / "chat_history.db"


def get_connection():
    """Get database connection with timeout to prevent locks"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Conversations table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            title TEXT DEFAULT 'Nueva conversación',
            subject_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Messages table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            sources TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    
    # Users table (for authentication later)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ Database initialized at {DB_PATH}")


# --- Conversation operations ---

def create_conversation(user_id: str, subject_id: Optional[str] = None, title: str = "Nueva conversación") -> int:
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO conversations (user_id, title, subject_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, title, subject_id, now, now))
    conn.commit()
    conv_id = cur.lastrowid
    conn.close()
    return conv_id


def get_conversations(user_id: str) -> List[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, subject_id, created_at, updated_at
        FROM conversations
        WHERE user_id = ?
        ORDER BY updated_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_conversation(conversation_id: int) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_conversation_title(conversation_id: int, title: str):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    cur.execute("""
        UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?
    """, (title, now, conversation_id))
    conn.commit()
    conn.close()


def delete_conversation(conversation_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()


# --- Message operations ---

def add_message(conversation_id: int, role: str, content: str, sources: Optional[List[dict]] = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    sources_json = json.dumps(sources) if sources else None
    cur.execute("""
        INSERT INTO messages (conversation_id, role, content, sources, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (conversation_id, role, content, sources_json, now))
    
    # Update conversation timestamp
    cur.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
    
    conn.commit()
    msg_id = cur.lastrowid
    conn.close()
    return msg_id


def get_messages(conversation_id: int) -> List[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, role, content, sources, created_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    """, (conversation_id,))
    rows = cur.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        msg = dict(row)
        if msg["sources"]:
            msg["sources"] = json.loads(msg["sources"])
        messages.append(msg)
    return messages


# Initialize database on import
init_db()
