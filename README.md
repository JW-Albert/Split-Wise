# Split-Wise 分帳工具

一個多人分帳工具，支援 Email 註冊/驗證碼登入、房間管理、支出記錄和自動結算功能。

## 功能特色

- Email + OTP 驗證碼登入（無需密碼）
- 房間（Room）管理系統
- 支出記錄與分攤
- 自動結算功能（雙指針配對算法）
- 權限管理（管理員可查看所有房間）
- SQL Injection 防護（全部使用參數化查詢）
- 現代化 UI（TailwindCSS + Alpine.js）

## 技術棧

- **Backend**: Python + Flask
- **Database**: SQLite3（參數化查詢）
- **Frontend**: HTML + TailwindCSS + Alpine.js
- **Templates**: Jinja2
- **Auth**: Email + 6 位數 OTP
- **Config**: python-dotenv (.env)

## 安裝與設定

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

複製 `.env.example` 並在 `ENV/` 資料夾中建立 `.env` 檔案：

```bash
# 如果專案中有 .env.example，複製它
cp .env.example ENV/.env

# 或手動在 ENV/ 資料夾中建立 .env 檔案
```

`.env` 檔案內容：

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

ADMIN_EMAIL=admin@example.com
SECRET_KEY=your-secret-key-here-change-this-to-random-string
```

**重要提示**：
- `.env` 檔案必須放在 `ENV/` 資料夾中
- Gmail 需要使用「應用程式密碼」而非一般密碼
- `SECRET_KEY` 請設定為隨機字串（用於 session 簽名）
- `ADMIN_EMAIL` 設定的 email 將擁有管理員權限

### 3. 初始化資料庫

執行應用程式時會自動建立資料庫和表格：

```bash
# 使用 Python 直接執行
python src/app.py

# 或使用提供的腳本（Linux/Mac）
bash run.sh
```

資料庫檔案 `splitwise.db` 會自動建立在專案根目錄。

## 使用說明

### 啟動應用程式

```bash
# 方法 1: 使用 Python 直接執行
python src/app.py

# 方法 2: 使用提供的腳本（Linux/Mac）
bash run.sh

# 方法 3: 在虛擬環境中執行
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
python src/app.py
```

應用程式會在 `http://localhost:5000` 啟動。

### 使用流程

1. **登入/註冊**
   - 訪問 `/login`
   - 輸入 email
   - 系統會發送 6 位數驗證碼到您的信箱
   - 在 `/verify` 頁面輸入驗證碼完成登入

2. **建立房間**
   - 登入後進入房間列表頁面
   - 點擊「建立新房間」
   - 輸入房間名稱（例如：「日本旅遊 2025」）

3. **邀請成員**
   - 進入房間詳情頁
   - 在「邀請成員」區塊輸入 email
   - 點擊「邀請」按鈕

4. **新增支出**
   - 在房間詳情頁填寫支出表單
   - 輸入標題、金額、付款人和參與者
   - 系統會自動平均分攤給所有參與者

5. **查看結算**
   - 在房間詳情頁底部查看「結算結果」
   - 系統會自動計算每人應付/應收金額
   - 顯示付款建議（誰應該付給誰）

## API 端點

### 認證相關

- `POST /api/auth/send-otp` - 發送驗證碼
- `POST /api/auth/resend-otp` - 重新發送驗證碼
- `POST /api/auth/verify-otp` - 驗證 OTP
- `GET /api/auth/me` - 取得當前使用者資訊
- `POST /api/auth/logout` - 登出

### 房間相關

- `GET /api/rooms` - 取得房間列表
- `POST /api/rooms` - 建立新房間
- `GET /api/rooms/<room_id>` - 取得房間詳情
- `POST /api/rooms/<room_id>/invite` - 邀請成員

### 支出相關

- `GET /api/rooms/<room_id>/expenses` - 取得支出列表
- `POST /api/rooms/<room_id>/expenses` - 新增支出

