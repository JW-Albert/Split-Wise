import sqlite3
import os
from datetime import datetime, timedelta

DB_NAME = "splitwise.db"

def get_db():
    """取得資料庫連線"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化資料庫，建立所有必要的表格"""
    conn = get_db()
    cursor = conn.cursor()
    
    # users 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT,
            password_hash TEXT,
            verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 如果 name 欄位不存在，添加它（用於現有資料庫）
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass  # 欄位已存在
    
    # login_tokens 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_tokens (
            email TEXT,
            otp TEXT,
            expires_at TIMESTAMP,
            PRIMARY KEY (email, otp)
        )
    """)
    
    # rooms 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            owner_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # room_members 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS room_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            email TEXT NOT NULL,
            UNIQUE(room_id, email)
        )
    """)
    
    # expenses 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            title TEXT NOT NULL,
            amount INTEGER NOT NULL,
            payer_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # expense_participants 表格
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expense_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            UNIQUE(expense_id, email)
        )
    """)
    
    conn.commit()
    conn.close()

