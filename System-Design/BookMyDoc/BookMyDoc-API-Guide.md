# API Guide — BookMyDoc

> Source: learn-patwari/book-my-doc

## Base URL
- Development: `http://localhost:8000`
- Production: `https://api.{your-domain}.com`
- Interactive docs: `{BASE_URL}/docs` (Swagger UI)
- ReDoc: `{BASE_URL}/redoc`

## Authentication

All API calls (except registration/login) require:
```
Authorization: Bearer {access_token}
X-Tenant-Slug: {clinic-slug}
```

### Flow
1. `POST /api/v1/auth/register` — Create account, receive tokens
2. `POST /api/v1/auth/login` — Login, receive tokens
3. Use `access_token` in `Authorization` header
4. When access token expires (15 min), `POST /api/v1/auth/refresh` with `refresh_token`

## API Versioning

All endpoints are under `/api/v1/`. Breaking changes create `/api/v2/`.
Non-breaking additions (new fields, new endpoints) happen within the same version.

## Pagination

List endpoints support:
```
?page=1&page_size=20
```
Response includes: `items[]`, `total`, `page`, `page_size`, `total_pages`

## Error Format
```json
{
  "detail": "Human-readable error message",
  "code": "OPTIONAL_ERROR_CODE"
}
```

## Key Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Invalidate refresh token |
| POST | `/api/v1/auth/otp/send` | Send OTP to phone |
| POST | `/api/v1/auth/otp/verify` | Verify OTP |

### Clinic
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/clinics` | Create clinic profile |
| GET | `/api/v1/clinics/me` | Get clinic details |
| PATCH | `/api/v1/clinics/me` | Update clinic details |
| POST | `/api/v1/clinics/me/logo` | Upload clinic logo |

### Doctors
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/doctors` | Create doctor |
| GET | `/api/v1/doctors` | List doctors (filter by specialization) |
| GET | `/api/v1/doctors/{id}` | Get doctor |
| PATCH | `/api/v1/doctors/{id}` | Update doctor |
| GET | `/api/v1/doctors/{id}/schedules` | Get weekly schedule |
| PUT | `/api/v1/doctors/{id}/schedules` | Set weekly schedule |
| POST | `/api/v1/doctors/{id}/leaves` | Add leave date |

### Appointments
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/appointments/slots` | Get available slots for date |
| POST | `/api/v1/appointments` | Book appointment |
| GET | `/api/v1/appointments` | List appointments |
| GET | `/api/v1/appointments/{id}` | Get appointment detail |
| PATCH | `/api/v1/appointments/{id}` | Update status/notes |

### Prescriptions
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/prescriptions` | Create digital prescription |
| POST | `/api/v1/prescriptions/upload` | Upload scanned prescription |
| GET | `/api/v1/prescriptions` | List prescriptions |
| GET | `/api/v1/prescriptions/{id}` | Get prescription |

### Medical Records
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/records` | Upload medical record (multipart) |
| GET | `/api/v1/records` | List records for patient |
| GET | `/api/v1/records/{id}/download` | Get pre-signed download URL |

### Follow-ups
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/follow-ups` | Create follow-up |
| GET | `/api/v1/follow-ups` | List follow-ups |
| PATCH | `/api/v1/follow-ups/{id}` | Update status |

### Reports (Clinic Admin only)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/reports/appointments/summary` | Appointment metrics |
| GET | `/api/v1/reports/doctors/performance` | Doctor performance |

### Admin (Super Admin only)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/tenants` | List all tenants |
| POST | `/api/v1/admin/tenants` | Create tenant |
| PATCH | `/api/v1/admin/tenants/{slug}/suspend` | Suspend tenant |
| PATCH | `/api/v1/admin/tenants/{slug}/activate` | Activate tenant |

## Appointment Status Lifecycle
```
SCHEDULED → CONFIRMED → CHECKED_IN → COMPLETED
          ↓            ↓             
       CANCELLED    NO_SHOW
```
Only valid transitions are accepted. Invalid transitions return HTTP 400.

## File Uploads

Use `multipart/form-data` for:
- `POST /api/v1/records` — medical record upload
- `POST /api/v1/prescriptions/upload` — scanned prescription
- `POST /api/v1/clinics/me/logo` — clinic logo

Max file size: 50MB (enforced by Nginx)
