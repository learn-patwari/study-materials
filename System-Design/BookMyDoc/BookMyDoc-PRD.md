# Product Requirement Document
# BookMyDoc — Multi-Tenant Healthcare SaaS Platform

> Source: learn-patwari/book-my-doc

**Version:** 1.0  
**Date:** 2026-06-20  
**Target Market:** India  

---

## 1. Executive Summary

BookMyDoc is a cloud-native, multi-tenant SaaS platform that enables private clinics, polyclinics, and specialty chains across India to digitize their entire patient journey — from appointment booking to discharge and follow-up — without managing their own infrastructure.

The platform operates on a **shared-infrastructure, isolated-data** model: every clinic (tenant) owns its data in a segregated PostgreSQL schema while sharing compute, storage, and networking resources to keep operational costs low.

**Vision:** Become the operating system for independent healthcare providers in India.

---

## 2. Target Market

| Segment | Description | Size |
|---|---|---|
| Independent clinics | 1–5 doctor practices in Tier 1–3 cities | ~500,000 |
| Polyclinics | Multi-specialty, 5–20 doctors | ~50,000 |
| Specialty chains | Dermatology, dental, eye care chains | ~10,000 |
| Diagnostic centres | Lab + radiology, EMR upload focus | ~30,000 |

**Initial focus:** Independent clinics and polyclinics in metro and Tier-2 cities (Delhi, Mumbai, Bengaluru, Hyderabad, Pune, Jaipur, Lucknow).

---

## 3. User Personas

### 3.1 Super Admin (Platform Operator)
- Manages tenant onboarding, subscription plans, and platform health
- Access to cross-tenant analytics (anonymized)
- Can impersonate clinic admin for support

### 3.2 Clinic Admin
- Sets up clinic profile, working hours, and service fees
- Manages doctors and support staff
- Views clinic-level reports and revenue summaries
- Configures notification preferences

### 3.3 Doctor
- Manages personal schedule and availability
- Views patient appointments and history
- Creates digital prescriptions and accesses EMR
- Manages follow-up reminders

### 3.4 Patient
- Self-registers or is registered by clinic staff
- Books appointments online or in-clinic
- Views appointment history and prescriptions
- Receives SMS/email reminders

---

## 4. Feature Matrix

| Feature | Super Admin | Clinic Admin | Doctor | Patient |
|---|---|---|---|---|
| Tenant management | ✅ | — | — | — |
| Subscription billing | ✅ | View | — | — |
| Clinic settings | — | ✅ | View | — |
| Doctor management | — | ✅ | Self | — |
| Patient management | — | ✅ | View | Self |
| Appointment booking | — | ✅ | View | ✅ |
| Appointment management | — | ✅ | ✅ | Cancel only |
| Digital prescription | — | — | ✅ | View |
| EMR / Medical records | — | ✅ | ✅ | View own |
| Follow-up management | — | ✅ | ✅ | View |
| Notifications | ✅ | ✅ | ✅ | ✅ |
| Reports | Platform-level | Clinic-level | Own stats | — |
| Audit logs | ✅ | Clinic-level | — | — |

---

## 5. Core Modules

### 5.1 Multi-Tenant SaaS
- Schema-per-tenant isolation in PostgreSQL
- Tenant resolution via `X-Tenant-Slug` header or subdomain
- Per-tenant feature flags based on subscription tier
- Tenant onboarding wizard (clinic profile → first doctor → schedule setup)

### 5.2 Authentication & Authorization
- Phone/email + OTP registration for patients
- Email + password for clinic staff and doctors
- JWT access tokens (15-minute TTL)
- Refresh tokens stored in Redis (7-day TTL, rotated on use)
- RBAC: 4 roles with granular permission checks via FastAPI dependencies
- Password reset via OTP (email/SMS)

### 5.3 Clinic Management
- Clinic profile: name, address, GSTIN, logo, contact
- Working hours per day with break times (JSONB)
- Holiday calendar
- Multi-branch support (future: each branch = separate tenant)
- Fee configuration per service type

### 5.4 Doctor Management
- Doctor profile: specialization, qualification, experience, bio, photo
- Weekly schedule with time slots (configurable duration: 10/15/20/30 min)
- Per-doctor consultation fee
- Availability toggle (leave management)
- Doctor-specific booking link

