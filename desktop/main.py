import os
import sys
import threading
from datetime import datetime, date, timedelta, timezone

import flet as ft

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auth_handler
from calendar_manager import (
    fetch_events,
    create_event,
    update_event,
    delete_event,
    set_attendance,
    check_availability,
)

WEEKDAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTH_NAMES = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
               "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def format_date_ru(d: date) -> str:
    return f"{d.day} {MONTH_NAMES[d.month]} {d.year}"


class CalendarApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Календарь записей"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window_width = 1100
        self.page.window_height = 750
        self.page.padding = 0

        self._events: list[dict] = []
        self._current_view = "today"
        self._week_offset = 0
        self._cal_month = date.today().month
        self._cal_year = date.today().year
        self._edit_event: dict | None = None
        self._clients = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        self._check_auth()

    def _check_auth(self):
        if auth_handler.is_authenticated():
            self._load_and_show()
        else:
            self._show_login()

    def _show_login(self):
        self.page.clean()
        status_text = ft.Text("Нажмите кнопку для входа через Google", size=16)

        def on_login(e):
            status_text.value = "🔄 Открываем браузер..."
            status_text.color = ft.Colors.ORANGE_300
            self.page.update()

            def _do_login():
                success = auth_handler.login()
                if success:
                    status_text.value = "✅ Успешно! Загружаем данные..."
                    status_text.color = ft.Colors.GREEN_400
                    self.page.update()
                    self._load_and_show()
                else:
                    status_text.value = "❌ Ошибка входа. Попробуйте снова."
                    status_text.color = ft.Colors.RED_400
                    self.page.update()

            threading.Thread(target=_do_login, daemon=True).start()

        self.page.add(
            ft.Container(
                content=ft.Column([
                    ft.Text("🔐 Вход в систему", size=24, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=20),
                    ft.ElevatedButton("Войти через Google", on_click=on_login, width=300),
                    status_text,
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                expand=True,
            )
        )

    # ── Main app ────────────────────────────────────────────

    def _load_and_show(self):
        self.page.clean()
        self._build_main_layout()

        def _fetch():
            try:
                now = datetime.now(timezone.utc)
                past = now - timedelta(days=7)
                future = now + timedelta(days=90)
                self._events = fetch_events(time_min=past, time_max=future)
                self._refresh_client_list()
            except Exception as ex:
                self._show_error(str(ex))

        threading.Thread(target=_fetch, daemon=True).start()

    def _build_main_layout(self):
        sidebar = ft.Container(
            content=ft.Column([
                ft.Text("📅 Записи", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(height=10),
                ft.NavigationRail(
                    selected_index=0,
                    label_type=ft.NavigationRailLabelType.ALL,
                    destinations=[
                        ft.NavigationRailDestination(icon=ft.Icons.TODAY, label="Сегодня"),
                        ft.NavigationRailDestination(icon=ft.Icons.DATE_RANGE, label="Неделя"),
                        ft.NavigationRailDestination(icon=ft.Icons.TABLE_CHART, label="Таблица"),
                        ft.NavigationRailDestination(icon=ft.Icons.CALENDAR_MONTH, label="Календарь"),
                    ],
                    on_change=self._on_nav_change,
                    expand=True,
                ),
                ft.Divider(height=10),
                ft.ElevatedButton("+ Новая запись", on_click=self._show_add_dialog),
                ft.Divider(height=10),
                ft.ElevatedButton("Выйти", on_click=self._on_logout),
            ], expand=True),
            padding=10,
            width=200,
            bgcolor=ft.Colors.GREY_900,
        )

        self._main_content = ft.Container(content=ft.Text("Загрузка..."), padding=20, expand=True)
        self._sidebar = sidebar

        self.page.add(
            ft.Row([sidebar, self._main_content], expand=True)
        )

    def _on_nav_change(self, e):
        views = ["today", "week", "table", "calendar"]
        idx = e.control.selected_index
        self._current_view = views[idx] if idx < len(views) else "today"
        self._refresh_client_list()

    def _refresh_client_list(self):
        content = None
        if self._current_view == "today":
            content = self._build_today_view()
        elif self._current_view == "week":
            content = self._build_week_view()
        elif self._current_view == "table":
            content = self._build_table_view()
        elif self._current_view == "calendar":
            content = self._build_calendar_view()

        if content:
            self._main_content.content = content
            self.page.update()

    def _show_error(self, msg: str):
        self._main_content.content = ft.Column([
            ft.Text(f"❌ {msg}", color=ft.Colors.RED_400, size=16),
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.page.update()

    def _on_logout(self, e):
        auth_handler.logout()
        self._show_login()

    # ── Event helpers ───────────────────────────────────────

    def _today_events(self):
        today_str = date.today().isoformat()
        return sorted(
            [e for e in self._events if e["date"] == today_str],
            key=lambda x: x["time"],
        )

    def _attendance_icon(self, status: str) -> str:
        return {"arrived": "✅", "missed": "❌"}.get(status, "⏳")

    def _attendance_text(self, status: str) -> str:
        return {"arrived": "Пришёл", "missed": "Не пришёл"}.get(status, "Ожидание")

    def _build_event_card(self, ev: dict, prefix: str = "") -> ft.Container:
        att_icon = self._attendance_icon(ev.get("attendance", ""))
        att_text = self._attendance_text(ev.get("attendance", ""))
        notes = f"\n📝 {ev['notes']}" if ev.get("notes") else ""

        info_text = f"{ev['service']}"
        if ev.get("phone"):
            info_text += f" · 📞 {ev['phone']}"

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(f"{att_icon} {ev['time']}", weight=ft.FontWeight.BOLD, size=16),
                    ft.Text(f"{ev['duration']} мин", size=12, color=ft.Colors.GREY_400),
                    ft.Row([
                        ft.IconButton(ft.Icons.CHECK_CIRCLE_OUTLINE, tooltip="Пришёл",
                                      icon_color=ft.Colors.GREEN_400,
                                      on_click=lambda _, eid=ev["id"]: self._mark_attendance(eid, "arrived")),
                        ft.IconButton(ft.Icons.CANCEL_OUTLINED, tooltip="Не пришёл",
                                      icon_color=ft.Colors.RED_400,
                                      on_click=lambda _, eid=ev["id"]: self._mark_attendance(eid, "missed")),
                        ft.IconButton(ft.Icons.EDIT, tooltip="Изменить",
                                      on_click=lambda _, e=ev: self._show_edit_dialog(e)),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Удалить",
                                      icon_color=ft.Colors.RED_300,
                                      on_click=lambda _, eid=ev["id"]: self._delete_event_wrapper(eid)),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(f"{ev['client_name']}", weight=ft.FontWeight.W_500, size=14),
                ft.Text(info_text, size=12, color=ft.Colors.GREY_400),
                ft.Text(f"{att_icon} {att_text}", size=11, color=ft.Colors.GREY_500) if not notes else ft.Text(""),
                ft.Text(notes, size=11, color=ft.Colors.GREY_400),
            ], spacing=2),
            padding=10,
            margin=ft.margin.only(bottom=8),
            border=ft.border.all(1, ft.Colors.GREY_700),
            border_radius=8,
            bgcolor=ft.Colors.GREY_800,
        )

    def _mark_attendance(self, event_id: str, status: str):
        try:
            set_attendance(event_id, status)
            self._refresh_events_and_ui()
        except Exception as ex:
            self._show_error(str(ex))

    def _delete_event_wrapper(self, event_id: str):
        try:
            delete_event(event_id)
            self._refresh_events_and_ui()
        except Exception as ex:
            self._show_error(str(ex))

    def _refresh_events_and_ui(self):
        def _reload():
            try:
                now = datetime.now(timezone.utc)
                past = now - timedelta(days=7)
                future = now + timedelta(days=90)
                self._events = fetch_events(time_min=past, time_max=future)
                self._refresh_client_list()
            except Exception as ex:
                self._show_error(str(ex))

        threading.Thread(target=_reload, daemon=True).start()

    # ── Today view ──────────────────────────────────────────

    def _build_today_view(self) -> ft.Column:
        events = self._today_events()
        if not events:
            return ft.Column([
                ft.Text("📋 Сегодня", size=22, weight=ft.FontWeight.BOLD),
                ft.Text("Нет записей на сегодня", color=ft.Colors.GREY_400, size=16),
            ])

        cards = [ft.Text(f"📋 Сегодня · {len(events)} записей", size=22, weight=ft.FontWeight.BOLD)]
        for ev in events:
            cards.append(self._build_event_card(ev, "today"))

        return ft.Column(cards, scroll=ft.ScrollMode.AUTO)

    # ── Week view ───────────────────────────────────────────

    def _build_week_view(self) -> ft.Column:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        week_start = monday + timedelta(weeks=self._week_offset)
        week_dates = [week_start + timedelta(days=i) for i in range(7)]

        nav = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=self._week_prev),
            ft.Text(f"{format_date_ru(week_dates[0])} — {format_date_ru(week_dates[-1])}",
                    size=16, weight=ft.FontWeight.W_500),
            ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=self._week_next),
        ], alignment=ft.MainAxisAlignment.CENTER)

        rows = []
        for d in week_dates:
            ds = d.isoformat()
            day_events = sorted(
                [e for e in self._events if e["date"] == ds],
                key=lambda x: x["time"],
            )
            is_today = d == today
            day_color = ft.Colors.BLUE_300 if is_today else ft.Colors.GREY_400
            cards = [ft.Text(WEEKDAY_NAMES[d.weekday()], size=12, weight=ft.FontWeight.W_600, color=day_color),
                     ft.Text(str(d.day), size=18, weight=ft.FontWeight.BOLD, color=day_color)]
            for ev in day_events:
                cards.append(ft.Container(
                    content=ft.Text(f"{self._attendance_icon(ev.get('attendance',''))} {ev['time']} {ev['client_name']}",
                                    size=12),
                    padding=5, border=ft.border.all(1, ft.Colors.GREY_700),
                    border_radius=4, bgcolor=ft.Colors.GREY_800,
                ))
            rows.append(ft.Column(cards, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

        grid = ft.Row([ft.Container(content=c, expand=True) for c in rows])
        return ft.Column([ft.Text("🗓️ Неделя", size=22, weight=ft.FontWeight.BOLD), nav, grid],
                         scroll=ft.ScrollMode.AUTO)

    def _week_prev(self, e):
        self._week_offset -= 1
        self._refresh_client_list()

    def _week_next(self, e):
        self._week_offset += 1
        self._refresh_client_list()

    # ── Table view ──────────────────────────────────────────

    def _build_table_view(self) -> ft.Column:
        search = ft.TextField(hint_text="Поиск по имени или дате (ГГГГ-ММ-ДД)",
                              prefix_icon=ft.Icons.SEARCH, on_change=self._on_search)

        filtered = self._events
        if self._search_query:
            q = self._search_query.lower()
            filtered = [e for e in self._events
                        if q in e["client_name"].lower() or q in e["date"]]

        if not filtered:
            return ft.Column([
                ft.Text("📊 Таблица", size=22, weight=ft.FontWeight.BOLD),
                search,
                ft.Text("Записи не найдены", color=ft.Colors.GREY_400),
            ])

        cards = [ft.Text("📊 Таблица", size=22, weight=ft.FontWeight.BOLD), search]
        for ev in filtered:
            cards.append(self._build_event_card(ev, "table"))

        return ft.Column(cards, scroll=ft.ScrollMode.AUTO)

    _search_query = ""

    def _on_search(self, e):
        self._search_query = e.control.value
        self._refresh_client_list()

    # ── Calendar view ───────────────────────────────────────

    def _build_calendar_view(self) -> ft.Column:
        today = date.today()
        first_day = date(self._cal_year, self._cal_month, 1)

        if self._cal_month == 12:
            last_day = date(self._cal_year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(self._cal_year, self._cal_month + 1, 1) - timedelta(days=1)

        start_weekday = first_day.weekday()
        total_days = (last_day - first_day).days + 1

        events_by_date = {}
        for e in self._events:
            events_by_date.setdefault(e["date"], []).append(e)

        nav = ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=self._cal_prev),
            ft.Text(f"{MONTH_NAMES[self._cal_month]} {self._cal_year}",
                    size=18, weight=ft.FontWeight.W_500),
            ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=self._cal_next),
        ], alignment=ft.MainAxisAlignment.CENTER)

        # Header
        header = ft.Row(
            [ft.Container(content=ft.Text(d, size=12, weight=ft.FontWeight.W_600,
                                          color=ft.Colors.GREY_400),
                           alignment=ft.alignment.center, expand=True)
             for d in WEEKDAY_NAMES]
        )

        cells = [None] * start_weekday + list(range(1, total_days + 1))
        weeks = []
        for ws in range(0, len(cells), 7):
            week_days = cells[ws:ws + 7]
            row_cells = []
            for i in range(7):
                if i < len(week_days) and week_days[i] is not None:
                    day_num = week_days[i]
                    d = date(self._cal_year, self._cal_month, day_num)
                    ds = d.isoformat()
                    is_today = d == today
                    day_events = events_by_date.get(ds, [])

                    dots = ""
                    for ev in day_events[:3]:
                        dots += f"\n{self._attendance_icon(ev.get('attendance',''))} {ev['time']}"
                    if len(day_events) > 3:
                        dots += f"\n+{len(day_events) - 3}"

                    color = ft.Colors.BLUE_300 if is_today else ft.Colors.GREY_100
                    row_cells.append(ft.Container(
                        content=ft.Column([
                            ft.Text(str(day_num), size=14, weight=ft.FontWeight.BOLD,
                                    color=color),
                            ft.Text(dots, size=9, color=ft.Colors.GREY_400),
                        ]),
                        expand=True, height=80,
                        border=ft.border.all(0.5, ft.Colors.GREY_700),
                        padding=3,
                    ))
                else:
                    row_cells.append(ft.Container(expand=True, height=80,
                                                  border=ft.border.all(0.5, ft.Colors.GREY_800)))

            weeks.append(ft.Row(row_cells))

        return ft.Column([
            ft.Text("📅 Календарь", size=22, weight=ft.FontWeight.BOLD),
            nav, header, *weeks,
        ], scroll=ft.ScrollMode.AUTO)

    def _cal_prev(self, e):
        if self._cal_month == 1:
            self._cal_month = 12
            self._cal_year -= 1
        else:
            self._cal_month -= 1
        self._refresh_client_list()

    def _cal_next(self, e):
        if self._cal_month == 12:
            self._cal_month = 1
            self._cal_year += 1
        else:
            self._cal_month += 1
        self._refresh_client_list()

    # ── Add / Edit dialogs ──────────────────────────────────

    def _show_add_dialog(self, e=None):
        default_date = date.today()
        self._open_booking_dialog(default_date)

    def _show_edit_dialog(self, ev: dict):
        self._edit_event = ev
        self._open_booking_dialog(ev)

    def _open_booking_dialog(self, ev_or_date):
        is_edit = isinstance(ev_or_date, dict)
        ev = ev_or_date if is_edit else None
        default_date = ev_or_date if not is_edit else date.fromisoformat(ev["date"])

        name = ft.TextField(label="Имя клиента", value=ev["client_name"] if ev else "")
        phone = ft.TextField(label="Телефон", value=ev.get("phone", "") if ev else "")
        service = ft.Dropdown(
            label="Услуга",
            options=[ft.dropdown.Option("Первичный прием"), ft.dropdown.Option("Повторный прием")],
            value=ev.get("service", "Первичный прием") if ev else "Первичный прием",
        )
        date_picker = ft.TextField(label="Дата (ГГГГ-ММ-ДД)", value=default_date.isoformat(), width=150)
        time_options = [f"{h:02d}:{m:02d}" for h in range(11, 19) for m in (0, 30)]
        time_picker = ft.Dropdown(
            label="Время",
            options=[ft.dropdown.Option(t) for t in time_options],
            value=ev["time"] if ev else time_options[0],
        )
        duration = ft.Dropdown(
            label="Длительность (мин)",
            options=[ft.dropdown.Option(str(d)) for d in [30, 60, 90, 120]],
            value=str(ev.get("duration", 60)) if ev else "60",
        )
        notes = ft.TextField(label="Заметка", value=ev.get("notes", "") if ev else "",
                             multiline=True, min_lines=2, max_lines=4)

        dialog = ft.AlertDialog(
            title=ft.Text("✏️ Редактировать" if is_edit else "➕ Новая запись"),
            content=ft.Column([
                name, phone, service,
                ft.Row([date_picker, time_picker, duration]),
                notes,
            ], width=500, height=350, scroll=ft.ScrollMode.AUTO),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: self._close_dialog(dialog)),
                ft.ElevatedButton("Сохранить" if is_edit else "Записать",
                                  on_click=lambda e: self._save_booking(dialog, ev, name, phone,
                                                                         service, date_picker, time_picker,
                                                                         duration, notes, is_edit)),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _close_dialog(self, dialog):
        dialog.open = False
        self.page.update()

    def _save_booking(self, dialog, ev, name, phone, service, date_picker, time_picker, duration, notes, is_edit):
        if not name.value.strip():
            self._show_dialog_error("Укажите имя клиента")
            return

        date_str = date_picker.value
        time_str = time_picker.value
        dur = int(duration.value)

        try:
            if is_edit:
                update_event(ev["id"], name.value.strip(), phone.value.strip(),
                             service.value, date_str, time_str, dur, notes.value)
            else:
                if not check_availability(date_str, time_str, dur):
                    self._show_dialog_error("Слот занят")
                    return
                create_event(name.value.strip(), phone.value.strip(),
                             service.value, date_str, time_str, dur, notes.value)

            dialog.open = False
            self.page.update()
            self._refresh_events_and_ui()
        except Exception as ex:
            self._show_dialog_error(str(ex))

    def _show_dialog_error(self, msg: str):
        pass  # упрощённо

    # ── Run ─────────────────────────────────────────────────


def main():
    ft.app(target=lambda p: CalendarApp(p))


if __name__ == "__main__":
    main()
