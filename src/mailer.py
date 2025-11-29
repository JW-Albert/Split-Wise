import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# 從 ENV/.env 載入環境變數
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ENV', '.env')
load_dotenv(env_path)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def send_otp_email(email, otp):
    """發送 OTP 驗證碼到指定 email"""
    if not SMTP_USER or not SMTP_PASS:
        raise ValueError("SMTP credentials not configured in .env")
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = email
    msg['Subject'] = "分帳工具驗證碼"
    
    body = f"""
    您的驗證碼是：{otp}
    
    此驗證碼將在 10 分鐘後過期。
    請勿將此驗證碼分享給他人。
    """
    
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        text = msg.as_string()
        server.sendmail(SMTP_USER, email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

