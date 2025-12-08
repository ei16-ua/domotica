"""
Predictions Database - Student performance predictions
Used by RAG service to personalize responses based on predicted performance
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).parent / "predictions.db"


def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Predictions table - stores predicted scores for students
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            predicted_score REAL NOT NULL CHECK(predicted_score >= 0 AND predicted_score <= 10),
            confidence REAL CHECK(confidence >= 0 AND confidence <= 1),
            model_version TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(student_id, subject_id)
        )
    """)
    
    # Prediction factors - what contributed to the prediction
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prediction_factors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER NOT NULL,
            factor_name TEXT NOT NULL,
            factor_value REAL NOT NULL,
            weight REAL,
            FOREIGN KEY (prediction_id) REFERENCES predictions(id) ON DELETE CASCADE
        )
    """)
    
    # Student interactions - tracking for future model training
    cur.execute("""
        CREATE TABLE IF NOT EXISTS student_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_id TEXT NOT NULL,
            interaction_type TEXT NOT NULL,  -- 'question', 'test_request', 'exercise_request'
            topic TEXT,
            difficulty_level TEXT,
            success_indicator REAL,  -- 0.0 to 1.0, null if not evaluated
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ Predictions database initialized at {DB_PATH}")


# --- Prediction operations ---

def set_prediction(student_id: str, subject_id: str, predicted_score: float, 
                   confidence: Optional[float] = None, model_version: str = "v1") -> int:
    """Set or update prediction for a student in a subject"""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    cur.execute("""
        INSERT INTO predictions (student_id, subject_id, predicted_score, confidence, model_version, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id, subject_id) DO UPDATE SET
            predicted_score = excluded.predicted_score,
            confidence = excluded.confidence,
            model_version = excluded.model_version,
            updated_at = excluded.updated_at
    """, (student_id, subject_id, predicted_score, confidence, model_version, now, now))
    
    conn.commit()
    pred_id = cur.lastrowid
    conn.close()
    return pred_id


def get_prediction(student_id: str, subject_id: str) -> Optional[dict]:
    """Get prediction for a student in a subject"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM predictions WHERE student_id = ? AND subject_id = ?
    """, (student_id, subject_id))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_predictions(student_id: str) -> List[dict]:
    """Get all predictions for a student"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM predictions WHERE student_id = ? ORDER BY updated_at DESC
    """, (student_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_performance_level(predicted_score: float) -> str:
    """Convert score to performance level"""
    if predicted_score >= 8.5:
        return "excelente"
    elif predicted_score >= 7.0:
        return "bueno"
    elif predicted_score >= 5.0:
        return "suficiente"
    elif predicted_score >= 3.5:
        return "insuficiente"
    else:
        return "muy bajo"


# --- Interaction tracking ---

def log_interaction(student_id: str, subject_id: str, interaction_type: str,
                   topic: Optional[str] = None, difficulty_level: Optional[str] = None,
                   success_indicator: Optional[float] = None) -> int:
    """Log a student interaction for future analysis"""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now().isoformat()
    
    cur.execute("""
        INSERT INTO student_interactions 
        (student_id, subject_id, interaction_type, topic, difficulty_level, success_indicator, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (student_id, subject_id, interaction_type, topic, difficulty_level, success_indicator, now))
    
    conn.commit()
    interaction_id = cur.lastrowid
    conn.close()
    return interaction_id


def get_student_interactions(student_id: str, subject_id: Optional[str] = None, limit: int = 100) -> List[dict]:
    """Get recent interactions for a student"""
    conn = get_connection()
    cur = conn.cursor()
    
    if subject_id:
        cur.execute("""
            SELECT * FROM student_interactions 
            WHERE student_id = ? AND subject_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (student_id, subject_id, limit))
    else:
        cur.execute("""
            SELECT * FROM student_interactions 
            WHERE student_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (student_id, limit))
    
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# Initialize database on import
init_db()
