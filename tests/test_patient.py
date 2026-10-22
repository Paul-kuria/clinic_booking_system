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


def test_get_patient_upcoming_appointments(client):
    slot_day4 = _get_slot(4, 10, 0)
    slot_day2 = _get_slot(2, 10, 0)
    slot_day3 = _get_slot(3, 10, 0)

    # Book day 4 first, then day 2, then day 3
    client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_day4},
    )
    client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_day2},
    )
    b3 = client.post(
        "/appointments",
        json={"doctor_id": 1, "patient_id": 1, "start_time": slot_day3},
    )
    appt3_id = b3.json()["id"]

    # Cancel day 3 appointment
    client.patch(
        f"/appointments/{appt3_id}/cancel",
        json={"reason": "Cannot make it"},
    )

    # Fetch patient's upcoming appointments
    response = client.get("/patients/1/appointments")
    assert response.status_code == 200
    data = response.json()

    # Cancelled appointment must not be in upcoming active appointments
    assert len(data) == 2

    # Must be sorted by date ascending: day 2 first, then day 4
    assert slot_day2[:19] in data[0]["start_time"]
    assert slot_day4[:19] in data[1]["start_time"]
    assert data[0]["doctor_name"] == "Dr. Angela Test"
    assert data[0]["doctor_specialty"] == "Physiotherapy"


def test_get_patient_appointments_not_found(client):
    response = client.get("/patients/9999/appointments")
    assert response.status_code == 404
