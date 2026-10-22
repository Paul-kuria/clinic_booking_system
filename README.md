# Clinic Booking System - Backend API

A production-ready REST API for managing doctor appointments in a small clinic, built with **Python**, **FastAPI**, and **PostgreSQL**.

* **Live API Base URL:** [https://clinic-booking-api-ygs4.onrender.com](https://clinic-booking-api-ygs4.onrender.com)
* **Interactive API Docs (Swagger UI):** [https://clinic-booking-api-ygs4.onrender.com/docs](https://clinic-booking-api-ygs4.onrender.com/docs)
* **Health Check Probe:** [https://clinic-booking-api-ygs4.onrender.com/health](https://clinic-booking-api-ygs4.onrender.com/health)

---

## Section 1: System Design

### 1. Models & Schema Design
To keep things lean while planning for future clinic growth, I broke down the system into four core models:

* **Doctor**: Represents clinic practitioners.
  * Fields: `id`, `name`, `email`, `specialty`, `created_at`
* **DoctorSchedule (Working Hours)**: Defines recurring working hours per doctor per weekday.
  * Fields: `id`, `doctor_id` (FK), `day_of_week` (0=Monday ... 6=Sunday), `start_time`, `end_time`
  * *Why a separate table?* Doctors rarely work identical hours every day of the week. Storing weekly schedules in a dedicated table allows each doctor to have custom shifts (e.g. mornings on Monday, full day on Wednesday) without hardcoding business hours in application logic.
* **Patient**: Represents patients booking sessions.
  * Fields: `id`, `name`, `email`, `phone`, `created_at`
* **Appointment**: Represents a booked, cancelled, or rescheduled slot.
  * Fields: `id`, `doctor_id` (FK), `patient_id` (FK), `start_time` (UTC), `end_time` (UTC), `status` (`BOOKED` | `CANCELLED`), `cancellation_reason`, `created_at`, `updated_at`

#### Why is "Slot" not a database table?
Instead of pre-generating and storing thousands of empty 30-minute rows in the database (bloats storage and creates a nightmare whenever a doctor changes their shift), **availability is calculated dynamically on request**:
1. Look up the doctor's working hours for the requested day of the week.
2. Chop the working hours into 30-minute intervals.
3. Query the database for active appointments for that doctor on that date.
4. Filter out any slots that are already booked, in the past, or within the 1-hour notice window.
5. Return whatever slots remain as available.

---

### 2. Architecture & Components
The codebase uses a clean, layered architecture to make sure concerns are kept separate:

* **`app/api/v1/` (Routers)**: The HTTP layer. Handles incoming requests, enforces status codes, and translates payloads. The routers do not handle business logic or touch database queries directly.
* **`app/schemas/` (Pydantic DTOs)**: Handles input validation, ensuring timestamps fall on exact `:00` or `:30` boundaries with zero seconds.
* **`app/services/` (Business Logic)**: The brain of the application. Contains the rules for slot availability, booking validations, cancellation guards, and atomic rescheduling. This layer is decoupled from HTTP, making it fast and easy to test.
* **`app/models/` (SQLAlchemy ORM)**: Maps directly to PostgreSQL tables, relations, and database-level constraints.
* **`app/core/` (Configuration & DB Setup)**: App settings via `pydantic-settings`, connection pooling, and session management.

---

### 3. Key Decisions

1. **Two-Way Race Condition Prevention (Partial Unique Indexes)**
   * *The Problem*: If two patients click "Book" on the same doctor at 10:00 AM at the exact same millisecond, a simple check-in-code (`if not is_booked`) has a race condition where both requests see the slot is empty and both insert.
   * *The Solution*: A two-tier defense:
     * **Code check**: First queries the database to return clean, friendly `409 Conflict` errors under normal traffic.
     * **Database vault**: A PostgreSQL **partial unique index** enforces exclusivity at the storage level:
       ```sql
       CREATE UNIQUE INDEX uq_doctor_active_slot 
       ON appointments (doctor_id, start_time) 
       WHERE status = 'BOOKED';
       ```
   * *Patient Protection*: A patient also cannot physically attend two appointments at the same time. I added an equivalent partial unique index on `(patient_id, start_time) WHERE status = 'BOOKED'`, preventing a patient from double-booking themselves across different doctors.
2. **UTC in the Database, Nairobi Time for the Clinic**
   * All timestamps are saved in the database strictly in **UTC (`timezone=True`)**.
   * Doctor working schedules (e.g. 09:00 - 17:00) operate on the clinic's local timezone (`Africa/Nairobi`, UTC+3). When generating availability or validating bookings, the date is localized to Nairobi time to establish shift boundaries, and then converted to UTC for database queries.
3. **Soft Cancellations with History**
   * When an appointment is cancelled, we do not delete the row. We mark `status = 'CANCELLED'` and record the `cancellation_reason` for clinical audit.
   * Because the partial unique index only applies `WHERE status = 'BOOKED'`, the slot immediately opens back up for other patients to book without deleting history.
4. **Atomic Rescheduling**
   * Rescheduling runs inside a single database transaction: validating the new slot, freeing the old slot, and locking the new slot atomically. If anything fails, the transaction rolls back cleanly.

---

### 4. Trade-offs Considered

* **PostgreSQL over SQLite**: SQLite is fine for quick demos, but it doesn't natively enforce PostgreSQL-style partial unique indexes without workarounds, and it stores timestamps as naive text strings. PostgreSQL gives us real ACID concurrency control and index filtering.
* **Fixed 30-Minute Slots vs. Variable Durations**:
  * Fixed 30-minute slots aligned to `:00` and `:30` allow using partial unique indexes on `start_time`.
  * If the clinic ever introduces variable lengths (e.g. 45-min physio vs 15-min checkup), we would upgrade to PostgreSQL **GiST exclusion constraints** using `tstzrange`.
* **No Authentication (For Now)**:
  * To focus strictly on core booking logic, concurrency, and validation within the assessment scope, authentication was omitted. `patient_id` is passed directly in the payload. In a production build, this would be extracted from a verified JWT session.

---

## Section 2: API Implementation

### 1. Endpoints Reference

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `POST` | `/appointments` | Book a 30-minute slot | `201`, `400`, `404`, `409`, `422` |
| `GET` | `/doctors/{id}/availability?date=YYYY-MM-DD` | Get available 30-min slots for a date | `200`, `404`, `422` |
| `PATCH` | `/appointments/{id}/cancel` | Cancel an appointment with a reason | `200`, `404`, `409`, `422` |
| `PATCH` | `/appointments/{id}/reschedule` | Move appointment to a new slot | `200`, `400`, `404`, `409`, `422` |
| `GET` | `/patients/{id}/appointments` | *(Bonus)* Upcoming active appointments for a patient | `200`, `404` |
| `GET` | `/doctors` | List all doctors and their weekly schedules | `200` |
| `GET` | `/patients` | List registered patients | `200` |
| `GET` | `/health` | Health check probe | `200` |

---

### 2. Payload Examples

#### A. Book an Appointment
* **POST** `/appointments`
```json
{
  "doctor_id": 1,
  "patient_id": 1,
  "start_time": "2026-10-25T07:00:00Z"
}
```
* **Response (201 Created):**
```json
{
  "id": 1,
  "doctor_id": 1,
  "patient_id": 1,
  "start_time": "2026-10-25T07:00:00Z",
  "end_time": "2026-10-25T07:30:00Z",
  "status": "BOOKED",
  "cancellation_reason": null,
  "created_at": "2026-10-22T10:30:00Z",
  "updated_at": "2026-10-22T10:30:00Z"
}
```

#### B. Check Availability
* **GET** `/doctors/1/availability?date=2026-10-25`
* **Response (200 OK):**
```json
{
  "doctor_id": 1,
  "doctor_name": "Dr. Angela Wanjiku",
  "date": "2026-10-25",
  "available_slots": [
    {
      "start_time": "2026-10-25T05:30:00Z",
      "end_time": "2026-10-25T06:00:00Z"
    },
    {
      "start_time": "2026-10-25T06:00:00Z",
      "end_time": "2026-10-25T06:30:00Z"
    }
  ]
}
```

#### C. Cancel an Appointment
* **PATCH** `/appointments/1/cancel`
```json
{
  "reason": "Recovered earlier than expected"
}
```
* **Response (200 OK):** returns status `CANCELLED`. Subsequent calls return `409 Conflict`.

#### D. Reschedule an Appointment
* **PATCH** `/appointments/1/reschedule`
```json
{
  "new_start_time": "2026-10-25T08:00:00Z"
}
```
* **Response (200 OK):** atomically updates slot. The previous slot becomes immediately available for other patients.

---

### 3. How to Run Locally

#### Prerequisites
* [uv](https://docs.astral.sh/uv/) (fast Python package manager)
* [Docker](https://www.docker.com/) & Docker Compose

#### Option 1: Local Development with `uv`
1. Clone the repo:
   ```bash
   git clone <repo-url>
   cd techsavannah_backend
   ```
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Start the PostgreSQL database:
   ```bash
   docker compose up db -d
   ```
4. Run migrations:
   ```bash
   uv run alembic upgrade head
   ```
5. Start the FastAPI server:
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```
6. Open docs: `http://localhost:8000/docs`

#### Option 2: Run Full Stack via Docker
```bash
docker compose up --build
```

#### Running Tests
Run the 18 automated unit and integration tests:
```bash
uv run pytest -v
```

---

## Section 3: Deployment & CI/CD

### 1. Deployed Application
* **Live Base URL:** [https://clinic-booking-api-ygs4.onrender.com](https://clinic-booking-api-ygs4.onrender.com)
* **Live Interactive Docs:** [https://clinic-booking-api-ygs4.onrender.com/docs](https://clinic-booking-api-ygs4.onrender.com/docs)
* **Live Health Check:** [https://clinic-booking-api-ygs4.onrender.com/health](https://clinic-booking-api-ygs4.onrender.com/health)

### 2. Which branch triggers deployment and how?
* **Branch:** `main`
* **Trigger:** Every merge or direct push to `main`.
* **How it works:**
  1. **CI Verification:** On any Pull Request targeting `main`, GitHub Actions automatically spins up an Ubuntu runner, installs Python 3.13 and `uv`, installs dependencies, and runs all 18 Pytest unit and integration tests.
  2. **Merge Gate:** Once the PR is verified and merged into `main`, Render's GitHub webhook automatically detects the updated commit on `main`.
  3. **Auto-Deploy:** Render builds the Docker container from our multi-stage `Dockerfile`, applies database configurations declared in `render.yaml`, executes startup database verification and idempotent seeding, and brings the updated build live with zero downtime.


---

## Section 4: AI Reflection

The complete reflection on AI usage across the four sections of this assessment is documented in [REFLECTION.md](REFLECTION.md).