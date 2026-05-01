import streamlit as st
import datetime
from auth import (init_firebase, get_user, create_user, generate_otp,
                  send_otp_email, store_otp, verify_otp, log_activity)

# ─── Shared CSS (injected once) ───────────────────────────────────────────────
AUTH_CSS = """
<style>
.auth-card {
    background: linear-gradient(135deg, #1a2332 0%, #1e2d40 100%);
    border: 1px solid #2a4060;
    border-radius: 20px;
    padding: 36px 40px;
    max-width: 460px;
    margin: 40px auto;
    box-shadow: 0 8px 40px rgba(0,150,255,0.12);
}
.auth-title {
    font-size: 1.7rem;
    font-weight: 700;
    color: #00d4ff;
    text-align: center;
    margin-bottom: 4px;
}
.auth-subtitle {
    font-size: 0.9rem;
    color: #8899aa;
    text-align: center;
    margin-bottom: 28px;
}
.otp-hint {
    background: #0d1e30;
    border: 1px solid #1a3a50;
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 0.82rem;
    color: #8899aa;
    margin-top: 8px;
}
.flag-badge {
    background: #2d0a0a;
    border: 1px solid #ff4444;
    border-radius: 8px;
    padding: 8px 14px;
    color: #ff8888;
    font-size: 0.82rem;
}
</style>
"""


def show_login_page():
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    db = init_firebase()

    # ── Session state defaults ────────────────────────────────────────────────
    for key, default in [("auth_stage", "entry"), ("auth_email", ""),
                         ("auth_name", ""), ("auth_purpose", "login")]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ════════════════════════════════════════════════════════
    # STAGE 1 — Email entry (login or register)
    # ════════════════════════════════════════════════════════
    if st.session_state.auth_stage == "entry":
        st.markdown("""
        <div class='auth-card'>
            <div class='auth-title'>🛡️ UPI Fraud Detection</div>
            <div class='auth-subtitle'>Secure login — MCA Project by Aryan Jaiswal · Rsmt Varanasi</div>
        </div>""", unsafe_allow_html=True)

        with st.container():
            col = st.columns([1, 2, 1])[1]
            with col:
                tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])

                # ── Login Tab ─────────────────────────────────────────────────
                with tab_login:
                    st.markdown("")
                    email = st.text_input("📧 Email Address",
                                          placeholder="you@gmail.com",
                                          key="login_email")
                    if st.button("Send OTP →", use_container_width=True,
                                 key="login_send"):
                        email = email.strip().lower()
                        if not email or "@" not in email:
                            st.error("Please enter a valid email.")
                        else:
                            user = get_user(db, email)
                            if not user:
                                st.error("No account found. Please register first.")
                            elif not user.get("is_active", True):
                                st.error("Account suspended. Contact admin.")
                            else:
                                otp = generate_otp()
                                store_otp(db, email, otp, "Login")
                                try:
                                    send_otp_email(email, otp, "Login")
                                    st.session_state.auth_email   = email
                                    st.session_state.auth_purpose = "login"
                                    st.session_state.auth_stage   = "otp"
                                    log_activity(db, email, "otp_requested",
                                                 status="success",
                                                 details="Login OTP sent")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to send OTP: {e}")

                # ── Register Tab ──────────────────────────────────────────────
                with tab_register:
                    st.markdown("")
                    reg_name  = st.text_input("👤 Full Name",
                                              placeholder="Aryan Kumar",
                                              key="reg_name")
                    reg_email = st.text_input("📧 Email Address",
                                              placeholder="you@gmail.com",
                                              key="reg_email")
                    if st.button("Register & Send OTP →",
                                 use_container_width=True, key="reg_send"):
                        reg_email = reg_email.strip().lower()
                        reg_name  = reg_name.strip()
                        if not reg_name:
                            st.error("Please enter your name.")
                        elif not reg_email or "@" not in reg_email:
                            st.error("Please enter a valid email.")
                        else:
                            existing = get_user(db, reg_email)
                            if existing:
                                st.warning("Account already exists. Please login.")
                            else:
                                otp = generate_otp()
                                store_otp(db, reg_email, otp, "Registration")
                                try:
                                    send_otp_email(reg_email, otp, "Registration")
                                    st.session_state.auth_email   = reg_email
                                    st.session_state.auth_name    = reg_name
                                    st.session_state.auth_purpose = "register"
                                    st.session_state.auth_stage   = "otp"
                                    log_activity(db, reg_email, "registration_started",
                                                 status="success")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to send OTP: {e}")

    # ════════════════════════════════════════════════════════
    # STAGE 2 — OTP Verification
    # ════════════════════════════════════════════════════════
    elif st.session_state.auth_stage == "otp":
        email   = st.session_state.auth_email
        purpose = st.session_state.auth_purpose

        st.markdown(f"""
        <div class='auth-card'>
            <div class='auth-title'>📨 Enter OTP</div>
            <div class='auth-subtitle'>6-digit code sent to <strong>{email}</strong></div>
        </div>""", unsafe_allow_html=True)

        col = st.columns([1, 2, 1])[1]
        with col:
            otp_input = st.text_input("🔢 Enter 6-digit OTP",
                                      placeholder="123456",
                                      max_chars=6,
                                      key="otp_input")
            st.markdown("""<div class='otp-hint'>
                ⏱️ OTP valid for 10 minutes &nbsp;|&nbsp;
                🔒 Don't share with anyone
            </div>""", unsafe_allow_html=True)
            st.markdown("")

            if st.button("✅ Verify OTP", use_container_width=True):
                if not otp_input or len(otp_input) != 6:
                    st.error("Please enter the 6-digit OTP.")
                else:
                    valid, msg = verify_otp(db, email, otp_input.strip())
                    if valid:
                        if purpose == "register":
                            create_user(db, email, st.session_state.auth_name)
                            log_activity(db, email, "registered",
                                         status="success")
                            st.success("✅ Account created successfully!")
                        # Mark session as logged in
                        user = get_user(db, email)
                        st.session_state.logged_in   = True
                        st.session_state.user_email  = email
                        st.session_state.user_name   = user.get("name", email)
                        st.session_state.user_role   = user.get("role", "user")
                        st.session_state.auth_stage  = "entry"
                        log_activity(db, email, "login_success", status="success")
                        st.rerun()
                    else:
                        st.error(msg)

            st.markdown("")
            if st.button("← Back", use_container_width=True, key="back_btn"):
                st.session_state.auth_stage = "entry"
                st.rerun()

            st.markdown("")
            if st.button("🔄 Resend OTP", use_container_width=True,
                         key="resend_btn"):
                otp = generate_otp()
                store_otp(db, email, otp, purpose.title())
                try:
                    send_otp_email(email, otp, purpose.title())
                    st.success("New OTP sent!")
                    log_activity(db, email, "otp_resent", status="success")
                except Exception as e:
                    st.error(f"Failed: {e}")
