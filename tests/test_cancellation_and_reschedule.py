from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

EAT = ZoneInfo("Africa/Nairobi")


def _get_slot(days_ahead: int, hour: int, minute: int) -> str:
    now_eat = datetime.now(EAT)
    target_date = (now_eat + timedelta(days=days_ahead)).date()
    target_dt_eat = datetime.combine(
        target_date, datetime.min.time().replace(hour=hour, minute=minute), tzinfo=EAT
    )
    return target_dt_eat.astimezone(timezone.utc).isoformat()


def test_cancel_already_cancelled_returns_409(client):
    slot = _get_slot(3, 14, 0)
    book = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot},
    )
    appt_id = book.json()["id"]

    # First cancel succeeds
    c1 = client.patch(
        f"/appointments/{appt_id}/cancel",
        json={"reason": "Feeling much better"},
    )
    assert c1.status_code == 200
    assert c1.json()["status"] == "CANCELLED"
    assert c1.json()["cancellation_reason"] == "Feeling much better"

    # Second cancel must fail with 409 Conflict
    c2 = client.patch(
        f"/appointments/{appt_id}/cancel",
        json={"reason": "Trying to cancel again"},
    )
    assert c2.status_code == 409
    assert "already been cancelled" in c2.json()["detail"].lower()


def test_reschedule_success(client):
    slot1 = _get_slot(4, 10, 0)
    slot2 = _get_slot(4, 14, 0)

    # Book slot 1
    book = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot1},
    )
    appt_id = book.json()["id"]

    # Reschedule to slot 2
    resched = client.patch(
        f"/appointments/{appt_id}/reschedule",
        json={"new_start_time": slot2},
    )
    assert resched.status_code == 200
    data = resched.json()
    assert data["id"] == appt_id
    assert slot2[:19] in data["start_time"]
    assert data["status"] == "BOOKED"

    # Slot 1 is now free again, so another patient can book it!
    book_slot1_again = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 2, "start_time": slot1},
    )
    assert book_slot1_again.status_code == 201


def test_reschedule_cancelled_appointment_fails(client):
    slot1 = _get_slot(3, 9, 0)
    slot2 = _get_slot(3, 11, 0)

    book = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot1},
    )
    appt_id = book.json()["id"]

    # Cancel
    client.patch(
        f"/appointments/{appt_id}/cancel",
        json={"reason": "Emergency"},
    )

    # Attempt to reschedule cancelled appointment
    r = client.patch(
        f"/appointments/{appt_id}/reschedule",
        json={"new_start_time": slot2},
    )
    assert r.status_code == 409
    assert "cancelled" in r.json()["detail"].lower()


def test_reschedule_to_same_time_fails(client):
    slot1 = _get_slot(3, 15, 0)
    book = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot1},
    )
    appt_id = book.json()["id"]

    r = client.patch(
        f"/appointments/{appt_id}/reschedule",
        json={"new_start_time": slot1},
    )
    assert r.status_code == 400
    assert "different" in r.json()["detail"].lower()


def test_reschedule_to_taken_slot_fails(client):
    slot1 = _get_slot(3, 12, 0)
    slot2 = _get_slot(3, 12, 30)

    # Patient 1 books slot 1
    b1 = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot1},
    )
    appt1_id = b1.json()["id"]

    # Patient 2 books slot 2
    b2 = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 2, "start_time": slot2},
    )
    assert b2.status_code == 201

    # Patient 1 tries to reschedule into slot 2 (already occupied)
    r = client.patch(
        f"/appointments/{appt1_id}/reschedule",
        json={"new_start_time": slot2},
    )
    assert r.status_code == 409
    assert "already booked" in r.json()["detail"].lower()
