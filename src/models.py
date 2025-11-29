import secrets
import random
from datetime import datetime, timedelta
from database import get_db

def generate_room_id():
    """生成 8 位隨機房間 ID"""
    return secrets.token_urlsafe(6)[:8]

def generate_otp():
    """生成 6 位數字 OTP"""
    return str(random.randint(100000, 999999))

def create_user(email):
    """建立新使用者（如果不存在）"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 檢查使用者是否已存在
    cursor.execute("SELECT email FROM users WHERE email=?", (email,))
    if cursor.fetchone():
        conn.close()
        return False
    
    # 建立新使用者
    cursor.execute(
        "INSERT INTO users (email, verified) VALUES (?, ?)",
        (email, 1)
    )
    conn.commit()
    conn.close()
    return True

def save_otp(email, otp):
    """儲存 OTP 到資料庫（10 分鐘有效）"""
    conn = get_db()
    cursor = conn.cursor()
    
    expires_at = datetime.now() + timedelta(minutes=10)
    
    # 刪除舊的 OTP
    cursor.execute("DELETE FROM login_tokens WHERE email=?", (email,))
    
    # 插入新 OTP
    cursor.execute(
        "INSERT INTO login_tokens (email, otp, expires_at) VALUES (?, ?, ?)",
        (email, otp, expires_at)
    )
    conn.commit()
    conn.close()

def verify_otp(email, otp):
    """驗證 OTP 是否正確且未過期"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT expires_at FROM login_tokens WHERE email=? AND otp=?",
        (email, otp)
    )
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    expires_at = datetime.fromisoformat(result[0])
    if datetime.now() > expires_at:
        return False
    
    return True

def is_user_verified(email):
    """檢查使用者是否已驗證"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT verified FROM users WHERE email=?", (email,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    return result[0] == 1

