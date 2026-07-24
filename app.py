import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from auth_handler import get_credentials, revoke_token, is_authenticated, login_section
from calendar_manager import fetch_events, create_event, update_event, delete_event, set_attendance, check_availability

WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTH_NAMES = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]
WEEKDAY_FULL = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg-primary: #0e1117;
        --bg-secondary: #161b22;
        --bg-card: #1c2128;
        --bg-hover: #21262d;
        --border: #30363d;
        --border-light: #21262d;
        --text-primary: #e6edf3;
        --text-secondary: #8b949e;
        --text-muted: #6e7681;
        --accent: #58a6ff;
        --accent-subtle: rgba(56,139,253,0.1);
        --success: #3fb950;
        --success-subtle: rgba(63,185,80,0.1);
        --danger: #f85149;
        --danger-subtle: rgba(248,81,73,0.1);
        --warning: #d29922;
        --warning-subtle: rgba(210,153,34,0.1);
    }

    .stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }

    section[data-testid="stSidebar"] {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-light) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdown"] span {
        color: var(--text-secondary) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSuccess"] {
        background: var(--success-subtle) !important;
        border: 1px solid rgba(63,185,80,0.2) !important;
        color: var(--success) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stWarning"] {
        background: var(--warning-subtle) !important;
        border: 1px solid rgba(210,153,34,0.2) !important;
        color: var(--warning) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stError"] {
        background: var(--danger-subtle) !important;
        border: 1px solid rgba(248,81,73,0.2) !important;
        color: var(--danger) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stInfo"] {
        background: var(--accent-subtle) !important;
        border: 1px solid rgba(56,139,253,0.2) !important;
        color: var(--accent) !important;
    }
    section[data-testid="stSidebar"] hr { border-color: var(--border-light) !important; }
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        border-radius: 6px !important;
        font-size: 0.85rem !important;
        padding: 0.35rem 1rem !important;
        transition: all 0.15s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: var(--bg-hover) !important;
        border-color: var(--text-muted) !important;
        color: var(--text-primary) !important;
    }

    h1 { font-weight: 700 !important; letter-spacing: -0.02em !important; color: var(--text-primary) !important; }
    h2, h3 { font-weight: 600 !important; color: var(--text-primary) !important; }
    .stMarkdown p { color: var(--text-secondary) !important; }
    [data-testid="stCaption"] { color: var(--text-muted) !important; }
    hr { border-color: var(--border) !important; opacity: 0.5 !important; }

    div[data-testid="stMetric"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        padding: 16px 20px !important;
    }
    div[data-testid="stMetric"] label { color: var(--text-muted) !important; font-size: 0.8rem !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--text-primary) !important; font-weight: 700 !important; }

    [data-testid="stExpander"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }
    [data-testid="stExpander"] summary { color: var(--text-primary) !important; font-weight: 500 !important; }
    [data-testid="stExpander"][data-testid="stExpander"] details[open] { border-color: var(--accent) !important; }

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px var(--accent) !important;
    }

    .stForm {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: 12px !important;
        padding: 24px !important;
    }

    .stButton > button {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
        transition: all 0.15s ease !important;
    }
    .stButton > button:hover {
        background: var(--bg-hover) !important;
        border-color: var(--text-muted) !important;
    }
    .stButton > button:active { transform: scale(0.98) !important; }

    div[data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: 10px !important; overflow: hidden; }
    div[data-testid="stDataFrame"] table { background: var(--bg-card) !important; }
    div[data-testid="stDataFrame"] th { background: var(--bg-secondary) !important; color: var(--text-secondary) !important; font-weight: 600 !important; text-transform: uppercase !important; font-size: 0.75rem !important; letter-spacing: 0.05em !important; }

    .stRadio > div { gap: 2px !important; }
    .stRadio > div > label {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        transition: all 0.15s ease !important;
    }
    .stRadio > div > label:hover { background: var(--bg-hover) !important; }
    .stRadio > div > label[data-checked="true"] {
        background: var(--accent-subtle) !important;
        border-color: var(--accent) !important;
        color: var(--accent) !important;
    }

    [data-testid="stPopover"] {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }

    .stSuccess { background: var(--success-subtle) !important; border: 1px solid rgba(63,185,80,0.2) !important; color: var(--success) !important; }
    .stError { background: var(--danger-subtle) !important; border: 1px solid rgba(248,81,73,0.2) !important; color: var(--danger) !important; }
    .stWarning { background: var(--warning-subtle) !important; border: 1px solid rgba(210,153,34,0.2) !important; color: var(--warning) !important; }
    .stInfo { background: var(--accent-subtle) !important; border: 1px solid rgba(56,139,253,0.2) !important; color: var(--accent) !important; }

    .block-container { padding-top: 2rem !important; max-width: 1200px !important; }

    .att-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .att-arrived { background: var(--success-subtle); color: var(--success); }
    .att-missed { background: var(--danger-subtle); color: var(--danger); }
    .att-pending { background: var(--accent-subtle); color: var(--accent); }

    /* ─── Action buttons (table/today compact icon buttons) ─── */
    .stButton > button[kind="secondaryFormSubmit"],
    .stButton > button:not([kind="primary"]):not([kind="secondary"]):not([kind="primaryFormSubmit"]) {
        min-width: 30px !important;
        height: 30px !important;
        padding: 0 2px !important;
        font-size: 0.75rem !important;
        border-radius: 6px !important;
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text-secondary) !important;
        transition: all 0.15s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    .stButton > button:not([kind="primary"]):not([kind="secondary"]):not([kind="primaryFormSubmit"]):hover {
        transform: scale(1.15) !important;
        background: var(--bg-hover) !important;
        border-color: var(--text-muted) !important;
        color: var(--text-primary) !important;
    }
    /* Color hints by button text */
    .stButton > button:not([kind]):hover { }
    /* ─── Mobile (≤768px) ─── */
    @media (max-width: 768px) {
        .block-container { max-width: 100% !important; padding: 0.5rem !important; }
        section[data-testid="stSidebar"] { width: 100% !important; min-width: 100% !important; }
        h1 { font-size: 1.3rem !important; }
        h2 { font-size: 1.1rem !important; }
        h3 { font-size: 1rem !important; }
        .stButton > button { font-size: 0.8rem !important; padding: 0.4rem 0.8rem !important; }
        .att-badge { font-size: 0.7rem !important; padding: 1px 6px !important; }
    }
    @media (max-width: 480px) {
        section[data-testid="stSidebar"] > div:first-child { padding: 10px 8px !important; }
        .stMarkdown p { font-size: 0.8rem !important; }
    }
