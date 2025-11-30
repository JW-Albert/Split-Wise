# Split-Wise Expense Sharing Tool

**Version: 1.2.0**

A multi-person expense sharing tool that supports Email registration/OTP login, room management, expense tracking, and automatic settlement.

## Features

- Email + OTP verification login (no password required)
- User name system (set during registration, displayed site-wide)
- Room management system (create, delete)
- Expense tracking and splitting (add, edit, delete)
- Support for advance payments (payer can be excluded from participants)
- Automatic settlement feature (two-pointer pairing algorithm)
- Permission management (admins can view all rooms)
- Admin user management features (add, edit, delete users, set/remove admin privileges)
- Unauthenticated redirect (page requests redirect to login page)
- Data export functionality (export expense records and settlement results as CSV, Excel compatible)
- Database backup functionality (admins can export SQLite database)
- Auto-startup on boot (supports Linux systemd and Windows)
- Display total expenses and individual member expenses
- SQL Injection protection (all queries use parameterized queries)
- Modern UI (TailwindCSS + Alpine.js)
- Cloudflare Tunnel support (ProxyFix middleware)

## Tech Stack

- **Backend**: Python + Flask
- **Database**: SQLite3 (parameterized queries)
- **Frontend**: HTML + TailwindCSS + Alpine.js
- **Templates**: Jinja2
- **Auth**: Email + 6-digit OTP
- **Config**: python-dotenv (.env)

## Installation and Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` and create a `.env` file in the `ENV/` folder:

```bash
# If the project has .env.example, copy it
cp .env.example ENV/.env

# Or manually create a .env file in the ENV/ folder
```

`.env` file content:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

ADMIN_EMAIL=admin@example.com
ADMIN_NAME=Administrator
SECRET_KEY=your-secret-key-here-change-this-to-random-string
```

**Important Notes**:
- The `.env` file must be placed in the `ENV/` folder
- Gmail requires an "App Password" instead of a regular password
- `SECRET_KEY` should be set to a random string (used for session signing)
- The email set in `ADMIN_EMAIL` will have administrator privileges
- `ADMIN_NAME` is the display name for the administrator (optional, defaults to "Administrator")

### 3. Initialize Database

The database and tables will be automatically created when running the application:

```bash
# Run directly with Python
python src/app.py

# Or use the provided script (Linux/Mac)
bash run.sh
```

The database file `splitwise.db` will be automatically created in the project root directory.

## Usage

### Starting the Application

```bash
# Method 1: Run directly with Python
python src/app.py

# Method 2: Use the provided script (Linux/Mac)
bash run.sh

# Method 3: Run in a virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
python src/app.py
```

The application will start at `http://localhost:5000`.

### Setting up Auto-Startup

#### Linux (systemd)

1. **Install Service**
   ```bash
   cd boot
   sudo bash install_service.sh
   ```

2. **Service Management**
   ```bash
   # Start service
   sudo systemctl start splitwise
   
   # Stop service
   sudo systemctl stop splitwise
   
   # Restart service
   sudo systemctl restart splitwise
   
   # Check status
   sudo systemctl status splitwise
   
   # View logs
   sudo journalctl -u splitwise -f
   
   # Disable auto-startup
   sudo systemctl disable splitwise
   ```

3. **Uninstall Service**
   ```bash
   cd boot
   sudo bash uninstall_service.sh
   ```

#### Windows

1. Copy `boot/start_windows.bat` to the Windows Startup folder:
   - Press `Win + R` to open the Run dialog
   - Type `shell:startup` and press Enter
   - Place a shortcut to `start_windows.bat` in this folder

2. Or use Task Scheduler to set up automatic execution on boot

### Usage Flow

1. **Login/Register**
   - Visit `/login`
   - Enter your email
   - The system will send a 6-digit verification code to your email
   - Enter the verification code on the `/verify` page
   - First-time registrants or users without a name will be prompted to enter a username
   - Complete the process to log in

2. **Create Room**
   - After logging in, go to the room list page
   - Click "Create New Room"
   - Enter a room name (e.g., "Japan Trip 2025")

3. **Invite Members**
   - Go to the room details page
   - Enter an email in the "Invite Members" section
   - Click the "Invite" button