### 5.5 Patient Management
- Patient registration with Aadhaar/ABHA ID (optional)
- Demographics: DOB, gender, blood group, allergies, emergency contact
- Patient search by name / phone / ABHA
- Patient merge (duplicate prevention)
- Patient portal: self-service history view

### 5.6 Appointment Booking
- Real-time slot availability query
- Booking channels: online (patient) + walk-in (clinic staff)
- Appointment types: In-person, Video consultation
- Status lifecycle: Scheduled → Confirmed → Checked-In → Completed / Cancelled / No-Show
- Cancellation policy: configurable per clinic
- Waitlist for fully-booked slots

### 5.7 Medical Records (EMR)
- File upload: PDF, JPEG, PNG (lab reports, scans, referrals)
- Record types: Lab Report, Radiology, Referral, Discharge Summary, Other
- Per-patient record timeline view
- MinIO storage with pre-signed URL download
- Record sharing: generate time-limited share link

### 5.8 Prescription Management
- Scanned prescription upload (PDF/image)
- Digital prescription builder:
  - Medicine name (autocomplete from common Indian drugs)
  - Dosage, frequency (OD/BD/TDS/QID), duration
  - Instructions (before/after food, with water, etc.)
  - Doctor digital signature
- PDF generation and patient delivery via SMS/email
- Prescription history per patient

### 5.9 Follow-Up Management
- Create follow-up from appointment completion
- Configurable reminder intervals (3 days / 1 week / 2 weeks / 1 month)
- Follow-up status: Pending → Scheduled → Completed / Missed
- Bulk follow-up report for clinic admin

### 5.10 Notifications
- Channels: SMS (via Fast2SMS/MSG91), Email (via SendGrid/SMTP), In-app
- Templates: Appointment confirmation, reminder (24h, 2h), cancellation, prescription ready, follow-up due
- Patient notification preferences
- Notification delivery status tracking

### 5.11 Reporting & Analytics
- Appointment metrics: total, completed, cancelled, no-show rates
- Revenue summary by doctor / period
- Doctor utilization and slot fill rate
- Patient demographics breakdown
- Export to CSV/Excel

### 5.12 Audit Logs
- All data-modifying actions logged with: user, action, entity, old/new values, IP, timestamp
- Tamper-proof append-only log table
- Filterable audit trail in clinic admin panel

---

## 6. Non-Functional Requirements

| Requirement | Target |
|---|---|
| API response time (p95) | < 200ms for read, < 500ms for write |
| Uptime | 99.9% monthly |
| Concurrent users per tenant | 100 (Starter), 500 (Growth), unlimited (Enterprise) |
| Data residency | India (ap-south-1 or in-mum) |
| DPDP Act 2023 compliance | Consent collection, data deletion on request, breach notification |
| Session security | HTTPS only, SameSite cookies, CORS whitelist |
| File storage | Max 50MB per file, 5GB per tenant (Starter) |
| Password policy | Min 8 chars, 1 uppercase, 1 number |
| Rate limiting | 100 req/min auth endpoints, 1000 req/min general |

---

## 7. Subscription Tiers

| Feature | Starter (Free) | Growth (₹2,999/mo) | Enterprise (₹9,999/mo) |
|---|---|---|---|
| Doctors | 1 | 10 | Unlimited |
| Appointments/month | 200 | 2,000 | Unlimited |
| Storage | 1 GB | 10 GB | 100 GB |
| SMS notifications | 100/mo | 1,000/mo | Unlimited |
| Reports | Basic | Advanced | Custom |
| API access | — | — | ✅ |
| White-label | — | — | ✅ |
| SLA | Community | Business hours | 24/7 |

---

## 8. Constraints & Assumptions

- Internet connectivity: assume 4G minimum (UI must be lightweight, lazy-load heavy assets)
- Language: English UI for MVP; Hindi/regional language support in v2
- Payment integration: out of scope for MVP (future: Razorpay)
- Video consultation: out of scope for MVP (future: WebRTC or Twilio integration)
- ABHA integration: best-effort via NHA APIs (future milestone)
- All times stored in UTC, displayed in clinic's configured timezone (IST default)