</style>
"""


def format_date_ru(d: date) -> str:
    return f"{d.day} {MONTH_NAMES[d.month]} {d.year}"


def format_weekday_ru(d: date) -> str:
    return WEEKDAY_FULL[d.weekday()]


def attendance_badge(status: str) -> str:
    if status == "arrived":
        return '<span class="att-badge att-arrived">Пришёл</span>'
    elif status == "missed":
        return '<span class="att-badge att-missed">Не пришёл</span>'
    return '<span class="att-badge att-pending">Ожидание</span>'


def attendance_icon(status: str) -> str:
    return {"arrived": "✅", "missed": "❌"}.get(status, "⏳")



def render_today_view(events: list[dict]):
    today_str = date.today().isoformat()
    today_events = [e for e in events if e["date"] == today_str]
    today_events.sort(key=lambda e: e["time"])

    st.markdown(f"### Сегодня · {len(today_events)} записей")

    if not today_events:
        st.info("Нет записей на сегодня")
        return

    for ev in today_events:
        with st.container(border=False):
            c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
            with c1:
                st.markdown(f"**{ev['time']}**")
                st.caption(f"{ev['duration']} мин")
            with c2:
                st.markdown(f"**{ev['client_name']}**")
                info = [ev['service']]
                if ev.get('phone'):
                    info.append(ev['phone'])
                st.caption(" · ".join(info))
                if ev.get('notes'):
                    st.caption(f"📝 {ev['notes']}")
            with c3:
                st.markdown(attendance_badge(ev.get("attendance", "")), unsafe_allow_html=True)
            with c4:
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("✅", key=f"arr_{ev['id']}", help="Пришёл"):
                        set_attendance(ev["id"], "arrived")
                        st.rerun()
                with b2:
                    if st.button("❌", key=f"miss_{ev['id']}", help="Не пришёл"):
                        set_attendance(ev["id"], "missed")
                        st.rerun()
                with b3:
                    if st.button("✏️", key=f"edit_today_{ev['id']}", help="Редактировать"):
                        st.session_state["editing_event"] = ev
                        st.rerun()
        st.divider()


def render_week_view(events: list[dict]):
    if "week_offset" not in st.session_state:
        st.session_state["week_offset"] = 0

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_start = monday + timedelta(weeks=st.session_state["week_offset"])
    week_end = week_start + timedelta(days=6)

    nav1, nav_title, nav2 = st.columns([1, 4, 1])
    with nav1:
        if st.button("←", use_container_width=True):
            st.session_state["week_offset"] -= 1
            st.rerun()
    with nav_title:
        st.markdown(
            f"<div style='text-align:center; padding-top:6px; font-size:1em; color:var(--text-secondary);'>"
            f"{format_date_ru(week_start)} — {format_date_ru(week_end)}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with nav2:
        if st.button("→", use_container_width=True):
            st.session_state["week_offset"] += 1
            st.rerun()

    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    week_date_strs = [d.isoformat() for d in week_dates]

    events_by_date = {ds: [] for ds in week_date_strs}
    for e in events:
        if e["date"] in events_by_date:
            events_by_date[e["date"]].append(e)
    for ds in events_by_date:
        events_by_date[ds].sort(key=lambda e: e["time"])

    cols = st.columns(7)
    for i, (col, d) in enumerate(zip(cols, week_dates)):
        with col:
            is_today = d == today
            color = "var(--accent)" if is_today else "var(--text-muted)"
            st.markdown(
                f"<div style='text-align:center; margin-bottom:8px;'>"
                f"<div style='color:{color}; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>"
                f"{WEEKDAY_NAMES[i]}</div>"
                f"<div style='font-size:1.4em; font-weight:700; color:{color};'>{d.day}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            day_events = events_by_date[d.isoformat()]
            if not day_events:
                st.caption("—")
            else:
                for ev in day_events:
                    icon = attendance_icon(ev.get("attendance", ""))
                    st.markdown(
                        f"<div style='padding:6px 8px; background:var(--bg-card); border:1px solid var(--border); "
                        f"border-radius:6px; margin-bottom:4px; font-size:0.85rem;'>"
                        f"{icon} <b>{ev['time']}</b> {ev['client_name']}<br>"
                        f"<span style='color:var(--text-muted); font-size:0.75rem;'>{ev['service']}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )


def render_table_view(events: list[dict]):
    st.markdown("### Таблица")

    search_query = st.text_input("Поиск", placeholder="Имя или дата (ГГГГ-ММ-ДД)", label_visibility="collapsed")

    filtered = events
    if search_query:
        q = search_query.lower()
        filtered = [e for e in events if q in e["client_name"].lower() or q in e["date"]]

    if not filtered:
        st.info("Записи не найдены")
        return

    for ev in filtered:
        with st.container(border=False):
            c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1.5, 1.5])
            with c1:
                st.markdown(f"**{ev['date']}** {ev['time']}")
                st.caption(f"{ev['duration']} мин")
            with c2:
                st.markdown(f"**{ev['client_name']}**")
                if ev.get('phone'):
                    st.caption(f"📞 {ev['phone']}")
            with c3:
                st.markdown(ev['service'])
                if ev.get('notes'):
                    st.caption(f"📝 {ev['notes']}")
            with c4:
                st.markdown(attendance_badge(ev.get("attendance", "")), unsafe_allow_html=True)
            with c5:
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("✅", key=f"arr_tab_{ev['id']}", help="Пришёл"):
                        set_attendance(ev["id"], "arrived")
                        st.rerun()
                with b2:
                    if st.button("❌", key=f"miss_tab_{ev['id']}", help="Не пришёл"):
                        set_attendance(ev["id"], "missed")
                        st.rerun()
                b3, b4 = st.columns(2)
                with b3:
                    if st.button("✏️", key=f"edit_tab_{ev['id']}", help="Изменить"):
                        st.session_state["editing_event"] = ev
                        st.rerun()
                with b4:
                    if st.button("🗑️", key=f"del_tab_{ev['id']}", help="Удалить"):
                        try:
                            delete_event(ev["id"])
                            st.rerun()
                        except RuntimeError as e:
                            st.error(str(e))
        st.divider()


def render_calendar_view(events: list[dict]):
    today = date.today()

    if "cal_month" not in st.session_state:
        st.session_state["cal_month"] = today.month
    if "cal_year" not in st.session_state:
        st.session_state["cal_year"] = today.year

    col_prev, col_title, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("←", use_container_width=True):
            if st.session_state["cal_month"] == 1:
                st.session_state["cal_month"] = 12
                st.session_state["cal_year"] -= 1
            else:
                st.session_state["cal_month"] -= 1
            st.rerun()
    with col_title:
        month_name = MONTH_NAMES[st.session_state["cal_month"]]
        st.markdown(
            f"<div style='text-align:center; padding-top:6px; font-size:1.1em; font-weight:600; color:var(--text-primary);'>"
            f"{month_name} {st.session_state['cal_year']}"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("→", use_container_width=True):
            if st.session_state["cal_month"] == 12:
                st.session_state["cal_month"] = 1
                st.session_state["cal_year"] += 1
            else:
                st.session_state["cal_month"] += 1
            st.rerun()

    cal_year = st.session_state["cal_year"]
    cal_month = st.session_state["cal_month"]

    first_day = date(cal_year, cal_month, 1)
    if cal_month == 12:
        last_day = date(cal_year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(cal_year, cal_month + 1, 1) - timedelta(days=1)

    start_weekday = first_day.weekday()
    total_days = (last_day - first_day).days + 1

    events_by_date = {}
    for e in events:
        events_by_date.setdefault(e["date"], []).append(e)

    # Day headers
    cols = st.columns(7)
    for i, col in enumerate(cols):
        with col:
            st.markdown(
                f"<div style='text-align:center; font-size:0.7rem; font-weight:600; "
                f"color:var(--text-muted); text-transform:uppercase; letter-spacing:0.05em; padding:6px;'>"
                f"{WEEKDAY_NAMES[i]}</div>",
                unsafe_allow_html=True,
            )

    # Calendar grid
    cells = [None] * start_weekday + list(range(1, total_days + 1))

    for week_start in range(0, len(cells), 7):
        week_days = cells[week_start:week_start + 7]
        cols = st.columns(7)
        for i, col in enumerate(cols):
            with col:
                if i < len(week_days) and week_days[i] is not None:
                    day_num = week_days[i]
                    d = date(cal_year, cal_month, day_num)
                    day_str = d.isoformat()
                    is_today = d == today
                    is_selected = st.session_state.get("cal_selected_day") == day_str
                    day_events = events_by_date.get(day_str, [])

                    # Day number button
                    btn_type = "primary" if is_today or is_selected else "secondary"
                    if st.button(str(day_num), key=f"cal_day_{day_str}", use_container_width=True, type=btn_type):
                        st.session_state["cal_selected_day"] = day_str
                        st.session_state["cal_selected_date"] = d
                        st.rerun()

                    # Event dots
                    for ev in day_events[:3]:
                        icon = attendance_icon(ev.get("attendance", ""))
                        st.markdown(
                            f"<div style='font-size:0.65rem; padding:1px 4px; margin:1px 0; "
                            f"overflow:hidden; text-overflow:ellipsis; white-space:nowrap; "
                            f"color:var(--text-secondary);'>"
                            f"{icon} {ev['time']}</div>",
                            unsafe_allow_html=True,
                        )
                    if len(day_events) > 3:
                        st.markdown(f"<div style='font-size:0.6rem; color:var(--text-muted);'>+{len(day_events) - 3}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div style='height:60px;'></div>", unsafe_allow_html=True)

    # ── Selected day view ──
    if "cal_selected_day" in st.session_state:
        selected = st.session_state["cal_selected_day"]
        selected_d = st.session_state.get("cal_selected_date", today)
        day_events = [e for e in events if e["date"] == selected]

        st.divider()
        st.markdown(f"### {selected_d.day} {MONTH_NAMES[selected_d.month]} {selected_d.year} — {format_weekday_ru(selected_d)}")

        if day_events:
            for ev in day_events:
                with st.container(border=False):
                    c1, c2, c3, c4 = st.columns([1, 3, 2, 1.5])
                    with c1:
                        st.markdown(f"**{ev['time']}**")
                        st.caption(f"{ev['duration']} мин")
                    with c2:
                        st.markdown(f"**{ev['client_name']}**")
                        info = [ev['service']]
                        if ev.get('phone'):
                            info.append(ev['phone'])
                        st.caption(" · ".join(info))
                        if ev.get('notes'):
                            st.caption(f"📝 {ev['notes']}")
                    with c3:
                        st.markdown(attendance_badge(ev.get("attendance", "")), unsafe_allow_html=True)
                    with c4:
                        c4a, c4b, c4c = st.columns(3)
                        with c4a:
                            if st.button("✅", key=f"arr_cal_{ev['id']}", help="Пришёл"):
                                set_attendance(ev["id"], "arrived")
                                st.rerun()
                        with c4b:
                            if st.button("❌", key=f"miss_cal_{ev['id']}", help="Не пришёл"):
                                set_attendance(ev["id"], "missed")
                                st.rerun()
                        with c4c:
                            if st.button("✏️", key=f"edit_cal_{ev['id']}", help="Изменить"):
                                st.session_state["editing_event"] = ev
                                st.rerun()
                st.divider()
        else:
            st.info("Нет записей на этот день")

        # ── Кнопка добавления на выбранный день ──
        st.divider()
        with st.popover("+ Записать на этот день", use_container_width=True):
            booking_form(default_date=selected_d, form_key="booking_form_cal", booked_slots=day_events)


def edit_event_form():
    ev = st.session_state.get("editing_event")
    if not ev:
        return

    st.markdown(f"### ✏️ {ev['client_name']}")

    with st.form("edit_event_form"):
        col1, col2 = st.columns(2)

        with col1:
            client_name = st.text_input("Имя клиента", value=ev["client_name"])
            phone = st.text_input("Телефон", value=ev.get("phone", ""))
            service = st.selectbox("Услуга", ["Первичный прием", "Повторный прием"], index=0 if ev.get("service") == "Первичный прием" else 1)

        with col2:
            booking_date = st.date_input("Дата", value=date.fromisoformat(ev["date"]))
            booking_time = st.time_input("Время", value=datetime.strptime(ev["time"], "%H:%M").time())
            duration = st.selectbox("Длительность", [30, 60, 90, 120], index=[30, 60, 90, 120].index(ev.get("duration", 60)))

        notes = st.text_area("Заметка", value=ev.get("notes", ""), height=80)

        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            submitted = st.form_submit_button("Сохранить", use_container_width=True, type="primary")
        with c2:
            if st.form_submit_button("Отмена", use_container_width=True):
                del st.session_state["editing_event"]
                st.rerun()
        with c3:
            if st.form_submit_button("🗑️", use_container_width=True):
                try:
                    delete_event(ev["id"])
                    del st.session_state["editing_event"]
                    st.rerun()
                except RuntimeError as e:
                    st.error(str(e))

        if submitted:
            if not client_name.strip():
                st.error("Укажите имя клиента.")
                return

            date_str = booking_date.isoformat()
            time_str = booking_time.strftime("%H:%M")

            try:
                update_event(ev["id"], client_name.strip(), phone.strip(), service, date_str, time_str, duration, notes)
                del st.session_state["editing_event"]
                st.rerun()
            except (ValueError, RuntimeError) as e:
                st.error(str(e))


def booking_form(default_date: date | None = None, form_key: str = "booking_form", booked_slots: list[dict] | None = None):
    with st.form(form_key, clear_on_submit=True):
        st.markdown("### Новая запись")

        col1, col2 = st.columns(2)

        with col1:
            client_name = st.text_input("Имя клиента", placeholder="Иван Иванов")
            phone = st.text_input("Телефон", placeholder="+7 (999) 123-45-67")
            service = st.selectbox("Услуга", ["Первичный прием", "Повторный прием"])

        with col2:
            booking_date = st.date_input("Дата", value=default_date or date.today())
            # С 11:00 до 18:30 с шагом 30 мин
            time_options = [f"{h:02d}:{m:02d}" for h in range(11, 19) for m in (0, 30)]

            # Фильтруем занятые слоты
            if booked_slots and default_date:
                def _is_free(t: str, dur: int = 60) -> bool:
                    cand_start = datetime.strptime(f"{default_date.isoformat()} {t}", "%Y-%m-%d %H:%M")
                    cand_end = cand_start + timedelta(minutes=dur)
                    for b in booked_slots:
                        b_start = datetime.strptime(f"{default_date.isoformat()} {b['time']}", "%Y-%m-%d %H:%M")
                        b_end = b_start + timedelta(minutes=b["duration"])
                        if cand_start < b_end and cand_end > b_start:
                            return False
                    return True
                time_options = [t for t in time_options if _is_free(t, 60)]

            time_idx = 0
            now = datetime.now()
            default_time = f"{now.hour:02d}:{now.minute // 30 * 30:02d}"
            if default_time in time_options:
                time_idx = time_options.index(default_time)
            elif time_options:
                time_idx = 0
            booking_time_str = st.selectbox("Время", time_options, index=time_idx) if time_options else st.empty()
            if time_options:
                booking_time = datetime.strptime(booking_time_str, "%H:%M").time()
            else:
                st.warning("На этот день нет свободных слотов.")
                st.form_submit_button("Записать", use_container_width=True, type="primary", disabled=True)
                return
            duration = st.selectbox("Длительность", [30, 60, 90, 120], index=1)

        notes = st.text_area("Заметка", placeholder="Дополнительная информация...", height=80)

        submitted = st.form_submit_button("Записать", use_container_width=True, type="primary")

        if submitted:
            if not client_name.strip():
                st.error("Укажите имя клиента.")
                return

            date_str = booking_date.isoformat()
            time_str = booking_time.strftime("%H:%M")

            # Проверка что запись не выходит за 18:00
            hour = booking_time.hour
            if hour + duration // 60 > 18 or (hour + duration // 60 == 18 and booking_time.minute + duration % 60 > 0):
                st.error(f"Запись на {booking_time_str} длительностью {duration} мин выходит за пределы рабочего дня (до 18:00).")
                return

            try:
                if not check_availability(date_str, time_str, duration):
                    st.error(f"Слот {date_str} в {time_str} уже занят.")
                    return

                create_event(client_name.strip(), phone.strip(), service, date_str, time_str, duration, notes)
                st.rerun()
            except (ValueError, RuntimeError) as e:
                st.error(str(e))


def main():
    st.set_page_config(page_title="Календарь записей", page_icon="📅", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    authenticated = login_section()

    if not authenticated:
        st.markdown(
            "<div style='text-align:center; padding:4rem 2rem;'>"
            "<div style='font-size:3rem; margin-bottom:1rem;'>📅</div>"
            "<h2 style='color:var(--text-primary);'>Календарь записей</h2>"
            "<p style='color:var(--text-secondary);'>Войдите через Google для доступа к записям</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    st.sidebar.divider()

    icons = {"Сегодня": "📋", "Неделя": "🗓️", "Таблица": "📊", "Календарь": "📅"}
    view_labels = [f"{icons[v]} {v}" for v in ["Сегодня", "Неделя", "Таблица", "Календарь"]]
    view_mode_raw = st.sidebar.radio("Режим", view_labels, index=0, label_visibility="collapsed")
    view_mode = view_mode_raw.split(" ", 1)[1]

    st.sidebar.divider()

    # ── Кнопка добавления записи ──
    with st.sidebar.popover("+ Новая запись", use_container_width=True):
        booking_form()

    events = []
    try:
        now = datetime.utcnow()
        past = now - timedelta(days=7)
        future = now + timedelta(days=90)
        events = fetch_events(time_min=past, time_max=future)
    except RuntimeError as e:
        st.error(f"Ошибка загрузки событий: {e}")
        st.stop()

    st.sidebar.divider()

    if "editing_event" in st.session_state:
        edit_event_form()
    else:
        if view_mode == "Сегодня":
            render_today_view(events)
        elif view_mode == "Неделя":
            render_week_view(events)
        elif view_mode == "Таблица":
            render_table_view(events)
        else:
            render_calendar_view(events)


if __name__ == "__main__":
    main()
