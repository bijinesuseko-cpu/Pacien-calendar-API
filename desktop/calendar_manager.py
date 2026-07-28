from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from auth_handler import get_credentials


SERVICE_NAME = "calendar"
API_VERSION = "v3"
CALENDAR_ID = "7c2f32ceea7072ff8714c24c0cb67133502f33896ee226583b55b707dcd60ccf@group.calendar.google.com"
EVENT_PREFIX = "[BOOKING] "
TOKEN_EXPIRED = "TOKEN_EXPIRED"


def get_service():
    creds = get_credentials()
    if not creds:
        raise RuntimeError("Not authenticated. Please log in first.")
    return build(SERVICE_NAME, API_VERSION, credentials=creds)


def _handle_http_error(e: HttpError):
    if e.resp.status == 401:
        raise RuntimeError(TOKEN_EXPIRED)
    if e.resp.status == 400:
        body = e.content.decode("utf-8", errors="replace") if e.content else "no body"
        print(f"  ⚠️ Google API 400: {body}")
        raise RuntimeError(f"Bad Request (400): {body}")
    if e.resp.status == 429:
        raise RuntimeError("Превышен лимит запросов Google API. Попробуйте позже.")
    if e.resp.status in (403, 404):
        raise RuntimeError("Нет доступа к календарю. Обратитесь к администратору.")
    raise RuntimeError(f"Ошибка Google API: {e}")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_events(time_min: datetime | None = None, time_max: datetime | None = None) -> list[dict]:
    service = get_service()
    now = _utcnow_iso()

    params = {
        "calendarId": CALENDAR_ID,
        "timeMin": time_min.isoformat().replace("+00:00", "Z") + "Z" if time_min else now,
        "maxResults": 250,
        "singleEvents": True,
        "orderBy": "startTime",
    }
    if time_max:
        params["timeMax"] = time_max.isoformat().replace("+00:00", "Z") + "Z"

    try:
        events_result = service.events().list(**params).execute()
    except HttpError as e:
        _handle_http_error(e)

    items = events_result.get("items", [])
    return [_parse_event(e) for e in items]


def _parse_event(event: dict) -> dict:
    description = event.get("description", "")
    phone = ""
    service_name = ""
    notes = ""
    attendance = ""

    for line in description.split("\n"):
        if line.startswith("Phone: "):
            phone = line[len("Phone: "):]
        elif line.startswith("Service: "):
            service_name = line[len("Service: "):]
        elif line.startswith("Notes: "):
            notes = line[len("Notes: "):]
        elif line.startswith("Attendance: "):
            attendance = line[len("Attendance: "):]

    start = event.get("start", {})
    start_dt = start.get("dateTime", start.get("date", ""))

    if "T" in start_dt:
        dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
    else:
        date_str = start_dt
        time_str = "All day"

    end = event.get("end", {})
    end_dt = end.get("dateTime", end.get("date", ""))
    duration_minutes = 60
    if "T" in start_dt and "T" in end_dt:
        dt_start = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
        dt_end = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
        duration_minutes = int((dt_end - dt_start).total_seconds() / 60)

    title = event.get("summary", "")
    client_name = title
    if title.startswith(EVENT_PREFIX):
        client_name = title[len(EVENT_PREFIX):]

    return {
        "id": event.get("id"),
        "client_name": client_name,
        "date": date_str,
        "time": time_str,
        "duration": duration_minutes,
        "service": service_name,
        "phone": phone,
        "notes": notes,
        "attendance": attendance,
        "status": event.get("status", "confirmed"),
        "summary": title,
    }


def check_availability(date_str: str, time_str: str, duration_minutes: int = 60) -> bool:
    dt_start = datetime.fromisoformat(f"{date_str}T{time_str}:00")
    dt_end = dt_start + timedelta(minutes=duration_minutes)

    service = get_service()
    try:
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=dt_start.isoformat() + "Z",
            timeMax=dt_end.isoformat() + "Z",
            singleEvents=True,
            maxResults=50,
        ).execute()
    except HttpError as e:
        _handle_http_error(e)

    events = events_result.get("items", [])
    for ev in events:
        ev_start = ev.get("start", {})
        ev_end = ev.get("end", {})
        ev_start_dt = ev_start.get("dateTime", ev_start.get("date", ""))
        ev_end_dt = ev_end.get("dateTime", ev_end.get("date", ""))

        if "T" in ev_start_dt and "T" in ev_end_dt:
            existing_start = datetime.fromisoformat(ev_start_dt.replace("Z", "+00:00"))
            existing_end = datetime.fromisoformat(ev_end_dt.replace("Z", "+00:00"))
            if dt_start < existing_end and dt_end > existing_start:
                return False

    return True


def create_event(client_name: str, phone: str, service_name: str, date_str: str, time_str: str, duration_minutes: int = 60, notes: str = "") -> dict:
    if not check_availability(date_str, time_str, duration_minutes):
        raise ValueError(f"Слот {date_str} в {time_str} уже занят.")

    dt_start = datetime.fromisoformat(f"{date_str}T{time_str}:00")
    dt_end = dt_start + timedelta(minutes=duration_minutes)

    summary = f"{EVENT_PREFIX}{client_name}"
    description = f"Client: {client_name}\nPhone: {phone}\nService: {service_name}"
    if notes.strip():
        description += f"\nNotes: {notes.strip()}"

    event_body = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": dt_start.isoformat(),
            "timeZone": "Asia/Yekaterinburg",
        },
        "end": {
            "dateTime": dt_end.isoformat(),
            "timeZone": "Asia/Yekaterinburg",
        },
    }

    service = get_service()
    try:
        created = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
    except HttpError as e:
        _handle_http_error(e)

    return _parse_event(created)


def update_event(event_id: str, client_name: str, phone: str, service_name: str, date_str: str, time_str: str, duration_minutes: int = 60, notes: str = "", attendance: str = "") -> dict:
    dt_start = datetime.fromisoformat(f"{date_str}T{time_str}:00")
    dt_end = dt_start + timedelta(minutes=duration_minutes)

    summary = f"{EVENT_PREFIX}{client_name}"
    description = f"Client: {client_name}\nPhone: {phone}\nService: {service_name}"
    if notes.strip():
        description += f"\nNotes: {notes.strip()}"
    if attendance:
        description += f"\nAttendance: {attendance}"

    event_body = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": dt_start.isoformat(),
            "timeZone": "Asia/Yekaterinburg",
        },
        "end": {
            "dateTime": dt_end.isoformat(),
            "timeZone": "Asia/Yekaterinburg",
        },
    }

    service = get_service()
    try:
        updated = service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=event_body).execute()
    except HttpError as e:
        _handle_http_error(e)

    return _parse_event(updated)


def delete_event(event_id: str) -> None:
    service = get_service()
    try:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except HttpError as e:
        _handle_http_error(e)


def set_attendance(event_id: str, attendance: str) -> dict:
    service = get_service()
    try:
        event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except HttpError as e:
        _handle_http_error(e)

    description = event.get("description", "")
    lines = description.split("\n")
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("Attendance: "):
            new_lines.append(f"Attendance: {attendance}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"Attendance: {attendance}")

    event["description"] = "\n".join(new_lines)

    try:
        updated = service.events().update(calendarId=CALENDAR_ID, eventId=event_id, body=event).execute()
    except HttpError as e:
        _handle_http_error(e)

    return _parse_event(updated)
