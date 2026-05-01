import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from auth import init_firebase, get_all_users, get_activity_logs, log_activity
import datetime

def show_admin_dashboard():
    st.markdown("# 👑 Admin Dashboard")
    st.markdown("##### User management & activity monitoring")
    st.markdown("---")

    db = init_firebase()

    # ── Fetch data ────────────────────────────────────────────────────────────
    with st.spinner("Loading data..."):
        users = get_all_users(db)
        logs  = get_activity_logs(db, limit=300)

    users_df = pd.DataFrame(users) if users else pd.DataFrame()
    logs_df  = pd.DataFrame(logs)  if logs  else pd.DataFrame()

    # ── KPI Row ───────────────────────────────────────────────────────────────
    total_users     = len(users_df)
    flagged_users   = len(users_df[users_df.get('suspicious_activity',
                          pd.Series([False]*len(users_df))).fillna(False)]) \
                      if not users_df.empty and 'suspicious_activity' in users_df.columns else 0
    total_logins    = len(logs_df[logs_df['action'] == 'login_success']) \
                      if not logs_df.empty else 0
    failed_attempts = len(logs_df[logs_df['action'] == 'failed_otp']) \
                      if not logs_df.empty else 0

    k1, k2, k3, k4 = st.columns(4)
    cards = [
        (k1, total_users,     "#00d4ff", "Total Users"),
        (k2, total_logins,    "#44ff88", "Successful Logins"),
        (k3, failed_attempts, "#ffaa00", "Failed OTP Attempts"),
        (k4, flagged_users,   "#ff4444", "⚠️ Flagged Users"),
    ]
    for col, val, color, label in cards:
        with col:
            st.markdown(f"""<div style="background:linear-gradient(135deg,#1a2332,#1e2d40);
                border:1px solid #2a4060;border-radius:16px;padding:20px;text-align:center;">
                <div style="font-size:2rem;font-weight:700;color:{color}">{val}</div>
                <div style="font-size:0.8rem;color:#8899aa;text-transform:uppercase;
                            letter-spacing:1px;margin-top:4px">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["👥 Users", "📋 Activity Logs", "📊 Analytics"])

    # ── TAB 1: Users ──────────────────────────────────────────────────────────
    with tab1:
        st.markdown("### All Registered Users")
        if users_df.empty:
            st.info("No users registered yet.")
        else:
            display_cols = [c for c in ['name', 'email', 'role', 'created_at',
                                         'is_active', 'suspicious_activity',
                                         'flag_reason'] if c in users_df.columns]
            display = users_df[display_cols].copy()

            if 'is_active' in display.columns:
                display['is_active'] = display['is_active'].map(
                    {True: '✅ Active', False: '❌ Suspended'})
            if 'suspicious_activity' in display.columns:
                display['suspicious_activity'] = display['suspicious_activity'].fillna(False).map(
                    {True: '🚨 Flagged', False: '✅ Clean'})

            st.dataframe(display, use_container_width=True, hide_index=True)

            # Suspend / unsuspend user
            st.markdown("### ⚙️ Manage User")
            target_email = st.text_input("Enter user email to manage")
            mc1, mc2 = st.columns(2)
            with mc1:
                if st.button("🔴 Suspend User", use_container_width=True):
                    if target_email:
                        db.collection("users").document(target_email.lower()).update(
                            {"is_active": False})
                        log_activity(db, target_email, "suspended_by_admin",
                                     status="warning",
                                     details=f"Suspended by {st.session_state.user_email}")
                        st.success(f"User {target_email} suspended.")
                        st.rerun()
            with mc2:
                if st.button("🟢 Reactivate User", use_container_width=True):
                    if target_email:
                        db.collection("users").document(target_email.lower()).update(
                            {"is_active": True, "suspicious_activity": False})
                        st.success(f"User {target_email} reactivated.")
                        st.rerun()

    # ── TAB 2: Activity Logs ──────────────────────────────────────────────────
    with tab2:
        st.markdown("### Recent Activity Logs")
        if logs_df.empty:
            st.info("No activity recorded yet.")
        else:
            # Filter controls
            fc1, fc2 = st.columns(2)
            with fc1:
                filter_action = st.selectbox("Filter by Action",
                    ['All'] + sorted(logs_df['action'].unique().tolist()))
            with fc2:
                filter_status = st.selectbox("Filter by Status",
                    ['All'] + sorted(logs_df['status'].unique().tolist()))

            filtered_logs = logs_df.copy()
            if filter_action != 'All':
                filtered_logs = filtered_logs[filtered_logs['action'] == filter_action]
            if filter_status != 'All':
                filtered_logs = filtered_logs[filtered_logs['status'] == filter_status]

            display_cols = [c for c in ['timestamp', 'email', 'action',
                                         'status', 'details'] if c in filtered_logs.columns]
            display_logs = filtered_logs[display_cols].head(200).copy()

            # Color code status
            def style_status(val):
                colors = {'success': 'color:#44ff88', 'warning': 'color:#ffaa00',
                          'error':   'color:#ff4444', 'info':    'color:#00d4ff'}
                return colors.get(val, '')

            st.dataframe(display_logs, use_container_width=True,
                         hide_index=True, height=400)

            csv = filtered_logs.to_csv(index=False)
            st.download_button("⬇️ Export Logs CSV", csv,
                               "activity_logs.csv", "text/csv")

    # ── TAB 3: Analytics ──────────────────────────────────────────────────────
    with tab3:
        if logs_df.empty:
            st.info("No data to visualize yet.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Action Distribution")
                action_counts = logs_df['action'].value_counts().reset_index()
                action_counts.columns = ['Action', 'Count']
                fig = px.pie(action_counts, values='Count', names='Action',
                             hole=0.5,
                             color_discrete_sequence=px.colors.sequential.Blues_r)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                                  font=dict(color='#aabbcc'),
                                  margin=dict(t=10, b=10))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown("#### Logins by Hour")
                login_logs = logs_df[logs_df['action'] == 'login_success']
                if not login_logs.empty and 'hour' in login_logs.columns:
                    hourly = login_logs.groupby('hour').size().reset_index(name='count')
                    fig2 = px.bar(hourly, x='hour', y='count',
                                  color='count',
                                  color_continuous_scale=['#0066cc', '#00d4ff'],
                                  labels={'hour': 'Hour of Day', 'count': 'Logins'})
                    fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)',
                                       plot_bgcolor='rgba(0,0,0,0)',
                                       font=dict(color='#aabbcc'),
                                       margin=dict(t=10, b=10),
                                       coloraxis_showscale=False)
                    fig2.update_xaxes(gridcolor='#1a2d40')
                    fig2.update_yaxes(gridcolor='#1a2d40')
                    st.plotly_chart(fig2, use_container_width=True)

            # Suspicious users alert
            if 'suspicious_activity' in users_df.columns:
                flagged = users_df[users_df['suspicious_activity'].fillna(False)]
                if not flagged.empty:
                    st.markdown("#### 🚨 Suspicious Users Alert")
                    for _, u in flagged.iterrows():
                        st.markdown(f"""<div style="background:#2d0a0a;border:1px solid #ff4444;
                            border-radius:10px;padding:12px 16px;margin:6px 0;">
                            🚨 <strong>{u.get('email','')}</strong> —
                            {u.get('flag_reason','Suspicious activity detected')} —
                            Flagged at: {u.get('flagged_at','')}
                        </div>""", unsafe_allow_html=True)
