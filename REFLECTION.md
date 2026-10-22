# Section 4: AI Reflection

### 1. What did you use AI for across the four sections?

* **Section 1 (System Design):**
  Before touching AI, I had already mapped out the core domain entities (Doctor, Schedule, Patient, Appointment) and the request flows in my notes. I used AI as an architectural sounding board and to help review as I walk-through edge cases, discussing how to best handle slot exclusivity, and confirming that enforcing a partial unique constraint was the cleanest solution for race condition protection.
* **Section 2 (API Implementation):**
  I used AI to accelerate boilerplate generation: scaffolding Pydantic request/response schemas, structuring FastAPI router endpoints, and setting up initial seed templates. However, I drove the business logic, edge-case constraints, and model definitions myself to ensure the domain rules were strictly followed.
* **Section 3 (Deployment & CI/CD):**
  I used AI as a reference manual, refreshing my syntax on writing a Render Infrastructure-as-Code Blueprint (`render.yaml`) and setting up the GitHub Actions workflow using the modern `astral-sh/setup-uv` action.

---

### 2. Give one example where an AI suggestion improved your work. What did you prompt it with?

* **The Improvement:** Handling the timezones between database storage (UTC) and clinic operations (`Africa/Nairobi`, UTC+3). Rather than doing ad-hoc conversions inside endpoint handlers, AI helped formalize a clean translation pattern: localizing the requested date to Nairobi time first, constructing slot intervals in local clinic hours, and then converting to UTC for database queries and storage.
* **The Prompt:**
  > *"I want to store appointment timestamps in the database strictly in UTC, but the clinic operates in Nairobi (UTC+3) where doctor working hours (e.g. 09:00 - 17:00) and patient booking decisions happen in local time. What is the cleanest pattern to handle schedule generation, slot boundaries, and database queries without introducing timezone drift or off-by-one errors?"*

---

### 3. Give one example where AI output was wrong or incomplete and how you caught it.

* **The Issue:**
  During our initial discussion on concurrency, the AI suggested only protecting the doctor from double-booking, proposing that we leave patient double-booking as an "acceptable limitation" to keep the schema simple.
* **How I Caught It:**
  I caught this because I was thinking from the clinic's real-world operational perspective: a patient cannot physically be in two different consultation rooms with two different doctors at 10:00 AM. Allowing a patient to book Dr. Angela and Dr. Brian at the exact same time is a domain bug. I pushed back and insisted on implementing symmetric protection: checking for active patient bookings in code and adding a secondary partial unique index on `(patient_id, start_time) WHERE status = 'BOOKED'`.

---

### 4. Name two decisions you made without AI. Why did you trust your own judgment there?

1. **Dynamic 30-Minute Slot Calculation over Pre-Generated Database Rows:**
   * It's tempting to think of calendar slots as database rows (`Slot` table). But pre-populating 30-minute intervals creates thousands of empty records per doctor per year and creates massive synchronization friction whenever doctor hours change. I decided early on to compute slots dynamically on request by dividing working hours and subtracting booked appointments. It is stateless, lean, and avoids database bloat.
2. **Preventing Race Conditions via PostgreSQL Partial Unique Constraints:**
   * Many developers rely on code-level checks (`if existing_booking: raise HTTPException`). I knew from past experience that code-level checks fail under high concurrency due to the classic "check-then-act" race window. I chose to rely on the database engine itself by creating a partial unique index on `(doctor_id, start_time) WHERE status = 'BOOKED'`.
* **Why I trusted my judgment:**
  I prefer to analyze domain problems, explore failure modes, and hand-test edge cases on paper before prompting an AI agent. AI is an incredible accelerator, but foundational architecture, concurrency safety, and real-world domain rules require human engineering judgment.