4. **Add Expense**
   - Fill out the expense form on the room details page
   - Enter title, amount, payer, and participants
   - The payer can be excluded from participants (supports advance payment scenarios)
   - The system will automatically split the amount equally among all participants

4-1. **Edit Expense**
   - Room members or administrators can click the "Edit" button on expense records
   - Modify title, amount, payer, or participants
   - The settlement results will be automatically recalculated after updating

5. **View Settlement**
   - Check the "Settlement Results" section at the bottom of the room details page
   - The system will automatically calculate each person's payable/receivable amount
   - Display payment suggestions (who should pay whom)

6. **Delete Room**
   - Room owners or administrators can delete rooms from the room list or room details page
   - Deleting a room will also delete all related expense records and member relationships

7. **Delete Expense Record**
   - Room members or administrators can delete any expense record
   - The settlement results will be automatically updated after deletion

8. **Export Data**
   - Click the "Export CSV" button in the expense records section to export all expense records as a CSV file
   - Click the "Export CSV" button in the settlement results section to export settlement results (balances and payment suggestions) as a CSV file
   - The exported CSV files support Excel and correctly display Chinese characters

## API Endpoints

### Authentication

- `POST /api/auth/send-otp` - Send verification code
- `POST /api/auth/resend-otp` - Resend verification code
- `POST /api/auth/verify-otp` - Verify OTP
- `POST /api/auth/set-name` - Set user name (for first-time registration)
- `GET /api/auth/me` - Get current user information (including name)
- `POST /api/auth/logout` - Logout

### Room Related

- `GET /api/rooms` - Get room list
- `POST /api/rooms` - Create new room
- `GET /api/rooms/<room_id>` - Get room details
- `DELETE /api/rooms/<room_id>` - Delete room (owner or admin only)
- `POST /api/rooms/<room_id>/invite` - Invite member

### Expense Related

- `GET /api/rooms/<room_id>/expenses` - Get expense list
- `POST /api/rooms/<room_id>/expenses` - Add expense
- `PUT /api/rooms/<room_id>/expenses/<expense_id>` - Update expense record (room members or admin only)
- `DELETE /api/rooms/<room_id>/expenses/<expense_id>` - Delete expense record (room members or admin only)
- `GET /api/rooms/<room_id>/export/expenses` - Export expense records as CSV

### Settlement Related

- `GET /api/rooms/<room_id>/settlement` - Get settlement results

### Export Related

- `GET /api/rooms/<room_id>/export/expenses` - Export expense records as CSV (room members or admin only)
- `GET /api/rooms/<room_id>/export/settlement` - Export settlement results as CSV (room members or admin only)

### Admin Management

- `GET /admin/users` - Get all user list (admin only)
- `POST /admin/users` - Create new user (admin only)
- `PUT /admin/users/<user_email>` - Update user name (admin only)
- `DELETE /admin/users/<user_email>` - Delete user (admin only)
- `POST /admin/users/<user_email>/set-admin` - Set user as administrator (admin only)
- `POST /admin/users/<user_email>/remove-admin` - Remove user administrator privileges (admin only)
- `GET /admin/export-db` - Export SQLite database backup (admin only)
- `GET /admin` - Admin management page

## Database Schema

### users
- `email` (PRIMARY KEY)
- `name` (user name, can be NULL)
- `password_hash` (reserved field)
- `verified` (0 or 1)
- `created_at`

### admins
- `email` (PRIMARY KEY)

### login_tokens
- `email`
- `otp` (6-digit number)
- `expires_at` (valid for 10 minutes)

### rooms
- `id` (8-character token)
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

## Security

### SQL Injection Protection

All SQL queries use parameterized queries:

```python
# Correct
cursor.execute("SELECT * FROM users WHERE email=?", (email,))

# Wrong (forbidden)
cursor.execute(f"SELECT * FROM users WHERE email='{email}'")
```

### Session Security

- Use `SECRET_KEY` to sign sessions
- Sessions store user email
- All endpoints requiring authentication use the `@login_required` decorator
- Unauthenticated users accessing pages are automatically redirected to the login page
- API requests from unauthenticated users return JSON errors (401)

### OTP Security

- 6-digit random number
- 10-minute validity period
- Regenerated on each login/registration

## Permission Management

### Administrator

