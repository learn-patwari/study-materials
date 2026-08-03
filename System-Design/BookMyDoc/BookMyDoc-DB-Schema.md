# Database Schema — BookMyDoc

> Source: learn-patwari/book-my-doc

## Strategy
- **`public` schema:** Platform-level tables (shared across all tenants)
- **`tenant_{slug}` schema:** Per-clinic isolated tables (set via `search_path`)

---

## Public Schema

### `tenants`
```sql
CREATE TABLE public.tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        VARCHAR(63) UNIQUE NOT NULL,        -- URL-safe identifier
    name        VARCHAR(255) NOT NULL,
    plan_id     UUID REFERENCES public.subscription_plans(id),
    status      VARCHAR(20) DEFAULT 'active',       -- active, suspended, cancelled
    schema_name VARCHAR(63) GENERATED ALWAYS AS ('tenant_' || slug) STORED,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_tenants_slug ON public.tenants(slug);
CREATE INDEX idx_tenants_status ON public.tenants(status);
```

### `subscription_plans`
```sql
CREATE TABLE public.subscription_plans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(50) NOT NULL,        -- Starter, Growth, Enterprise
    price_monthly       NUMERIC(10,2) NOT NULL,
    max_doctors         INTEGER,                     -- NULL = unlimited
    max_appointments    INTEGER,                     -- NULL = unlimited
    storage_gb          INTEGER,
    sms_monthly         INTEGER,
    features            JSONB DEFAULT '{}',
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### `platform_admins`
```sql
CREATE TABLE public.platform_admins (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### `platform_audit_logs`
```sql
CREATE TABLE public.platform_audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    admin_id    UUID REFERENCES public.platform_admins(id),
    action      VARCHAR(100) NOT NULL,
    entity      VARCHAR(100),
    entity_id   UUID,
    ip_address  INET,
    user_agent  TEXT,
    payload     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_platform_audit_created ON public.platform_audit_logs(created_at DESC);
```

---

## Per-Tenant Schema (template applied to each `tenant_{slug}`)

### `users`
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(15) UNIQUE,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL,            -- clinic_admin, doctor, patient
    password_hash   VARCHAR(255),
    is_active       BOOLEAN DEFAULT TRUE,
    is_verified     BOOLEAN DEFAULT FALSE,
    avatar_url      TEXT,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_email_or_phone CHECK (email IS NOT NULL OR phone IS NOT NULL)
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_role ON users(role);
```

### `clinics`
```sql
CREATE TABLE clinics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    tagline         VARCHAR(500),
    address_line1   VARCHAR(255) NOT NULL,
    address_line2   VARCHAR(255),
    city            VARCHAR(100) NOT NULL,
    state           VARCHAR(100) NOT NULL,
    pincode         VARCHAR(10) NOT NULL,
    phone           VARCHAR(15),
    email           VARCHAR(255),
    website         VARCHAR(255),
    gstin           VARCHAR(20),
    logo_url        TEXT,
    timezone        VARCHAR(50) DEFAULT 'Asia/Kolkata',
    working_hours   JSONB NOT NULL DEFAULT '{}',    -- {mon: {open:"09:00",close:"18:00",...}}
    slot_duration   INTEGER DEFAULT 15,             -- minutes
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### `doctors`
```sql
CREATE TABLE doctors (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    registration_number VARCHAR(50),                -- Medical Council reg no
    specialization      VARCHAR(100) NOT NULL,
    qualifications      TEXT[],                     -- ['MBBS', 'MD', 'DNB']
    experience_years    INTEGER DEFAULT 0,
    consultation_fee    NUMERIC(10,2) DEFAULT 0,
    bio                 TEXT,
    languages           TEXT[] DEFAULT ARRAY['English', 'Hindi'],
    is_available        BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);
CREATE INDEX idx_doctors_specialization ON doctors(specialization);
CREATE INDEX idx_doctors_available ON doctors(is_available);
```

### `doctor_schedules`
```sql
CREATE TABLE doctor_schedules (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id   UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL,                  -- 0=Mon, 6=Sun
    start_time  TIME NOT NULL,
    end_time    TIME NOT NULL,
    break_start TIME,
    break_end   TIME,
    is_active   BOOLEAN DEFAULT TRUE,
    UNIQUE(doctor_id, day_of_week)
);
CREATE INDEX idx_schedules_doctor ON doctor_schedules(doctor_id);
```

### `doctor_leaves`
```sql
CREATE TABLE doctor_leaves (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id   UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    leave_date  DATE NOT NULL,
    reason      VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_leaves_doctor_date ON doctor_leaves(doctor_id, leave_date);
```

### `patients`
```sql
CREATE TABLE patients (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dob                 DATE,
    gender              VARCHAR(10),                -- male, female, other
    blood_group         VARCHAR(5),                 -- A+, B-, O+, AB+, etc.
    height_cm           NUMERIC(5,1),
    weight_kg           NUMERIC(5,1),
    allergies           TEXT[],
    chronic_conditions  TEXT[],
    emergency_contact   JSONB,                      -- {name, relation, phone}
    abha_id             VARCHAR(20) UNIQUE,         -- Ayushman Bharat Health Account
    aadhaar_last4       VARCHAR(4),                 -- last 4 digits only
    address             JSONB,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);
CREATE INDEX idx_patients_abha ON patients(abha_id);
```

### `appointments`
```sql
CREATE TABLE appointments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id       UUID NOT NULL REFERENCES doctors(id),
    patient_id      UUID NOT NULL REFERENCES patients(id),
    slot_start      TIMESTAMPTZ NOT NULL,
    slot_end        TIMESTAMPTZ NOT NULL,
    type            VARCHAR(20) DEFAULT 'in_person', -- in_person, video
    status          VARCHAR(20) DEFAULT 'scheduled', -- scheduled, confirmed, checked_in,
                                                      -- completed, cancelled, no_show
    chief_complaint TEXT,
    notes           TEXT,                            -- doctor's notes
    cancel_reason   VARCHAR(255),
    booked_by       UUID REFERENCES users(id),       -- who booked (patient or staff)
    token_number    INTEGER,                         -- queue token for walk-ins
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_appt_doctor_slot ON appointments(doctor_id, slot_start);
CREATE INDEX idx_appt_patient ON appointments(patient_id);
CREATE INDEX idx_appt_status ON appointments(status);
CREATE INDEX idx_appt_date ON appointments(DATE(slot_start AT TIME ZONE 'Asia/Kolkata'));
```

### `medical_records`
```sql
CREATE TABLE medical_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id),
    appointment_id  UUID REFERENCES appointments(id),
    record_type     VARCHAR(50) NOT NULL,   -- lab_report, radiology, referral,
                                            -- discharge_summary, vaccination, other
    title           VARCHAR(255) NOT NULL,
    file_url        TEXT NOT NULL,          -- MinIO pre-signed base path
    file_name       VARCHAR(255) NOT NULL,
    file_size_bytes INTEGER,
    mime_type       VARCHAR(100),
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    notes           TEXT,
    record_date     DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_records_patient ON medical_records(patient_id, created_at DESC);
CREATE INDEX idx_records_type ON medical_records(patient_id, record_type);
```

### `prescriptions`
```sql
CREATE TABLE prescriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id  UUID NOT NULL REFERENCES appointments(id),
    doctor_id       UUID NOT NULL REFERENCES doctors(id),
    patient_id      UUID NOT NULL REFERENCES patients(id),
    is_digital      BOOLEAN DEFAULT TRUE,
    file_url        TEXT,                   -- for scanned upload
    pdf_url         TEXT,                   -- generated PDF for digital
    diagnosis       TEXT,
    advice          TEXT,
    follow_up_days  INTEGER,
    issued_at       TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_rx_patient ON prescriptions(patient_id, issued_at DESC);
CREATE INDEX idx_rx_appointment ON prescriptions(appointment_id);
```

### `prescription_items`
```sql
CREATE TABLE prescription_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prescription_id UUID NOT NULL REFERENCES prescriptions(id) ON DELETE CASCADE,
    medicine_name   VARCHAR(255) NOT NULL,
    generic_name    VARCHAR(255),
    dosage          VARCHAR(100),           -- "500mg", "5ml"
    frequency       VARCHAR(50),            -- OD, BD, TDS, QID, SOS
    duration        VARCHAR(100),           -- "5 days", "2 weeks", "1 month"
    route           VARCHAR(50),            -- Oral, Topical, IV, IM
    instructions    TEXT,                   -- "After food", "With warm water"
    sort_order      SMALLINT DEFAULT 0
);
CREATE INDEX idx_rx_items_prescription ON prescription_items(prescription_id);
```

### `follow_ups`
```sql
CREATE TABLE follow_ups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id  UUID NOT NULL REFERENCES appointments(id),
    patient_id      UUID NOT NULL REFERENCES patients(id),
    doctor_id       UUID NOT NULL REFERENCES doctors(id),
    due_date        DATE NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',  -- pending, scheduled, completed, missed
    notes           TEXT,
    reminder_sent   BOOLEAN DEFAULT FALSE,
    linked_appt_id  UUID REFERENCES appointments(id), -- appointment created for follow-up
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_followup_patient ON follow_ups(patient_id, due_date);
CREATE INDEX idx_followup_status ON follow_ups(status, due_date);
CREATE INDEX idx_followup_doctor ON follow_ups(doctor_id, due_date);
```

### `notifications`
```sql
CREATE TABLE notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    type        VARCHAR(50) NOT NULL,       -- appointment_reminder, prescription_ready, etc.
    channel     VARCHAR(20) NOT NULL,       -- sms, email, push, in_app
    title       VARCHAR(255),
    content     TEXT NOT NULL,
    is_read     BOOLEAN DEFAULT FALSE,
    sent_at     TIMESTAMPTZ,
    status      VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed, delivered
    metadata    JSONB DEFAULT '{}',         -- {appointment_id, etc.}
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_notif_user ON notifications(user_id, created_at DESC);
CREATE INDEX idx_notif_status ON notifications(status, created_at);
```

### `reviews`
```sql
CREATE TABLE reviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id       UUID NOT NULL REFERENCES doctors(id),
    patient_id      UUID NOT NULL REFERENCES patients(id),
    appointment_id  UUID NOT NULL REFERENCES appointments(id) UNIQUE,
    rating          SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment         TEXT,
    is_visible      BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(patient_id, appointment_id)
);
CREATE INDEX idx_reviews_doctor ON reviews(doctor_id, rating DESC);
```

### `audit_logs`
```sql
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    role        VARCHAR(20),
    action      VARCHAR(100) NOT NULL,      -- CREATE, UPDATE, DELETE, VIEW, LOGIN, etc.
    entity      VARCHAR(100),               -- Appointment, Patient, Prescription, etc.
    entity_id   UUID,
    old_values  JSONB,
    new_values  JSONB,
    ip_address  INET,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_entity ON audit_logs(entity, entity_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

---

## Entity Relationship Summary

```
tenants (public)
  └── [schema created per tenant]
        ├── users ──────────────── doctors ─── doctor_schedules
        │                    │              └── doctor_leaves
        │                    └── patients
        │
        ├── appointments ─── prescriptions ─── prescription_items
        │        │      └─── follow_ups
        │        └────────── medical_records
        │
        ├── notifications
        ├── reviews
        └── audit_logs
```
