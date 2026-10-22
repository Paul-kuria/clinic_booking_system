from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

EAT = ZoneInfo("Africa/Nairobi")


def _get_valid_future_slot(days_ahead: int = 2, hour: int = 10, minute: int = 0) -> str:
    """Helper to return an ISO string in UTC for a valid local time in Nairobi."""
    now_eat = datetime.now(EAT)
    target_date = (now_eat + timedelta(days=days_ahead)).date()
    target_dt_eat = datetime.combine(
        target_date, datetime.min.time().replace(hour=hour, minute=minute), tzinfo=EAT
    )
    return target_dt_eat.astimezone(timezone.utc).isoformat()


def test_book_appointment_success(client):
    future_slot = _get_valid_future_slot(days_ahead=2, hour=10, minute=0)
    response = client.post(
        "/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": future_slot,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["doctor_id"] == 1
    assert data["patient_id"] == 1
    assert data["status"] == "BOOKED"
    assert data["cancellation_reason"] is None


def test_book_appointment_in_the_past(client):
    past_time = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).replace(minute=0, second=0, microsecond=0)
    response = client.post(
        "/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": past_time.isoformat(),
        },
    )
    assert response.status_code == 400
    assert "past" in response.json()["detail"].lower()


def test_book_appointment_within_one_hour(client):
    # Slot 30 minutes from now (must fall on :00 or :30)
    now_utc = datetime.now(timezone.utc)
    imminent = (now_utc + timedelta(minutes=25)).replace(
        minute=30 if now_utc.minute < 30 else 0, second=0, microsecond=0
    )
    # Ensure it is strictly < 1 hour ahead
    if (imminent - now_utc) >= timedelta(hours=1):
        imminent -= timedelta(minutes=30)

    response = client.post(
        "/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": imminent.isoformat(),
        },
    )
    assert response.status_code == 400
    assert "1 hour" in response.json()["detail"].lower()


def test_book_outside_working_hours(client):
    # Dr. Angela works 08:00 to 18:00 EAT. Let's try 22:00 EAT (outside hours)
    future_slot = _get_valid_future_slot(days_ahead=2, hour=22, minute=0)
    response = client.post(
        "/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": future_slot,
        },
    )
    assert response.status_code == 400
    assert "working hours" in response.json()["detail"].lower()


def test_book_misaligned_slot_minutes(client):
    # Slot at 10:15 (must be :00 or :30)
    future_slot = _get_valid_future_slot(days_ahead=2, hour=10, minute=15)
    response = client.post(
        "/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": future_slot,
        },
    )
    assert response.status_code == 422
    assert "30-minute boundary" in response.text


def test_double_booking_doctor_fails(client):
    future_slot = _get_valid_future_slot(days_ahead=3, hour=11, minute=0)

    # First booking succeeds
    r1 = client.post(
        "/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": future_slot,
        },
    )
    assert r1.status_code == 201

    # Second patient tries to book the same doctor at the same slot -> 409
    r2 = client.post(
        "/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 2,
            "start_time": future_slot,
        },
    )
    assert r2.status_code == 409
    assert "already booked" in r2.json()["detail"].lower()


def test_patient_double_booking_fails(client):
    future_slot = _get_valid_future_slot(days_ahead=3, hour=11, minute=30)

    # Patient 1 books Doctor 1
    r1 = client.post(
        "/appointments",
        json={
            "doctor_id": 1,
            "patient_id": 1,
            "start_time": future_slot,
        },
    )
    assert r1.status_code == 201

    # Patient 1 tries to book Doctor 2 at the exact same slot -> 409
    # (Note: Need Dr 2 working at this time. Dr 1 is available. Let's make sure Dr 2 has hours or use Dr 1 if days_ahead is Monday)
    # Let's test patient conflict on Monday when Dr. 2 also works
    now_eat = datetime.now(EAT)
    days_to_monday = (0 - now_eat.weekday() + 7) % 7
    if days_to_monday == 0:
        days_to_monday = 7
    monday_dt = datetime.combine(
        (now_eat + timedelta(days=days_to_monday)).date(),
        datetime.min.time().replace(hour=10, minute=0),
        tzinfo=EAT,
    )
    monday_utc = monday_dt.astimezone(timezone.utc).isoformat()

    # Patient 1 books Dr 1 on Monday 10:00
    r_doc1 = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": monday_utc},
    )
    assert r_doc1.status_code == 201

    # Patient 1 attempts to book Dr 2 on Monday 10:00
    r_doc2 = client.post(
        "/appointments",
        json={"doctor_id": 2, "patient_id": 1, "start_time": monday_utc},
    )
    assert r_doc2.status_code == 409
    assert "patient already has an active appointment" in r_doc2.json()["detail"].lower()