### 結算相關

- `GET /api/rooms/<room_id>/settlement` - 取得結算結果

## 資料庫結構

### users
- `email` (PRIMARY KEY)
- `password_hash` (預留欄位)
- `verified` (0 or 1)
- `created_at`

### login_tokens
- `email`
- `otp` (6 位數字)
- `expires_at` (10 分鐘有效)

### rooms
- `id` (8 字元 token)
- `name`
- `owner_email`
- `created_at`

### room_members
- `id` (AUTOINCREMENT)
- `room_id`
- `email`

### expenses
- `id` (AUTOINCREMENT)
- `room_id`
- `title`
- `amount`
- `payer_email`
- `created_at`

### expense_participants
- `id` (AUTOINCREMENT)
- `expense_id`
- `email`

## 安全性

### SQL Injection 防護

所有 SQL 查詢都使用參數化查詢：

```python
# 正確
cursor.execute("SELECT * FROM users WHERE email=?", (email,))

# 錯誤（禁止）
cursor.execute(f"SELECT * FROM users WHERE email='{email}'")
```

### Session 安全

- 使用 `SECRET_KEY` 簽名 session
- Session 儲存使用者 email
- 所有需要認證的端點都使用 `@login_required` 裝飾器

### OTP 安全

- 6 位數隨機數字
- 10 分鐘有效期
- 每次登入/註冊都重新產生

## 權限管理

### 管理員

- Email 符合 `ADMIN_EMAIL` 的使用者
- 可以查看所有房間
- 可以管理所有房間

### 一般使用者

- 只能查看/編輯自己擁有或參與的房間
- 可以建立自己的房間
- 可以邀請他人加入房間

## 結算算法

使用雙指針配對算法：

1. 計算每人總付款（total_paid）
2. 計算每人應負擔（total_share）
3. 計算餘額（balance = total_paid - total_share）
4. 分離債權人（balance > 0）和債務人（balance < 0）
5. 使用雙指針配對，最小化付款次數

## 專案結構

```
Split-Wise/
├── src/                   # 原始碼目錄
│   ├── app.py            # 主應用程式
│   ├── database.py      # 資料庫初始化
│   ├── models.py        # 資料模型和工具函數
│   ├── auth.py          # 認證和權限檢查
│   ├── calculations.py # 結算算法
│   ├── mailer.py        # SMTP 郵件發送
│   ├── templates/       # HTML 模板
│   │   ├── login.html
│   │   ├── verify.html
│   │   ├── rooms.html
│   │   ├── room.html
│   │   └── error.html
│   └── static/          # 靜態資源
│       ├── style.css
│       └── main.js
├── ENV/                  # 環境變數資料夾
│   └── .env             # 環境變數檔案（不加入 git）
├── venv/                 # Python 虛擬環境（不加入 git）
├── requirements.txt     # Python 依賴
├── .env.example         # 環境變數範例檔案
├── .gitignore           # Git 忽略規則
├── run.sh               # 啟動腳本（Linux/Mac）
├── deploy.sh            # 部署腳本（Linux/Mac）
├── splitwise.db         # SQLite 資料庫（自動產生，不加入 git）
└── README.md            # 專案說明文件
```

## 開發注意事項

1. **絕對不能使用 f-string 組 SQL**
   - 所有 SQL 必須使用 `?` 參數化
   - 動態 SQL 使用字串拼接 `?` 而非值

2. **環境變數**
   - 所有敏感資訊從 `ENV/.env` 載入
   - `.env` 檔案必須放在 `ENV/` 資料夾中
   - `ENV/.env` 不要加入版本控制（已在 .gitignore 中設定）
   - 使用 `.env.example` 作為範本

3. **錯誤處理**
   - 所有 API 回傳 JSON 格式
   - 錯誤格式：`{"error": "message"}`

## 授權

MIT License
