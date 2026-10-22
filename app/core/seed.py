from datetime import time
from sqlalchemy.orm import Session
from app.models.doctor import Doctor, DoctorSchedule
from app.models.patient import Patient


def seed_initial_data(db: Session) -> None:
    """
    Seeds the 5 clinic doctors (Physiotherapy, Dermatology, Nutrition),
    their weekly working schedules, and sample patients.
    Idempotent: checks each record by email so existing data is preserved.
    """
    doctors_data = [
        {
            "name": "Dr. Angela Wanjiku",
            "email": "angela.wanjiku@clinic.co.ke",
            "specialty": "Sports & Orthopedic Physiotherapy",
            # Mon to Fri (0 to 4), 08:30 - 16:30
            "schedules": [
                (day, time(8, 30), time(16, 30)) for day in range(5)
            ],
        },
        {
            "name": "Dr. Brian Otieno",
            "email": "brian.otieno@clinic.co.ke",
            "specialty": "Neuro-Rehabilitation & Spine Care",
            # Mon to Fri (0 to 4), 09:00 - 17:00
            "schedules": [(day, time(9, 0), time(17, 0)) for day in range(5)],
        },
        {
            "name": "Dr. Claire Muthoni",
            "email": "claire.muthoni@clinic.co.ke",
            "specialty": "Pediatric & Geriatric Physiotherapy",
            # Tue to Sat (1 to 5), 08:00 - 16:00
            "schedules": [(day, time(8, 0), time(16, 0)) for day in range(1, 6)],
        },
        {
            "name": "Dr. David Kiprop",
            "email": "david.kiprop@clinic.co.ke",
            "specialty": "Dermatology & Skin Health",
            # Mon, Wed, Fri (0, 2, 4), 09:00 - 17:00
            "schedules": [(day, time(9, 0), time(17, 0)) for day in (0, 2, 4)],
        },
        {
            "name": "Dr. Esther Njeri",
            "email": "esther.njeri@clinic.co.ke",
            "specialty": "Clinical Nutrition & Dietetics",
            # Mon to Fri (0 to 4), 10:00 - 18:00
            "schedules": [(day, time(10, 0), time(18, 0)) for day in range(5)],
        },
    ]

    for d in doctors_data:
        doctor = db.query(Doctor).filter(Doctor.email == d["email"]).first()
        if not doctor:
            doctor = Doctor(
                name=d["name"], email=d["email"], specialty=d["specialty"]
            )
            db.add(doctor)
            db.flush()

            for day, start_t, end_t in d["schedules"]:
                sched = DoctorSchedule(
                    doctor_id=doctor.id,
                    day_of_week=day,
                    start_time=start_t,
                    end_time=end_t,
                )
                db.add(sched)
        else:
            # Update specialty in case it was changed
            if doctor.specialty != d["specialty"]:
                doctor.specialty = d["specialty"]

    # Seed 2 sample patients if none exist
    sample_patients = [
        {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+254712345678",
        },
        {
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone": "+254798765432",
        },
    ]
    for p in sample_patients:
        patient = db.query(Patient).filter(Patient.email == p["email"]).first()
        if not patient:
            db.add(Patient(name=p["name"], email=p["email"], phone=p["phone"]))

    db.commit()
