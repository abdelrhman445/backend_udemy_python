"""
Email Service - Gmail OAuth2
🔄 من googleapis (Node.js) → google-auth-library + httpx (Python)
"""

import os
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest

log = logging.getLogger("RILLZO")

GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _get_access_token() -> str:
    """قراءة المتغيرات وقت التشغيل مش وقت الـ import"""
    creds = Credentials(
        token=None,
        refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
        client_id=os.getenv("GMAIL_CLIENT_ID"),
        client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
        token_uri=os.getenv("GMAIL_TOKEN_URI", "https://oauth2.googleapis.com/token")
    )
    creds.refresh(GoogleRequest())
    return creds.token


def _build_email_message(to_email: str, otp: str) -> str:
    msg = MIMEMultipart("alternative")
    msg["To"]      = to_email
    msg["Subject"] = "كود تفعيل حسابك - Udemy Coupons"

    html_content = f"""
    <div dir="rtl" style="font-family: Arial; text-align: center; border: 2px solid #a435f0; padding: 20px;">
        <h2>مرحباً بك في Udemy Coupons</h2>
        <p>كود التفعيل الخاص بك هو:</p>
        <h1 style="background: #f0f0f0; color: #a435f0; padding: 10px;">{otp}</h1>
        <p style="color: #888; font-size: 12px;">صالح لمدة 10 دقائق</p>
    </div>
    """

    msg.attach(MIMEText(html_content, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return raw


async def send_otp(email: str, otp: str) -> None:
    try:
        # التحقق إن البيانات موجودة قبل المحاولة
        if not all([
            os.getenv("GMAIL_CLIENT_ID"),
            os.getenv("GMAIL_CLIENT_SECRET"),
            os.getenv("GMAIL_REFRESH_TOKEN")
        ]):
            log.warning("⚠️ بيانات Gmail غير مكتملة في الـ .env")
            return

        access_token = _get_access_token()
        raw_message  = _build_email_message(email, otp)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GMAIL_API_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json"
                },
                json={"raw": raw_message},
                timeout=15
            )

        if response.status_code == 200:
            log.info("✅ الإيميل وصل بنجاح!")
        else:
            log.error(f"❌ فشل إرسال الإيميل: {response.status_code} - {response.text}")

    except Exception as e:
        log.error(f"❌ فشل إرسال الجيميل: {e}")
