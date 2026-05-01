import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, auth
import random
import string
import datetime
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── Firebase Init ────────────────────────────────────────────────────────────
def init_firebase():
    if not firebase_admin._apps:
        # Try Streamlit secrets first (for cloud deployment)
        try:
            key_dict = dict(st.secrets["firebase"])
            cred = credentials.Certificate(key_dict)
        except Exception:
            # Fall back to local file
            cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()


# ─── OTP Generator ────────────────────────────────────────────────────────────
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


# ─── Send OTP Email ───────────────────────────────────────────────────────────
def send_otp_email(to_email, otp, purpose="Login"):
    try:
        smtp_email = st.secrets["email"]["address"]
        smtp_pass  = st.secrets["email"]["password"]
    except Exception:
        smtp_email = os.environ.get("EMAIL_ADDRESS", "")
        smtp_pass  = os.environ.get("EMAIL_PASSWORD", "")

    subject = f"🛡️ UPI Fraud Detection — Your OTP for {purpose}"
    body = f"""
    <html><body style="font-family:Arial,sans-serif;background:#0a0e1a;color:#e0f0ff;padding:30px;">
        <div style="max-width:480px;margin:auto;background:#1a2332;border-radius:16px;
                    padding:32px;border:1px solid #2a4060;">
            <h2 style="color:#00d4ff;margin-top:0">🛡️ UPI Fraud Detection System</h2>
            <p style="color:#aabbcc">Your One-Time Password for <strong>{purpose}</strong>:</p>
            <div style="background:#0a0e1a;border-radius:12px;padding:20px;text-align:center;
                        margin:20px 0;border:2px solid #00d4ff;">
                <span style="font-size:2.5rem;font-weight:700;color:#00d4ff;
                             letter-spacing:12px;">{otp}</span>
            </div>
            <p style="color:#8899aa;font-size:0.85rem">
                ⏱️ This OTP is valid for <strong>10 minutes</strong>.<br>
                🔒 Never share this OTP with anyone.<br>
                ❌ If you did not request this, ignore this email.
            </p>
            <hr style="border-color:#2a4060;margin:20px 0">
            <p style="color:#556677;font-size:0.75rem">
                MCA Final Project — GBU Noida
            </p>
        </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_email
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_email, smtp_pass)
        server.sendmail(smtp_email, to_email, msg.as_string())
    return True


# ─── Firestore Helpers ────────────────────────────────────────────────────────
def get_user(db, email):
    doc = db.collection("users").document(email).get()
    return doc.to_dict() if doc.exists else None


def create_user(db, email, name):
    db.collection("users").document(email).set({
        "email":      email,
        "name":       name,
        "created_at": datetime.datetime.now().isoformat(),
        "role":       "user",
        "is_active":  True
    })


def store_otp(db, email, otp, purpose):
    db.collection("otps").document(email).set({
        "otp":        otp,
        "purpose":    purpose,
        "created_at": datetime.datetime.now().isoformat(),
        "expires_at": (datetime.datetime.now() +
                       datetime.timedelta(minutes=10)).isoformat(),
        "used":       False
    })


def verify_otp(db, email, entered_otp):
    doc = db.collection("otps").document(email).get()
    if not doc.exists:
        return False, "OTP not found. Please request a new one."
    data = doc.to_dict()
    if data.get("used"):
        return False, "OTP already used. Please request a new one."
    expires = datetime.datetime.fromisoformat(data["expires_at"])
    if datetime.datetime.now() > expires:
        return False, "OTP expired. Please request a new one."
    if data["otp"] != entered_otp:
        log_failed_attempt(db, email)
        return False, "Incorrect OTP. Please try again."
    # Mark OTP as used
    db.collection("otps").document(email).update({"used": True})
    return True, "OTP verified successfully!"


def log_activity(db, email, action, ip="unknown", status="success", details=""):
    db.collection("activity_logs").add({
        "email":      email,
        "action":     action,
        "status":     status,
        "details":    details,
        "ip":         ip,
        "timestamp":  datetime.datetime.now().isoformat(),
        "hour":       datetime.datetime.now().hour,
        "day":        datetime.datetime.now().strftime("%A")
    })


def log_failed_attempt(db, email):
    # Count recent failed attempts
    from google.cloud.firestore_v1.base_query import FieldFilter
    ten_min_ago = (datetime.datetime.now() -
                   datetime.timedelta(minutes=10)).isoformat()
    logs = db.collection("activity_logs") \
             .where(filter=FieldFilter("email",  "==", email)) \
             .where(filter=FieldFilter("action", "==", "failed_otp")) \
             .where(filter=FieldFilter("timestamp", ">=", ten_min_ago)) \
             .get()
    failed_count = len(logs)
    log_activity(db, email, "failed_otp", status="warning",
                 details=f"Failed attempt #{failed_count + 1}")
    # Flag suspicious if 3+ failures in 10 mins
    if failed_count >= 2:
        db.collection("users").document(email).update({
            "suspicious_activity": True,
            "flagged_at": datetime.datetime.now().isoformat(),
            "flag_reason": f"{failed_count + 1} failed OTP attempts in 10 minutes"
        })


def get_all_users(db):
    return [doc.to_dict() for doc in db.collection("users").stream()]


def get_activity_logs(db, limit=200):
    logs = db.collection("activity_logs") \
             .order_by("timestamp",
                       direction=firestore.Query.DESCENDING) \
             .limit(limit).stream()
    return [doc.to_dict() for doc in logs]
