from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.patient import Patient
from app.schemas.patient import PatientOut, PatientAppointmentOut
from app.services.appointment_service import get_patient_upcoming_appointments

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get(
    "",
    response_model=list[PatientOut],
    summary="List all registered patients",
)
def list_patients(db: Session = Depends(get_db)):
    return db.query(Patient).all()


@router.get(
    "/{id}/appointments",
    response_model=list[PatientAppointmentOut],
    summary="Get upcoming active appointments for a patient sorted by date",
)
def get_patient_appointments(id: int, db: Session = Depends(get_db)):
    appointments = get_patient_upcoming_appointments(db=db, patient_id=id)
    # Map to schema with doctor info
    results = []
    for appt in appointments:
        results.append(
            PatientAppointmentOut(
                id=appt.id,
                doctor_id=appt.doctor_id,
                doctor_name=appt.doctor.name if appt.doctor else "Unknown",
                doctor_specialty=(
                    appt.doctor.specialty if appt.doctor else "General"
                ),
                start_time=appt.start_time,
                end_time=appt.end_time,
                status=appt.status,
                cancellation_reason=appt.cancellation_reason,
            )
        )
    return results
