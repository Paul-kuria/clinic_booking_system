from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

EAT = ZoneInfo("Africa/Nairobi")


def test_doctor_availability_lists_slots(client):
    # Query Dr 1 for 5 days in the future
    target_date = (datetime.now(EAT) + timedelta(days=5)).date().isoformat()
    response = client.get(f"/doctors/1/availability?date={target_date}")
    assert response.status_code == 200
    data = response.json()
    assert data["doctor_id"] == 1
    assert data["doctor_name"] == "Dr. Angela Test"
    assert len(data["available_slots"]) > 0

    # Dr 1 works 08:00 to 18:00 (10 hours = 20 slots of 30 mins)
    assert len(data["available_slots"]) == 20


def test_booked_slot_removed_from_availability_and_reappears_on_cancel(client):
    target_date = (datetime.now(EAT) + timedelta(days=5)).date()
    # Pick 09:00 EAT
    slot_dt_eat = datetime.combine(
        target_date, datetime.min.time().replace(hour=9, minute=0), tzinfo=EAT
    )
    slot_utc = slot_dt_eat.astimezone(timezone.utc).isoformat()

    # 1. Check availability before booking
    r1 = client.get(f"/doctors/1/availability?date={target_date.isoformat()}")
    slots_before = [s["start_time"] for s in r1.json()["available_slots"]]
    # Normalize comparison string
    assert any(s.startswith(slot_utc[:19]) for s in slots_before)
    initial_count = len(slots_before)

    # 2. Book the slot
    book_resp = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_utc},
    )
    assert book_resp.status_code == 201
    appt_id = book_resp.json()["id"]

    # 3. Check availability again -> slot must be gone, count decreased by 1
    r2 = client.get(f"/doctors/1/availability?date={target_date.isoformat()}")
    slots_after_book = [s["start_time"] for s in r2.json()["available_slots"]]
    assert not any(s.startswith(slot_utc[:19]) for s in slots_after_book)
    assert len(slots_after_book) == initial_count - 1

    # 4. Cancel the appointment
    cancel_resp = client.patch(
        f"/appointments/{appt_id}/cancel",
        json={"reason": "Schedule conflict"},
    )
    assert cancel_resp.status_code == 200

    # 5. Check availability again -> slot must be back!
    r3 = client.get(f"/doctors/1/availability?date={target_date.isoformat()}")
    slots_after_cancel = [s["start_time"] for s in r3.json()["available_slots"]]
    assert any(s.startswith(slot_utc[:19]) for s in slots_after_cancel)
    assert len(slots_after_cancel) == initial_count


def test_doctor_availability_non_working_day(client):
    # Dr. 2 only works on Mondays (day 0). Let's find a Sunday.
    now_eat = datetime.now(EAT)
    days_to_sunday = (6 - now_eat.weekday() + 7) % 7
    if days_to_sunday == 0:
        days_to_sunday = 7
    sunday_date = (now_eat + timedelta(days=days_to_sunday)).date().isoformat()

    response = client.get(f"/doctors/2/availability?date={sunday_date}")
    assert response.status_code == 200
    assert response.json()["available_slots"] == []


def test_doctor_availability_doctor_not_found(client):
    response = client.get("/doctors/9999/availability?date=2026-10-25")
    assert response.status_code == 404
