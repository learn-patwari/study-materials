# System Design

Consolidated system design documents from across learn-patwari repositories.

## Contents

### HLD + DB Design
| Project | Source Repo | Documents |
|---|---|---|
| BookMyShow | `learn-patwari/system-design-book-my-show` | [HLD](./BookMyShow/BookMyShow-System-Design.md) · [DB Schema](./BookMyShow/BookMyShow-DB-Design.md) |

### Low-Level Design (LLD)
| Project | Source Repo | Documents |
|---|---|---|
| Smart Parking Lot | `learn-patwari/parking-lot-lld` | [LLD](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md) |

---

## Index by Topic

### Concurrency & Locking
- [Parking Lot: SKIP LOCKED spot allocation](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md#64-why-skip-locked)
- [BookMyShow: Redis NX seat reservation](./BookMyShow/BookMyShow-System-Design.md#51-seat-reservation--preventing-double-booking)

### Database Schema Design
- [BookMyShow: Full relational schema + 20 SQL queries](./BookMyShow/BookMyShow-DB-Design.md)
- [Parking Lot: PostgreSQL schema with indexes](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md#4-data-model-relational-schema)

### API Design
- [Parking Lot: Gate-facing REST APIs](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md#5-public-apis-gate-facing)

### Idempotency
- [Parking Lot: Idempotency key on entry](./ParkingLot-LLD/Smart-Parking-Lot-LLD.md#82-idempotency)
- [BookMyShow: Payment idempotent_key](./BookMyShow/BookMyShow-System-Design.md#53-payment-idempotency)
