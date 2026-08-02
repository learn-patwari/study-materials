# Smart Parking Lot — Low-Level Design (Backend)

## 1) Scope & Assumptions

### Functional scope
- Vehicle **entry**: assign a spot based on vehicle size/type + availability; generate a ticket/session.
- Vehicle **exit**: close the session; compute fee; mark spot free.
- **Real-time availability**: reflect spot state changes immediately.

### Explicit assumptions (can be adjusted)
- Vehicle types map to **spot categories**:
  - `MOTORCYCLE` → `COMPACT`
  - `CAR` → `REGULAR`
  - `BUS` → `LARGE`
- A vehicle occupies exactly **one** spot.
- One active parking session per `license_plate` at a time.
- Payment capture may be synchronous (exit gate waits) or asynchronous (pay-at-kiosk); the design supports either.

### Non-functional requirements
- Correctness under concurrency (multiple gates).
- Low-latency spot assignment (< 100–200ms typical).
- Auditable transactions & fee calculation.
- Horizontal scalability.

---

## 2) High-Level Modules (Modular Monolith, service-ready)

You can implement as a modular monolith first (simpler for LLD) and later split into services.

### Core modules
- **Gate API**: endpoints used by entry/exit gates.
- **Allocation**: spot selection + reservation.
- **Session**: creates/updates parking sessions.
- **Billing**: calculates fee; produces invoice.
- **Inventory/Availability**: maintains spot states and fast availability indexes.
- **Payment** (optional in scope): records payment attempts; integrates external PSP.

### Supporting modules
- **Auth**: gate/kiosk authentication.
- **Events**: publish `SPOT_OCCUPIED`, `SPOT_RELEASED`, `SESSION_STARTED`, `SESSION_ENDED`.

---

## 3) Domain Model (Entities)

### Enums
- `VehicleType`: `MOTORCYCLE | CAR | BUS`
- `SpotType`: `COMPACT | REGULAR | LARGE`
- `SpotStatus`: `AVAILABLE | RESERVED | OCCUPIED | OUT_OF_SERVICE`
- `SessionStatus`: `ACTIVE | CLOSED | CANCELLED`
- `PaymentStatus`: `NOT_REQUIRED | PENDING | PAID | FAILED | REFUNDED`

### Entities
- `ParkingLot` — represents a lot (may have multiple floors).
- `Floor` — a level inside a lot.
- `ParkingSpot` — a physical spot.
- `Vehicle` — identified by license plate and type.
- `ParkingSession` — a ticket/transaction for a parked vehicle.
- `RatePlan` + `RateRule` — pricing configuration.
- `Payment` — payment record (optional if you only compute fee).

---

## 4) Data Model (Relational Schema)

Below is a Postgres-flavored schema; works similarly on MySQL with minor changes.

### 4.1 Tables

#### `parking_lot`
- `id (uuid pk)`
- `name (text)`
- `city (text)`
- `created_at (timestamptz)`

#### `floor`
- `id (uuid pk)`
- `parking_lot_id (uuid fk -> parking_lot.id)`
- `level (int)`
- `name (text)`
- `created_at (timestamptz)`

Indexes:
- `idx_floor_lot_level (parking_lot_id, level)` unique

#### `parking_spot`
- `id (uuid pk)`
- `floor_id (uuid fk -> floor.id)`
- `spot_number (text)`
- `spot_type (text)`  -- `SpotType`
- `status (text)`     -- `SpotStatus`
- `position_x (int)` optional
- `position_y (int)` optional
- `updated_at (timestamptz)`
- `version (int)` for optimistic locking

Constraints:
- unique `(floor_id, spot_number)`

Indexes:
- `idx_spot_floor_type_status (floor_id, spot_type, status)`
- `idx_spot_type_status (spot_type, status)`

#### `vehicle`
- `id (uuid pk)`
- `license_plate (text)`
- `vehicle_type (text)`  -- `VehicleType`
- `created_at (timestamptz)`

Constraints:
- unique `(license_plate)`

#### `parking_session`
- `id (uuid pk)`
- `parking_lot_id (uuid fk)`
- `vehicle_id (uuid fk)`
- `spot_id (uuid fk -> parking_spot.id)`
- `status (text)`        -- `SessionStatus`
- `entry_gate_id (text)`
- `exit_gate_id (text)` nullable
- `entry_time (timestamptz)`
- `exit_time (timestamptz)` nullable
- `rate_plan_id (uuid fk)`
- `fee_amount_cents (bigint)` nullable
- `currency (text)` default 'INR'
- `payment_status (text)`
- `created_at (timestamptz)`
- `updated_at (timestamptz)`
- `idempotency_key (text)` nullable

Constraints:
- unique `(parking_lot_id, idempotency_key)` where `idempotency_key is not null`
- at most one active session per vehicle per lot (enforced via partial unique index):
  - unique `(parking_lot_id, vehicle_id)` where `status = 'ACTIVE'`

