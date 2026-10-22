from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.appointment import Appointment, AppointmentStatus
from app.models.doctor import Doctor, DoctorSchedule
from app.models.patient import Patient
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentCancel,
    AppointmentReschedule,
)


def ensure_utc(dt: datetime) -> datetime:
    """Normalize datetime to timezone-aware UTC (handles SQLite naive timestamps)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _validate_slot_within_doctor_hours(
    db: Session, doctor_id: int, start_time_utc: datetime
) -> tuple[datetime, datetime]:
    """
    Validates that the given UTC start time falls within one of the doctor's
    active schedules on that day, when evaluated in the clinic's local timezone.
    Returns (start_time_utc, end_time_utc).
    """
    slot_duration = timedelta(minutes=settings.SLOT_DURATION_MINUTES)
    end_time_utc = start_time_utc + slot_duration

    # Convert to clinic local timezone
    tz = settings.timezone_info
    local_start = start_time_utc.astimezone(tz)
    local_end = end_time_utc.astimezone(tz)

    weekday = local_start.weekday()
    schedules = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.day_of_week == weekday,
        )
        .all()
    )

    if not schedules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Doctor does not work on {local_start.strftime('%A')}s.",
        )

    fits_in_schedule = False
    for sched in schedules:
        sched_start_dt = datetime.combine(
            local_start.date(), sched.start_time, tzinfo=tz
        )
        sched_end_dt = datetime.combine(
            local_start.date(), sched.end_time, tzinfo=tz
        )
        if sched_start_dt <= local_start and local_end <= sched_end_dt:
            fits_in_schedule = True
            break

    if not fits_in_schedule:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"The requested time slot ({local_start.strftime('%H:%M')} - "
                f"{local_end.strftime('%H:%M')} EAT) is outside the doctor's working hours."
            ),
        )

    return start_time_utc, end_time_utc


def _validate_advance_notice(start_time_utc: datetime) -> None:
    now_utc = datetime.now(timezone.utc)
    if start_time_utc < now_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book an appointment in the past.",
        )

    min_advance = timedelta(hours=settings.MIN_ADVANCE_BOOKING_HOURS)
    if start_time_utc < (now_utc + min_advance):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Appointments must be booked at least "
                f"{settings.MIN_ADVANCE_BOOKING_HOURS} hour in advance."
            ),
        )


def book_appointment(db: Session, payload: AppointmentCreate) -> Appointment:
    doctor = db.query(Doctor).filter(Doctor.id == payload.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with id {payload.doctor_id} not found.",
        )

    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id {payload.patient_id} not found.",
        )

    # Normalize UTC start time
    start_time_utc = ensure_utc(payload.start_time)

    # 3. Advance notice validation (not in past, >= 1 hour ahead)
    _validate_advance_notice(start_time_utc)

    # 4. Working hours validation
    start_time_utc, end_time_utc = _validate_slot_within_doctor_hours(
        db, payload.doctor_id, start_time_utc
    )

    # 5. Check if Doctor already has an active booking at this slot
    doctor_booked = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == payload.doctor_id,
            Appointment.start_time == start_time_utc,
            Appointment.status == AppointmentStatus.BOOKED,
        )
        .first()
    )
    if doctor_booked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This doctor is already booked for the requested time slot.",
        )

    # 6. Check if Patient already has an active booking at this slot
    patient_booked = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == payload.patient_id,
            Appointment.start_time == start_time_utc,
            Appointment.status == AppointmentStatus.BOOKED,
        )
        .first()
    )
    if patient_booked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient already has an active appointment at this time with another doctor.",
        )

    # 7. Create appointment & commit (relying on partial index to safeguard race conditions)
    appointment = Appointment(
        doctor_id=payload.doctor_id,
        patient_id=payload.patient_id,
        start_time=start_time_utc,
        end_time=end_time_utc,
        status=AppointmentStatus.BOOKED,
    )
    db.add(appointment)

    try:
        db.commit()
        db.refresh(appointment)
        return appointment
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested time slot was just taken by another request. Please choose another slot.",
        )


def cancel_appointment(
    db: Session, appointment_id: int, payload: AppointmentCancel
) -> Appointment:
    appointment = (
        db.query(Appointment).filter(Appointment.id == appointment_id).first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with id {appointment_id} not found.",
        )

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This appointment has already been cancelled.",
        )

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancellation_reason = payload.reason
    db.commit()
    db.refresh(appointment)
    return appointment


def reschedule_appointment(
    db: Session, appointment_id: int, payload: AppointmentReschedule
) -> Appointment:
    appointment = (
        db.query(Appointment).filter(Appointment.id == appointment_id).first()
    )
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with id {appointment_id} not found.",
        )

    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot reschedule an appointment that has been cancelled.",
        )

    new_start_utc = ensure_utc(payload.new_start_time)
    current_start_utc = ensure_utc(appointment.start_time)

    if current_start_utc == new_start_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New appointment time must be different from the current appointment time.",
        )

    # 1. Advance notice validation
    _validate_advance_notice(new_start_utc)

    # 2. Working hours validation
    new_start_utc, new_end_utc = _validate_slot_within_doctor_hours(
        db, appointment.doctor_id, new_start_utc
    )

    # 3. Check if Doctor already booked at new time (excluding this appointment)
    doctor_conflict = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.start_time == new_start_utc,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.id != appointment.id,
        )
        .first()
    )
    if doctor_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The doctor is already booked for the target reschedule slot.",
        )

    # 4. Check if Patient already booked at new time (excluding this appointment)
    patient_conflict = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == appointment.patient_id,
            Appointment.start_time == new_start_utc,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.id != appointment.id,
        )
        .first()
    )
    if patient_conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient already has another active appointment at this time.",
        )

    # 5. Atomically update within current transaction
    appointment.start_time = new_start_utc
    appointment.end_time = new_end_utc

    try:
        db.commit()
        db.refresh(appointment)
        return appointment
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The target slot was just taken by another request. Please choose another slot.",
        )


def get_patient_upcoming_appointments(
    db: Session, patient_id: int
) -> list[Appointment]:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id {patient_id} not found.",
        )

    now_utc = datetime.now(timezone.utc)
    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.start_time >= now_utc,
        )
        .order_by(Appointment.start_time.asc())
        .all()
    )
    return appointments
