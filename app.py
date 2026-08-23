def check_login():
    if st.session_state.get("authenticated", False):
        return True

    _, col_form, _ = st.columns([1, 1.2, 1])

    with col_form:
        try:
            st.image("assets/logo.png", width=220)
        except Exception:
            st.title("🍦 Kulfi Ops")

        st.subheader("Sign in")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

        if submitted:
            user_clean = str(username).strip()
            pass_clean = str(password).strip()

            # Retrieve and cast secrets safely to strings
            admin_user = str(st.secrets.get("app_username", "admin")).strip()
            admin_pass = str(st.secrets.get("app_password", "")).strip()

            entry_user = str(st.secrets.get("entry_username", "entry")).strip()
            entry_pass = str(st.secrets.get("entry_password", "")).strip()

            if admin_pass and hmac.compare_digest(user_clean, admin_user) and hmac.compare_digest(pass_clean, admin_pass):
                st.session_state["authenticated"] = True
                st.session_state["user_role"] = "admin"
                st.rerun()
            elif entry_pass and hmac.compare_digest(user_clean, entry_user) and hmac.compare_digest(pass_clean, entry_pass):
                st.session_state["authenticated"] = True
                st.session_state["user_role"] = "entry"
                st.rerun()
            else:
                st.error("Incorrect username or password — try again.")

    return False