Indexes:
- `idx_session_vehicle_status (vehicle_id, status)`
- `idx_session_spot_status (spot_id, status)`
- `idx_session_entry_time (parking_lot_id, entry_time desc)`

#### `rate_plan`
- `id (uuid pk)`
- `parking_lot_id (uuid fk)`
- `name (text)`
- `effective_from (timestamptz)`
- `effective_to (timestamptz)` nullable
- `created_at (timestamptz)`

Indexes:
- `idx_rate_plan_lot_effective (parking_lot_id, effective_from desc)`

#### `rate_rule`
- `id (uuid pk)`
- `rate_plan_id (uuid fk)`
- `vehicle_type (text)`
- `billing_unit_minutes (int)`   -- e.g. 60
- `grace_minutes (int)`          -- e.g. 10
- `base_fee_cents (bigint)`      -- optional
- `per_unit_fee_cents (bigint)`  -- fee per billing unit
- `daily_cap_cents (bigint)` nullable
- `created_at (timestamptz)`

Indexes:
- `idx_rate_rule_plan_vehicle (rate_plan_id, vehicle_type)` unique

#### `payment` (optional)
- `id (uuid pk)`
- `session_id (uuid fk -> parking_session.id)`
- `amount_cents (bigint)`
- `currency (text)`
- `status (text)`  -- `PaymentStatus`
- `provider (text)`
- `provider_ref (text)` nullable
- `created_at (timestamptz)`

Indexes:
- `idx_payment_session (session_id)`

### 4.2 Availability cache (recommended)
To avoid scanning the `parking_spot` table at high load:
- Maintain Redis structures per lot/floor/type, e.g. sorted sets keyed by "distance".
- DB remains source of truth; cache is a performance optimization.

---

## 5) Public APIs (Gate-facing)

Base path: `/api/v1`

### 5.1 Entry
`POST /lots/{lotId}/entry`

Request:
```json
{
  "licensePlate": "KA01AB1234",
  "vehicleType": "CAR",
  "gateId": "GATE-E-1",
  "idempotencyKey": "uuid-or-snowflake"
}
```

Response:
```json
{
  "sessionId": "...",
  "spot": {
    "spotId": "...",
    "floorLevel": 2,
    "spotNumber": "R-2-045",
    "spotType": "REGULAR"
  },
  "entryTime": "2026-02-14T10:12:00Z"
}
```

Errors:
- `409` if lot is full for the requested vehicle type.
- `409` if vehicle already has an active session.

### 5.2 Exit (fee quote + close)
Option A (single call):

`POST /lots/{lotId}/exit`

Request:
```json
{
  "licensePlate": "KA01AB1234",
  "gateId": "GATE-X-1",
  "paid": true,
  "paymentRef": "optional"
}
```

Response:
```json
{
  "sessionId": "...",
  "exitTime": "2026-02-14T12:42:00Z",
  "durationMinutes": 150,
  "fee": {
    "amountCents": 30000,
    "currency": "INR",
    "breakdown": {
      "graceApplied": false,
      "billingUnits": 3,
      "unitMinutes": 60,
      "perUnitFeeCents": 10000,
      "dailyCapApplied": false
    }
  }
}
```

Option B (two-step): `GET /sessions/{sessionId}/quote` then `POST /sessions/{sessionId}/close`.

### 5.3 Availability
`GET /lots/{lotId}/availability`

Response:
```json
{
  "lotId": "...",
  "byType": {
    "COMPACT": 12,
    "REGULAR": 40,
    "LARGE": 2
  },
  "byFloor": [
    {"level": 1, "COMPACT": 5, "REGULAR": 15, "LARGE": 1},
    {"level": 2, "COMPACT": 7, "REGULAR": 25, "LARGE": 1}
  ]
}
```

---

## 6) Spot Allocation Algorithm

### 6.1 Allocation rules
1. Determine eligible `SpotType` for `VehicleType`.
2. Prefer lowest floor level (or nearest gate) and then lowest `distance_score`.
3. Only choose spots with `status = AVAILABLE`.

### 6.2 Data structures
**Baseline (DB-only, simpler):**
- Query `parking_spot` with `WHERE spot_type=? AND status='AVAILABLE'` and order by `floor.level asc` then `spot_number asc`.

**Optimized (DB + Redis):**
- Redis `ZSET` per `(lotId, spotType)` containing `spotId` with score = distance.
- On allocation: pop candidate(s) and confirm in DB with a conditional update.

### 6.3 Allocation flow (transaction-safe)
Pseudo-steps (DB-first, recommended for correctness):
1. Begin transaction.
2. Validate vehicle: create-or-get by `license_plate`.
3. Ensure no active session exists (unique partial index makes this safe).
4. Select one available spot using row lock:
   - Postgres example:
     - `SELECT id FROM parking_spot WHERE spot_type = $1 AND status='AVAILABLE'
        ORDER BY ...
        FOR UPDATE SKIP LOCKED
        LIMIT 1;`
