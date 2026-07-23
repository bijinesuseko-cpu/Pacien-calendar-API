# Calendar Booking App

Streamlit-приложение для управления записями через Google Calendar API.

## Структура проекта

```
├── app.py                # Точка входа, весь UI (streamlit run app.py)
├── auth_handler.py       # OAuth2: логин, сохранение/обновление токена, logout
├── calendar_manager.py   # Работа с Google Calendar API: чтение, создание, обновление, удаление
├── requirements.txt      # Зависимости (pip install -r requirements.txt)
├── credentials.json      # OAuth ключ из Google Cloud Console (НЕ коммитить!)
└── token.json            # Генерируется автоматически при первом логине (НЕ коммитить!)
```

## auth_handler.py

| Функция | Что делает |
|---|---|
| `get_credentials()` | Загружает токен, обновляет если истёк, или запускает OAuth flow |
| `save_token(creds)` | Сохраняет токен в token.json |
| `revoke_token()` | Удаляет token.json (logout) |
| `is_authenticated()` | Проверяет, есть ли валидный токен |

## calendar_manager.py

| Функция | Что делает |
|---|---|
| `fetch_events(time_min, time_max)` | Получает события из календаря, парсит описание |
| `check_availability(date, time, duration)` | Проверяет, свободен ли слот |
| `create_event(name, phone, service, date, time, duration, notes)` | Создаёт событие |
| `update_event(event_id, ...)` | Обновляет существующее событие |
| `delete_event(event_id)` | Удаляет событие |
| `set_attendance(event_id, status)` | Отмечает посещение (arrived/missed) |

Данные хранятся в поле **Description** события:
```
Client: Имя
Phone: +7...
Service: Первичный прием
Notes: Заметка
Attendance: arrived
```

## app.py

| Блок | Что делает |
|---|---|
| `login_section()` | Боковая панель: логин/вывод статуса/logout |
| `render_today_view()` | Записи на сегодня в виде карточек |
| `render_week_view()` | Неделя Пн–Вс с навигацией по неделям |
| `render_table_view()` | Таблица с поиском по имени и дате |
| `render_calendar_view()` | Полный месяц с popover по дням |
| `edit_event_form()` | Форма редактирования/удаления записи |
| `booking_form()` | Форма добавления записи с валидацией |

## Режимы просмотра

- **Сегодня** — карточки записей на текущий день
- **Неделя** — 7 колонок (Пн–Вс) с кнопками навигации
- **Таблица** — все записи с поиском
- **Календарь** — сетка месяца, клик по дню открывает popover

## Отметки посещения

Каждая запись имеет три состояния:
- ⏳ **Ожидание** — ещё не отмечено
- ✅ **Пришёл** — клиент был
- ❌ **Не пришёл** — клиент не пришёл

## Запуск

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Google Cloud Console

1. Создать проект в console.cloud.google.com
2. Включить **Google Calendar API**
3. Создать OAuth credentials типа **Desktop app**
4. Скачать `credentials.json` → положить в корень проекта
5. В OAuth consent screen добавить свою почту как тестового пользователя
6. Создать календарь «Записи» → расшарить с пользователями (Изменение событий)
7. ID календаря → в `calendar_manager.py` → `CALENDAR_ID`
