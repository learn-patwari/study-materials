# BookMyShow — High-Level System Design

> Source: learn-patwari/system-design-book-my-show

## Overview

BookMyShow is a movie/event ticket booking platform. This document covers the high-level architecture, component breakdown, and key design decisions.

---

## 1. Functional Requirements

- Users can search movies by city, theatre, and time slot
- Users can browse available seats and select them
- Users can book seats and complete payment
- Admins can manage movies, theatres, shows, and seats
- System sends booking confirmation

## 2. Non-Functional Requirements

- High availability (99.99% uptime)
- Low latency for seat selection (< 200ms)
- Concurrency: handle simultaneous seat bookings without double-booking
- Scale: millions of users during peak (e.g., popular movie release day)

---

## 3. Core Entities

| Entity | Description |
|---|---|
| User | Customer or Admin |
| Movie | Movie details (genre, rating, age restriction) |
| Theatre | Physical venue with screens and capacity |
| Show | A specific screening (movie + theatre + time slot) |
| Seat | Physical seat in a theatre (category: LUX, 4DX, 2D) |
| Show_Seat | Seat mapped to a specific show with dynamic pricing |
| Booking | A reservation by a user for a show |
| Booking_Item | Individual seat entries within a booking |
| Payment | Payment transaction linked to a booking |

---

## 4. High-Level Architecture

```
                        ┌─────────────────┐
  Users / Mobile App   │   API Gateway    │
         ──────────────►   (Rate Limiting,│
                        │   Auth, Routing) │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
     ┌────────▼────────┐ ┌───────▼───────┐ ┌───────▼───────┐
     │  Search Service  │ │Booking Service│ │Payment Service│
     │  (Movie/City/    │ │(Seat Lock,    │ │(Razorpay /    │
     │   Show Search)   │ │ Reserve,Book) │ │ PhonePe)      │
     └────────┬────────┘ └───────┬───────┘ └───────┬───────┘
              │                  │                  │
     ┌────────▼──────────────────▼──────────────────▼────────┐
     │                    Database Layer                       │
     │         PostgreSQL (primary) + Redis (cache)            │
     └────────────────────────────────────────────────────────┘
```

---

## 5. Key Design Decisions

### 5.1 Seat Reservation — Preventing Double Booking

Critical problem: Two users try to book seat A-1 for the same show simultaneously.

**Solution**: Optimistic locking + short-lived reservation

1. User selects seats → system creates a **temporary lock** (Redis TTL = 10 min)
2. Only one user can hold the lock per seat per show
3. On payment success → lock converted to confirmed booking in DB
4. On timeout / payment failure → lock released, seat available again

```
User A selects seat → Redis SET seat:show123:seatA1 userA EX 600 NX
                       NX = only set if Not eXists → atomically prevents double-lock
User B tries same  → NX fails → "Seat already selected by another user"
```

### 5.2 Pricing — Dynamic Show_Seat Price

Base price is on the Seat (category-based). Actual price shown to user is on Show_Seat — allows surge pricing, weekend premiums, and early-bird discounts without changing the seat entity.

### 5.3 Payment Idempotency

Every payment row has an `idempotent_key` — prevents double-charging if user retries on network failure. Gateway checks this key before processing a new charge.

### 5.4 Caching Strategy

- Movie list, theatre list → Redis with 1-hour TTL (low write frequency)
- Show availability → Redis with short TTL (high write due to bookings)
- Seat status for a show → per-show Redis bitmap (1 bit per seat)

---

## 6. Database Schema

See [BookMyShow-DB-Design.md](./BookMyShow-DB-Design.md) for the full relational schema with sample data and SQL queries.

---

## 7. Scale Considerations

| Scenario | Approach |
|---|---|
| High read traffic (browsing shows) | CDN + Redis cache for show listings |
| High write traffic (booking peak) | DB write replicas, connection pooling (PgBouncer) |
| Seat availability hotspot | Redis atomic operations (SETBIT, GETBIT) for seat bitmap |
| Payment failures | Async retry queue with exponential backoff |
| Notification on booking | Async event → Kafka → Notification Service (email/SMS) |
