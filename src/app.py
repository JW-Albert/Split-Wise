from flask import Flask, request, jsonify, session, render_template, redirect, url_for
import os
from dotenv import load_dotenv
from database import init_db, get_db
from models import generate_otp, save_otp, verify_otp, create_user, generate_room_id
from mailer import send_otp_email
from auth import login_required, is_admin, get_current_user, can_access_room, can_invite_to_room
from calculations import calculate_settlement

# 從 ENV/.env 載入環境變數
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ENV', '.env')
load_dotenv(env_path)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# 初始化資料庫
init_db()

# ==================== 認證相關路由 ====================

@app.route('/')
def index():
    """首頁重定向到登入頁"""
    if 'email' in session:
        return redirect(url_for('rooms_page'))
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    """登入頁面"""
    if 'email' in session:
        return redirect(url_for('rooms_page'))
    return render_template('login.html')

@app.route('/verify')
def verify_page():
    """驗證碼輸入頁面"""
    if 'email' in session:
        return redirect(url_for('rooms_page'))
    if 'pending_email' not in session:
        return redirect(url_for('login_page'))
    return render_template('verify.html')

@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    """發送 OTP 驗證碼"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    if not email or '@' not in email:
        return jsonify({"error": "請輸入有效的 email"}), 400
    
    # 生成並儲存 OTP
    otp = generate_otp()
    save_otp(email, otp)
    
    # 發送郵件
    try:
        send_otp_email(email, otp)
    except Exception as e:
        return jsonify({"error": f"發送郵件失敗: {str(e)}"}), 500
    
    # 儲存待驗證的 email 到 session
    session['pending_email'] = email
    
    return jsonify({"message": "驗證碼已發送"})

@app.route('/api/auth/resend-otp', methods=['POST'])
def resend_otp():
    """重新發送 OTP"""
    if 'pending_email' not in session:
        return jsonify({"error": "請先發送驗證碼"}), 400
    
    email = session['pending_email']
    
    # 生成並儲存 OTP
    otp = generate_otp()
    save_otp(email, otp)
    
    # 發送郵件
    try:
        send_otp_email(email, otp)
    except Exception as e:
        return jsonify({"error": f"發送郵件失敗: {str(e)}"}), 500
    
    return jsonify({"message": "驗證碼已重新發送"})

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp_endpoint():
    """驗證 OTP"""
    if 'pending_email' not in session:
        return jsonify({"error": "請先發送驗證碼"}), 400
    
    data = request.get_json()
    otp = data.get('otp', '').strip()
    email = session['pending_email']
    
    if not otp or len(otp) != 6 or not otp.isdigit():
        return jsonify({"error": "請輸入 6 位數字驗證碼"}), 400
    
    # 驗證 OTP
    if not verify_otp(email, otp):
        return jsonify({"error": "驗證碼錯誤或已過期"}), 400
    
    # 建立使用者（如果不存在）
    create_user(email)
    
    # 設置 session
    session['email'] = email
    session.pop('pending_email', None)
    
    return jsonify({"message": "登入成功", "email": email})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user_info():
    """取得當前使用者資訊"""
    email = get_current_user()
    is_admin_user = is_admin(email)
    return jsonify({
        "email": email,
        "is_admin": is_admin_user
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """登出"""
    session.clear()
    return jsonify({"message": "已登出"})

# ==================== 房間相關 API ====================

@app.route('/api/rooms', methods=['GET'])
@login_required
def get_rooms():
    """取得使用者可查看的房間列表"""
    email = get_current_user()
    conn = get_db()
    cursor = conn.cursor()
    
    if is_admin(email):
        # 管理員可以看到所有房間
        cursor.execute("SELECT id, name, owner_email, created_at FROM rooms ORDER BY created_at DESC")
    else:
        # 一般使用者只能看到自己擁有或參與的房間
        cursor.execute("""
            SELECT DISTINCT r.id, r.name, r.owner_email, r.created_at
            FROM rooms r
            LEFT JOIN room_members rm ON r.id = rm.room_id
            WHERE r.owner_email = ? OR rm.email = ?
            ORDER BY r.created_at DESC
        """, (email, email))
    
    rooms = cursor.fetchall()
    conn.close()
    
    result = []
    for room in rooms:
        result.append({
            "id": room[0],
            "name": room[1],
            "owner_email": room[2],
            "created_at": room[3]
        })
    
    return jsonify({"rooms": result})

@app.route('/api/rooms', methods=['POST'])
@login_required
def create_room():
    """建立新房間"""
    email = get_current_user()
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({"error": "房間名稱不能為空"}), 400
    
    room_id = generate_room_id()
    conn = get_db()
    cursor = conn.cursor()
    
    # 建立房間
    cursor.execute(
        "INSERT INTO rooms (id, name, owner_email) VALUES (?, ?, ?)",
        (room_id, name, email)
    )
    
    # 將建立者加入房間成員
    cursor.execute(
        "INSERT INTO room_members (room_id, email) VALUES (?, ?)",
        (room_id, email)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "房間建立成功", "room_id": room_id})

@app.route('/api/rooms/<room_id>', methods=['GET'])
@login_required
def get_room(room_id):
    """取得房間詳細資訊"""
    email = get_current_user()
    
    if not can_access_room(email, room_id):
        return jsonify({"error": "無權限存取此房間"}), 403
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 取得房間資訊
    cursor.execute("SELECT id, name, owner_email, created_at FROM rooms WHERE id=?", (room_id,))
    room = cursor.fetchone()
    
    if not room:
        conn.close()
        return jsonify({"error": "房間不存在"}), 404
    
    # 取得房間成員
    cursor.execute("SELECT email FROM room_members WHERE room_id=?", (room_id,))
    members = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        "id": room[0],
        "name": room[1],
        "owner_email": room[2],
        "created_at": room[3],
        "members": [member[0] for member in members]
    })

@app.route('/api/rooms/<room_id>/invite', methods=['POST'])
@login_required
def invite_to_room(room_id):
    """邀請使用者加入房間"""
    email = get_current_user()
    
    if not can_invite_to_room(email, room_id):
        return jsonify({"error": "無權限邀請他人加入此房間"}), 403
    
    data = request.get_json()
    invite_email = data.get('email', '').strip().lower()
    
    if not invite_email or '@' not in invite_email:
        return jsonify({"error": "請輸入有效的 email"}), 400
    
    if invite_email == email:
        return jsonify({"error": "不能邀請自己"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 檢查房間是否存在
    cursor.execute("SELECT id FROM rooms WHERE id=?", (room_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "房間不存在"}), 404
    
    # 檢查是否已經是成員
    cursor.execute(
        "SELECT id FROM room_members WHERE room_id=? AND email=?",
        (room_id, invite_email)
    )
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "該使用者已經是房間成員"}), 400
    
    # 如果使用者不存在，建立使用者記錄（verified=0）
    cursor.execute("SELECT email FROM users WHERE email=?", (invite_email,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (email, verified) VALUES (?, ?)",
            (invite_email, 0)
        )
    
    # 加入成員
    cursor.execute(
        "INSERT INTO room_members (room_id, email) VALUES (?, ?)",
        (room_id, invite_email)
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "邀請成功"})

# ==================== 支出相關 API ====================

@app.route('/api/rooms/<room_id>/expenses', methods=['GET'])
@login_required
def get_expenses(room_id):
    """取得房間的所有支出"""
    email = get_current_user()
    
    if not can_access_room(email, room_id):
        return jsonify({"error": "無權限存取此房間"}), 403
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 取得所有支出
    cursor.execute(
        "SELECT id, title, amount, payer_email, created_at FROM expenses WHERE room_id=? ORDER BY created_at DESC",
        (room_id,)
    )
    expenses = cursor.fetchall()
    
    result = []
    for expense in expenses:
        expense_id = expense[0]
        
        # 取得參與者
        cursor.execute(
            "SELECT email FROM expense_participants WHERE expense_id=?",
            (expense_id,)
        )
        participants = [p[0] for p in cursor.fetchall()]
        
        result.append({
            "id": expense_id,
            "title": expense[1],
            "amount": expense[2],
            "payer_email": expense[3],
            "created_at": expense[4],
            "participants": participants
        })
    
    conn.close()
    
    return jsonify({"expenses": result})

@app.route('/api/rooms/<room_id>/expenses', methods=['POST'])
@login_required
def create_expense(room_id):
    """建立新支出"""
    email = get_current_user()
    
    if not can_access_room(email, room_id):
        return jsonify({"error": "無權限存取此房間"}), 403
    
    data = request.get_json()
    title = data.get('title', '').strip()
    amount = data.get('amount', 0)
    payer = data.get('payer', '').strip().lower()
    participants = data.get('participants', [])
    
    if not title:
        return jsonify({"error": "支出標題不能為空"}), 400
    
    if amount <= 0:
        return jsonify({"error": "支出金額必須大於 0"}), 400
    
    if not payer or '@' not in payer:
        return jsonify({"error": "請輸入有效的付款人 email"}), 400
    
    if not participants or len(participants) == 0:
        return jsonify({"error": "至少需要一個參與者"}), 400
    
    # 轉換 participants 為小寫
    participants = [p.strip().lower() for p in participants]
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 檢查所有參與者是否都是房間成員
    # 使用參數化查詢，避免 SQL injection
    if len(participants) == 0:
        conn.close()
        return jsonify({"error": "至少需要一個參與者"}), 400
    
    # 建立參數化查詢
    placeholders = ','.join(['?'] * len(participants))
    query = "SELECT email FROM room_members WHERE room_id=? AND email IN (" + placeholders + ")"
    params = (room_id,) + tuple(participants)
    cursor.execute(query, params)
    valid_members = {row[0] for row in cursor.fetchall()}
    
    if len(valid_members) != len(participants):
        conn.close()
        return jsonify({"error": "所有參與者必須是房間成員"}), 400
    
    # 檢查付款人是否在參與者中
    if payer not in participants:
        conn.close()
        return jsonify({"error": "付款人必須在參與者列表中"}), 400
    
    # 建立支出
    cursor.execute(
        "INSERT INTO expenses (room_id, title, amount, payer_email) VALUES (?, ?, ?, ?)",
        (room_id, title, amount, payer)
    )
    expense_id = cursor.lastrowid
    
    # 加入參與者
    for participant_email in participants:
        cursor.execute(
            "INSERT INTO expense_participants (expense_id, email) VALUES (?, ?)",
            (expense_id, participant_email)
        )
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "支出建立成功", "expense_id": expense_id})

# ==================== 結算相關 API ====================

@app.route('/api/rooms/<room_id>/settlement', methods=['GET'])
@login_required
def get_settlement(room_id):
    """取得房間的結算結果"""
    email = get_current_user()
    
    if not can_access_room(email, room_id):
        return jsonify({"error": "無權限存取此房間"}), 403
    
    result = calculate_settlement(room_id)
    return jsonify(result)

# ==================== 頁面路由 ====================

@app.route('/rooms')
@login_required
def rooms_page():
    """房間列表頁面"""
    return render_template('rooms.html')

@app.route('/room/<room_id>')
@login_required
def room_page(room_id):
    """房間詳細頁面"""
    email = get_current_user()
    
    if not can_access_room(email, room_id):
        return render_template('error.html', message="無權限存取此房間"), 403
    
    return render_template('room.html', room_id=room_id)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

