from functools import wraps
from flask import session, jsonify
import os
from dotenv import load_dotenv

# 從 ENV/.env 載入環境變數
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ENV', '.env')
load_dotenv(env_path)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")

def login_required(f):
    """裝飾器：要求使用者必須登入"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            return jsonify({"error": "請先登入"}), 401
        return f(*args, **kwargs)
    return decorated_function

def is_admin(email):
    """檢查是否為管理員"""
    return email == ADMIN_EMAIL

def get_current_user():
    """取得當前登入的使用者 email"""
    return session.get('email')

def can_access_room(email, room_id):
    """檢查使用者是否有權限存取房間"""
    from database import get_db
    
    # 管理員可以存取所有房間
    if is_admin(email):
        return True
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 檢查是否為房間擁有者
    cursor.execute("SELECT owner_email FROM rooms WHERE id=?", (room_id,))
    room = cursor.fetchone()
    
    if not room:
        conn.close()
        return False
    
    if room[0] == email:
        conn.close()
        return True
    
    # 檢查是否為房間成員
    cursor.execute(
        "SELECT id FROM room_members WHERE room_id=? AND email=?",
        (room_id, email)
    )
    member = cursor.fetchone()
    conn.close()
    
    return member is not None

def can_invite_to_room(email, room_id):
    """檢查使用者是否可以邀請他人加入房間"""
    from database import get_db
    
    # 管理員可以邀請
    if is_admin(email):
        return True
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 檢查是否為房間擁有者
    cursor.execute("SELECT owner_email FROM rooms WHERE id=?", (room_id,))
    room = cursor.fetchone()
    
    if not room:
        conn.close()
        return False
    
    if room[0] == email:
        conn.close()
        return True
    
    # 檢查是否為房間成員（成員也可以邀請）
    cursor.execute(
        "SELECT id FROM room_members WHERE room_id=? AND email=?",
        (room_id, email)
    )
    member = cursor.fetchone()
    conn.close()
    
    return member is not None

