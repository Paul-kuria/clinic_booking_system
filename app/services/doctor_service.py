from datetime import date, datetime, time, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.doctor import Doctor, DoctorSchedule
from app.models.appointment import Appointment, AppointmentStatus
from app.schemas.doctor import DoctorAvailabilityResponse, TimeSlotOut


def ensure_utc(dt: datetime) -> datetime:
    """Normalize datetime to timezone-aware UTC (handles SQLite naive timestamps)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_doctor_by_id(db: Session, doctor_id: int) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with id {doctor_id} not found.",
        )
    return doctor


def get_doctor_availability(
    db: Session, doctor_id: int, target_date: date
) -> DoctorAvailabilityResponse:
    doctor = get_doctor_by_id(db, doctor_id)

    weekday = target_date.weekday()
    schedules = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.day_of_week == weekday,
        )
        .all()
    )

    if not schedules:
        return DoctorAvailabilityResponse(
            doctor_id=doctor.id,
            doctor_name=doctor.name,
            date=target_date,
            available_slots=[],
        )

    theoretical_slots: list[tuple[datetime, datetime]] = []
    slot_delta = timedelta(minutes=settings.SLOT_DURATION_MINUTES)
    tz = settings.timezone_info

    for sched in schedules:
        current_dt_local = datetime.combine(
            target_date, sched.start_time, tzinfo=tz
        )
        end_dt_local = datetime.combine(target_date, sched.end_time, tzinfo=tz)

        while current_dt_local + slot_delta <= end_dt_local:
            slot_start_utc = current_dt_local.astimezone(timezone.utc)
            slot_end_utc = (current_dt_local + slot_delta).astimezone(
                timezone.utc
            )
            theoretical_slots.append((slot_start_utc, slot_end_utc))
            current_dt_local += slot_delta

    if not theoretical_slots:
        return DoctorAvailabilityResponse(
            doctor_id=doctor.id,
            doctor_name=doctor.name,
            date=target_date,
            available_slots=[],
        )

    min_start = min(s[0] for s in theoretical_slots)
    max_end = max(s[1] for s in theoretical_slots)

    booked_appointments = (
        db.query(Appointment.start_time)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.start_time >= min_start,
            Appointment.start_time < max_end,
        )
        .all()
    )
    booked_set = {ensure_utc(b[0]) for b in booked_appointments}

    now_utc = datetime.now(timezone.utc)
    cutoff_time = now_utc + timedelta(hours=settings.MIN_ADVANCE_BOOKING_HOURS)

    available_slots: list[TimeSlotOut] = []
    for slot_start, slot_end in theoretical_slots:
        if slot_start <= cutoff_time:
            continue
        if slot_start in booked_set:
            continue

        available_slots.append(
            TimeSlotOut(start_time=slot_start, end_time=slot_end)
        )

    return DoctorAvailabilityResponse(
        doctor_id=doctor.id,
        doctor_name=doctor.name,
        date=target_date,
        available_slots=available_slots,
    )
