"""
Authentication module - JWT tokens and password hashing
"""
from datetime import datetime, timedelta
from typing import Optional
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

import database as db

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "tu-clave-secreta-muy-segura-cambiar-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing - using sha256_crypt for compatibility
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


# --- Pydantic models ---

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    created_at: str


# --- Password functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# --- Token functions ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify token and return username if valid"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None


# --- User database functions ---

def create_user(username: str, password: str, email: Optional[str] = None) -> Optional[int]:
    """Create a new user, returns user_id or None if username exists"""
    conn = db.get_connection()
    cur = conn.cursor()
    
    # Check if username exists
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cur.fetchone():
        conn.close()
        return None
    
    # Create user
    password_hash = get_password_hash(password)
    now = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO users (username, password_hash, email, created_at)
        VALUES (?, ?, ?, ?)
    """, (username, password_hash, email, now))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user, returns user dict or None"""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        return None
    
    user = dict(row)
    if not verify_password(password, user["password_hash"]):
        return None
    
    return user


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user by username"""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, created_at FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
