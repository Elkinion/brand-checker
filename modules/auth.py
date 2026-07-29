from __future__ import annotations
import time
import bcrypt
import streamlit as st
from modules.config import APP_PASSWORD_HASH

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 60


def _check_password(pw: str) -> bool:
    if not APP_PASSWORD_HASH or not pw:
        return False
    try:
        return bcrypt.checkpw(pw.encode("utf-8"), APP_PASSWORD_HASH.encode("utf-8"))
    except Exception:
        return False


def _init_state() -> None:
    st.session_state.setdefault("auth_ok", False)
    st.session_state.setdefault("auth_attempts", 0)
    st.session_state.setdefault("auth_locked_until", 0.0)


def require_login() -> bool:
    _init_state()
    if st.session_state.auth_ok:
        return True

    st.markdown(
        "<h2 style='text-align:center; margin-top:2rem;'>Brand Checker</h2>"
        "<p style='text-align:center; color:#6B7280;'>Acceso restringido</p>",
        unsafe_allow_html=True,
    )

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        now = time.time()
        locked_for = st.session_state.auth_locked_until - now
        if locked_for > 0:
            st.error(f"Demasiados intentos. Esperá {int(locked_for)}s.")
            st.stop()

        with st.form("login", clear_on_submit=True):
            pw = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Entrar", width="stretch")

        # --- Diagnóstico temporal ---
        with st.expander("🔧 Diagnóstico (temporal — borrar después)"):
            h = APP_PASSWORD_HASH or ""
            if not h:
                st.error("APP_PASSWORD_HASH está VACÍO — la app no lee ningún hash.")
            else:
                st.write(f"- Largo del hash: **{len(h)}** (bcrypt esperado: 60)")
                st.write(f"- Empieza con: `{h[:7]}` (debe ser `$2b$12$`)")
                st.write(f"- Termina con: `...{h[-6:]}`")
                st.write(f"- ¿Empieza con `$2b$` o `$2a$`?: **{h.startswith(('$2b$','$2a$','$2y$'))}**")

        if submit:
            if _check_password(pw):
                st.session_state.auth_ok = True
                st.session_state.auth_attempts = 0
                st.rerun()
            else:
                st.session_state.auth_attempts += 1
                remaining = MAX_ATTEMPTS - st.session_state.auth_attempts
                if remaining <= 0:
                    st.session_state.auth_locked_until = now + LOCKOUT_SECONDS
                    st.session_state.auth_attempts = 0
                    st.error(f"Cuenta bloqueada {LOCKOUT_SECONDS}s.")
                else:
                    st.error(f"Contraseña incorrecta. {remaining} intento(s) restantes.")

    st.stop()
    return False


def logout_button() -> None:
    if st.sidebar.button("Cerrar sesión", width="stretch"):
        for k in ("auth_ok", "auth_attempts", "auth_locked_until"):
            st.session_state.pop(k, None)
        st.rerun()
