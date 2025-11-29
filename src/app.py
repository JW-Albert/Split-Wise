from flask import Flask, request, jsonify, session, render_template, redirect, url_for
import os
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix
from database import init_db, get_db
from models import generate_otp, save_otp, verify_otp, create_user, generate_room_id, update_user_name, get_user_name, get_user_names
from mailer import send_otp_email
from auth import login_required, is_admin, get_current_user, can_access_room, can_invite_to_room
from calculations import calculate_settlement

# 從 ENV/.env 載入環境變數
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ENV', '.env')
load_dotenv(env_path)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# 配置 ProxyFix 以處理 Cloudflare Tunnel 的反向代理
# x_for=1: 信任 1 層 X-Forwarded-For 標頭
# x_proto=1: 信任 X-Forwarded-Proto 標頭
# x_host=1: 信任 X-Forwarded-Host 標頭
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

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
    
    # 檢查使用者是否已存在且有名稱
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM users WHERE email=?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        # 使用者已存在，檢查是否有名稱
        if user[0]:
            # 已有名稱，直接登入
            session['email'] = email
            session.pop('pending_email', None)
            return jsonify({"message": "登入成功", "email": email, "needs_name": False})
        else:
            # 沒有名稱，需要輸入
            session['otp_verified'] = True
            return jsonify({"message": "請輸入用戶名稱", "needs_name": True})
    else:
        # 新使用者，需要輸入名稱
        session['otp_verified'] = True
        return jsonify({"message": "請輸入用戶名稱", "needs_name": True})

@app.route('/api/auth/set-name', methods=['POST'])
def set_user_name():
    """設定用戶名稱"""
    if 'pending_email' not in session or not session.get('otp_verified'):
        return jsonify({"error": "請先完成驗證碼驗證"}), 400
    
    data = request.get_json()
    name = data.get('name', '').strip()
    email = session['pending_email']
    
    if not name:
        return jsonify({"error": "用戶名稱不能為空"}), 400
    
    if len(name) > 50:
        return jsonify({"error": "用戶名稱不能超過 50 個字元"}), 400
    
    # 建立或更新使用者
    create_user(email, name)
    
    # 設置 session
    session['email'] = email
    session.pop('pending_email', None)
    session.pop('otp_verified', None)
    
    return jsonify({"message": "設定成功", "email": email})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user_info():
    """取得當前使用者資訊"""
    email = get_current_user()
    is_admin_user = is_admin(email)
    name = get_user_name(email)
    return jsonify({
        "email": email,
        "name": name,
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
    
    # 取得所有擁有者的名稱
    owner_emails = [room[2] for room in rooms]
    owner_names = get_user_names(owner_emails)
    
    conn.close()
    
    result = []
    for room in rooms:
        result.append({
            "id": room[0],
            "name": room[1],
            "owner_email": room[2],
            "owner_name": owner_names.get(room[2], room[2]),
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
    member_emails = [member[0] for member in members]
    
    # 取得所有成員的名稱
    member_names = get_user_names(member_emails)
    owner_name = get_user_name(room[2])
    
    conn.close()
    
    return jsonify({
        "id": room[0],
        "name": room[1],
        "owner_email": room[2],
        "owner_name": owner_name,
        "created_at": room[3],
        "members": member_emails,
        "member_names": member_names
    })

@app.route('/api/rooms/<room_id>', methods=['DELETE'])
@login_required
def delete_room(room_id):
    """刪除房間（僅擁有者或管理員）"""
    email = get_current_user()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 檢查房間是否存在
    cursor.execute("SELECT owner_email FROM rooms WHERE id=?", (room_id,))
    room = cursor.fetchone()
    
    if not room:
        conn.close()
        return jsonify({"error": "房間不存在"}), 404
    
    # 檢查權限：只有擁有者或管理員可以刪除
    if room[0] != email and not is_admin(email):
        conn.close()
        return jsonify({"error": "無權限刪除此房間"}), 403
    
    # 刪除相關資料
    # 1. 刪除支出參與者
    cursor.execute("""
        DELETE FROM expense_participants 
        WHERE expense_id IN (SELECT id FROM expenses WHERE room_id=?)
    """, (room_id,))
    
    # 2. 刪除支出
    cursor.execute("DELETE FROM expenses WHERE room_id=?", (room_id,))
    
    # 3. 刪除房間成員
    cursor.execute("DELETE FROM room_members WHERE room_id=?", (room_id,))
    
    # 4. 刪除房間
    cursor.execute("DELETE FROM rooms WHERE id=?", (room_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "房間已刪除"})

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
    
    # 收集所有需要查詢名稱的 email
    all_emails = set()
    for expense in expenses:
        all_emails.add(expense[3])  # payer_email
        expense_id = expense[0]
        cursor.execute(
            "SELECT email FROM expense_participants WHERE expense_id=?",
            (expense_id,)
        )
        participants = [p[0] for p in cursor.fetchall()]
        all_emails.update(participants)
    
    # 取得所有用戶名稱
    user_names = get_user_names(list(all_emails))
    
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
            "payer_name": user_names.get(expense[3], expense[3]),
            "created_at": expense[4],
            "participants": participants,
            "participant_names": {email: user_names.get(email, email) for email in participants}
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

@app.route('/api/rooms/<room_id>/expenses/<expense_id>', methods=['DELETE'])
@login_required
def delete_expense(room_id, expense_id):
    """刪除支出（僅房間成員或管理員）"""
    email = get_current_user()
    
    # 檢查是否有權限存取房間
    if not can_access_room(email, room_id):
        return jsonify({"error": "無權限存取此房間"}), 403
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 檢查支出是否存在
    cursor.execute(
        "SELECT id FROM expenses WHERE id=? AND room_id=?",
        (expense_id, room_id)
    )
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "支出記錄不存在"}), 404
    
    # 刪除支出參與者
    cursor.execute("DELETE FROM expense_participants WHERE expense_id=?", (expense_id,))
    
    # 刪除支出
    cursor.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "支出記錄已刪除"})