5. If none found → return `409 Full`.
6. Update chosen spot: `status = OCCUPIED` (or `RESERVED` then `OCCUPIED`) and `updated_at`.
7. Insert `parking_session` with `status=ACTIVE`, `entry_time=now()`, `spot_id=...`, `rate_plan_id=activePlan()`.
8. Commit.

Complexity:
- With good indexes, selection is ~O(log N) for index scan + constant row lock.

### 6.4 Why `SKIP LOCKED`
- Multiple entry gates can allocate concurrently without deadlocks.
- Avoids two transactions picking the same spot.

---

## 7) Fee Calculation Logic

### 7.1 Inputs
- `vehicle_type`
- `entry_time`, `exit_time`
- `rate_rule` for `(rate_plan, vehicle_type)`

### 7.2 Computation
Let
- $\Delta = \max(0, \text{minutes}(exit - entry) - graceMinutes)$
- `unit = billing_unit_minutes`
- `billingUnits = ceil(Δ / unit)`
- `fee = base_fee + billingUnits * per_unit_fee`
- If `daily_cap` exists: `fee = min(fee, daily_cap)` for each 24h bucket (or apply global cap; choose one policy).

Recommended policy (simple):
- Apply grace once.
- Apply a global `daily_cap` scaled by number of started 24h periods:
  - `days = ceil(durationMinutes / 1440)`
  - `cap = days * daily_cap`
  - `fee = min(fee, cap)`

### 7.3 Determinism & auditability
- Store the selected `rate_plan_id` on session at entry.
- On exit, store `fee_amount_cents` and an optional JSON `fee_breakdown` (if desired).

---

## 8) Concurrency, Consistency, and Idempotency

### 8.1 Concurrency patterns
**Entry allocation:**
- Use DB transaction + `SELECT ... FOR UPDATE SKIP LOCKED`.
- Update spot status inside the same transaction.
- Unique partial index prevents double-active sessions per vehicle.

**Exit processing:**
- Lock the active session row: `SELECT ... FOR UPDATE`.
- Compute fee and set `exit_time`, `status=CLOSED`.
- Release spot with a conditional update: set spot `AVAILABLE` only if currently `OCCUPIED`.

### 8.2 Idempotency
- Require `idempotencyKey` from gates for `entry`.
- Enforce unique `(parking_lot_id, idempotency_key)` to safely retry.

### 8.3 Avoiding race conditions
- Spot state transitions are guarded by conditional updates:
  - `UPDATE parking_spot SET status='OCCUPIED' WHERE id=? AND status='AVAILABLE'`
- Session close guarded similarly:
  - `UPDATE parking_session SET status='CLOSED' ... WHERE id=? AND status='ACTIVE'`

### 8.4 Real-time availability updates
- Source of truth: `parking_spot.status`.
- Optional: maintain counters in Redis:
  - `INCR/DECR` on events inside an outbox pattern (see below).

### 8.5 Outbox (recommended if you add cache/events)
- Write changes and an `outbox_event` record in the same DB transaction.
- A background worker publishes events and updates caches.

---

## 9) Core Sequences

### 9.1 Entry sequence
1. Gate calls `POST /entry`.
2. Service starts transaction.
3. Validate/create vehicle.
4. Lock & pick spot (`SKIP LOCKED`).
5. Mark spot occupied.
6. Create active session.
7. Commit and return assigned spot.

### 9.2 Exit sequence
1. Gate calls `POST /exit`.
2. Service starts transaction.
3. Lock active session.
4. Compute fee.
5. Record payment status / fee.
6. Mark session closed; free spot.
7. Commit and return receipt.

---

## 10) Suggested Class Design (LLD)

### Key interfaces
- `SpotAllocationStrategy`
  - `allocate(lotId, vehicleType, preferredGateId) -> ParkingSpot`
- `FeeCalculator`
  - `calculate(vehicleType, entryTime, exitTime, ratePlanId) -> FeeQuote`

### Services
- `EntryService`
  - `checkIn(lotId, licensePlate, vehicleType, gateId, idempotencyKey)`
- `ExitService`
  - `checkOut(lotId, licensePlate, gateId, paymentInfo)`
- `AvailabilityService`
  - `getAvailability(lotId)`

### Repositories
- `SpotRepository` (select + lock + update)
- `SessionRepository`
- `VehicleRepository`
- `RatePlanRepository`

---

## 11) Extensibility Notes
- Add EV-charging spots by introducing `SpotFeature` and matching rules.
- Add reservations by using `RESERVED` state and expiration.
- Add dynamic pricing by versioning `rate_plan` and selecting at entry.