- Users whose email matches `ADMIN_EMAIL`, or users in the `admins` table
- Can view all rooms
- Can manage all rooms
- Can access the `/admin` management page
- Can add, edit, and delete user accounts
- Can modify any user's name
- Can set/remove administrator privileges for other users
- Can export SQLite database backups

### Regular Users

- Can only view/edit rooms they own or participate in
- Can create their own rooms
- Can delete rooms they own
- Can invite others to join rooms
- Can edit and delete expense records in rooms (must be a room member)

## Settlement Algorithm

Uses a two-pointer pairing algorithm:

1. Calculate each person's total payments (total_paid)
2. Calculate each person's share (total_share)
3. Calculate balance (balance = total_paid - total_share)
4. Separate creditors (balance > 0) and debtors (balance < 0)
5. Use two-pointer pairing to minimize the number of payments

## Project Structure

```
Split-Wise/
├── src/                   # Source code directory
│   ├── app.py            # Main application
│   ├── database.py      # Database initialization
│   ├── models.py        # Data models and utility functions
│   ├── auth.py          # Authentication and permission checks
│   ├── calculations.py # Settlement algorithm
│   ├── mailer.py        # SMTP email sending
│   ├── templates/       # HTML templates
│   │   ├── login.html
│   │   ├── verify.html
│   │   ├── rooms.html
│   │   ├── room.html
│   │   ├── admin.html
│   │   └── error.html
│   └── static/          # Static resources
│       ├── style.css
│       ├── main.js
│       └── bill.png
├── boot/                 # Auto-startup scripts
│   ├── splitwise.service # Linux systemd service configuration file
│   ├── install_service.sh # Linux installation script
│   ├── uninstall_service.sh # Linux uninstallation script
│   └── start_windows.bat # Windows startup script
├── ENV/                  # Environment variables folder
│   └── .env             # Environment variables file (not added to git)
├── venv/                 # Python virtual environment (not added to git)
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables example file
├── .gitignore           # Git ignore rules
├── run.sh               # Startup script (Linux/Mac)
├── deploy.sh            # Deployment script (Linux/Mac)
├── splitwise.db         # SQLite database (auto-generated, not added to git)
└── README.md            # Project documentation
```

## Development Notes

1. **Never use f-strings to construct SQL**
   - All SQL must use `?` parameterization
   - For dynamic SQL, use string concatenation with `?` placeholders, not values

2. **Environment Variables**
   - All sensitive information is loaded from `ENV/.env`
   - The `.env` file must be placed in the `ENV/` folder
   - `ENV/.env` should not be added to version control (already set in .gitignore)
   - Use `.env.example` as a template

3. **Error Handling**
   - All APIs return JSON format
   - Error format: `{"error": "message"}`

## Version History

### 1.2.0 (2025-11-29)

- Added auto-startup scripts
  - Linux (systemd) service configuration and installation/uninstallation scripts
  - Windows startup batch file
- Admin feature enhancements
  - Admins can set other users as administrators
  - Admins can remove administrator privileges from other users
  - Admins can export SQLite database backups
- Export feature enhancements
  - Settlement results CSV export includes complete expense records
  - Exported CSV files include: expense records, per-person balances, payment suggestions
- Expense statistics on room details page
  - Display total expense amount
  - Display each member's expense amount

### 1.1.0 (2025-11-29)

- Admin feature enhancements
  - Admins can set other users as administrators
  - Admins can remove administrator privileges from other users
  - Admins can export SQLite database backups
- Export feature enhancements
  - Settlement results CSV export includes complete expense records
  - Exported CSV files include: expense records, per-person balances, payment suggestions

### 1.0.0 (2025-11-29)

- Initial version release
- Email + OTP verification code login system
- User name functionality (set during registration, displayed site-wide)
- Room management system (create, delete)
- Expense tracking and splitting (add, edit, delete)
- Support for advance payments (payer can be excluded from participants)
- Automatic settlement feature (two-pointer pairing algorithm)
- Data export functionality (export expense records and settlement results as CSV, Excel compatible)
- Admin user management functionality (add, edit, delete users)
- Permission management (owners/admins can delete rooms, members/admins can edit and delete expenses)
- Unauthenticated redirect (page requests redirect to login page, API returns JSON errors)
- SQL Injection protection (parameterized queries)
- Cloudflare Tunnel support (ProxyFix middleware)

## License

MIT License