# ==================== 結算相關 API ====================

@app.route('/api/rooms/<room_id>/settlement', methods=['GET'])
@login_required
def get_settlement(room_id):
    """取得房間的結算結果"""
    email = get_current_user()
    
    if not can_access_room(email, room_id):
        return jsonify({"error": "無權限存取此房間"}), 403
    
    result = calculate_settlement(room_id)
    
    # 取得所有用戶的名稱
    all_emails = set()
    for balance in result.get("balances", []):
        all_emails.add(balance["email"])
    for payment in result.get("payments", []):
        all_emails.add(payment["from"])
        all_emails.add(payment["to"])
    
    user_names = get_user_names(list(all_emails))
    
    # 添加名稱到結果中
    for balance in result.get("balances", []):
        balance["name"] = user_names.get(balance["email"], balance["email"])
    
    for payment in result.get("payments", []):
        payment["from_name"] = user_names.get(payment["from"], payment["from"])
        payment["to_name"] = user_names.get(payment["to"], payment["to"])
    
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

# ==================== 管理員管理 API ====================

@app.route('/admin/users', methods=['GET'])
@login_required
def get_all_users():
    """取得所有使用者（僅管理員）"""
    email = get_current_user()
    
    if not is_admin(email):
        return jsonify({"error": "無權限"}), 403
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT email, name, verified, created_at FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    
    result = []
    for user in users:
        result.append({
            "email": user[0],
            "name": user[1] or user[0],  # 如果沒有名稱，使用 email
            "verified": user[2] == 1,
            "created_at": user[3]
        })
    
    return jsonify({"users": result})

@app.route('/admin/users/<user_email>', methods=['PUT'])
@login_required
def update_user(user_email):
    """更新使用者資訊（僅管理員）"""
    email = get_current_user()
    
    if not is_admin(email):
        return jsonify({"error": "無權限"}), 403
    
    data = request.get_json()
    new_name = data.get('name', '').strip()
    
    if not new_name:
        return jsonify({"error": "用戶名稱不能為空"}), 400
    
    if len(new_name) > 50:
        return jsonify({"error": "用戶名稱不能超過 50 個字元"}), 400
    
    update_user_name(user_email, new_name)
    
    return jsonify({"message": "更新成功"})

@app.route('/admin/users', methods=['POST'])
@login_required
def create_user_by_admin():
    """管理員建立新使用者"""
    email = get_current_user()
    
    if not is_admin(email):
        return jsonify({"error": "無權限"}), 403
    
    data = request.get_json()
    user_email = data.get('email', '').strip().lower()
    user_name = data.get('name', '').strip()
    
    if not user_email or '@' not in user_email:
        return jsonify({"error": "請輸入有效的 email"}), 400
    
    if not user_name:
        return jsonify({"error": "用戶名稱不能為空"}), 400
    
    if len(user_name) > 50:
        return jsonify({"error": "用戶名稱不能超過 50 個字元"}), 400
    
    # 檢查使用者是否已存在
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE email=?", (user_email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "使用者已存在"}), 400
    conn.close()
    
    create_user(user_email, user_name)
    
    return jsonify({"message": "使用者建立成功"})

@app.route('/admin/users/<user_email>', methods=['DELETE'])
@login_required
def delete_user(user_email):
    """刪除使用者（僅管理員）"""
    email = get_current_user()
    
    if not is_admin(email):
        return jsonify({"error": "無權限"}), 403
    
    # 不能刪除自己
    if user_email == email:
        return jsonify({"error": "不能刪除自己的帳號"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 檢查使用者是否存在
    cursor.execute("SELECT email FROM users WHERE email=?", (user_email,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "使用者不存在"}), 404
    
    # 刪除使用者相關資料
    # 刪除房間成員關係
    cursor.execute("DELETE FROM room_members WHERE email=?", (user_email,))
    # 刪除支出參與者
    cursor.execute("""
        DELETE FROM expense_participants 
        WHERE email=? AND expense_id IN (
            SELECT id FROM expenses WHERE payer_email=?
        )
    """, (user_email, user_email))
    # 刪除使用者擁有的房間（可選，這裡選擇刪除）
    cursor.execute("DELETE FROM rooms WHERE owner_email=?", (user_email,))
    # 刪除使用者
    cursor.execute("DELETE FROM users WHERE email=?", (user_email,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "使用者已刪除"})

@app.route('/admin')
@login_required
def admin_page():
    """管理員管理頁面"""
    email = get_current_user()
    
    if not is_admin(email):
        return render_template('error.html', message="無權限存取此頁面"), 403
    
    return render_template('admin.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

