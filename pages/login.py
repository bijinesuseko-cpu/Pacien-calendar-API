import streamlit as st
from auth_handler import build_google_auth_url, handle_oauth_callback, is_authenticated

st.set_page_config(page_title="Вход", page_icon="🔐", layout="centered")

LOGIN_PAGE_URL = st.secrets["google"].get("redirect_uri")

if not LOGIN_PAGE_URL:
    st.error("Настройте redirect_uri в Secrets")
    st.stop()

# Если уже авторизован — редирект на главную
if is_authenticated():
    st.success("✓ Уже авторизован")
    st.markdown(
        "<meta http-equiv='refresh' content='0; url=/'>",
        unsafe_allow_html=True,
    )
    st.button("Перейти в приложение", on_click=lambda: st.switch_page("app.py"))
    st.stop()

# ── OAuth callback ──
code = None
try:
    raw = st.query_params.get("code")
    code = raw[0] if isinstance(raw, list) else raw
except Exception:
    try:
        raw = st.experimental_get_query_params().get("code", [None])
        code = raw[0] if isinstance(raw, list) else raw
    except Exception:
        pass

if code:
    st.info(f"🔄 Обработка кода авторизации...")
    success = handle_oauth_callback(code, LOGIN_PAGE_URL)
    if success:
        st.success("✅ Вход выполнен!")
        st.markdown(
            "<meta http-equiv='refresh' content='1; url=/'>",
            unsafe_allow_html=True,
        )
        st.button("Перейти в приложение", on_click=lambda: st.switch_page("app.py"))
    else:
        st.error("❌ Ошибка обмена кода на токен. Попробуйте снова.")
        st.markdown(
            "<a href='/login' target='_self' "
            "style='display:inline-block;background:#dc2626;color:#fff;"
            "padding:8px 20px;border-radius:8px;text-decoration:none;"
            "font-weight:600;'>Повторить вход</a>",
            unsafe_allow_html=True,
        )
    st.stop()

# ── Debug info ──
if st.query_params:
    st.caption(f"Query params: {dict(st.query_params)}")

# ── Кнопка логина ──
st.markdown(
    "<div style='text-align:center; padding:2rem 0;'>"
    "<div style='font-size:3rem; margin-bottom:1rem;'>🔐</div>"
    "<h2 style='color:var(--text-primary);'>Вход в систему</h2>"
    "<p style='color:var(--text-secondary);'>Войдите через Google для доступа к записям</p>"
    "</div>",
    unsafe_allow_html=True,
)

auth_url = build_google_auth_url(LOGIN_PAGE_URL)

st.markdown(
    f"""
    <div style="display:flex;justify-content:center;padding:1rem 0;">
        <a href="{auth_url}" target="_self"
           style="background:#dc2626;color:#fff;border:none;border-radius:8px;
                  padding:10px 32px;font-size:15px;font-weight:600;
                  font-family:Inter,-apple-system,sans-serif;cursor:pointer;
                  text-decoration:none;display:inline-flex;align-items:center;gap:10px;
                  box-shadow:0 2px 6px rgba(220,38,38,0.35);">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5"
                 stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="8" r="4"/>
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            </svg>
            Войти через Google
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
