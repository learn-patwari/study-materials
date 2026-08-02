# Database schema design of the book my show application

## 1. **Schema's**
### a. List of entities

- **User**
    
    | **user_id** | **name** | **role** | **date_of_birth** |
    |-------------|----------|----------|-------------------|
    | 1           | Akshay   | Admin    | 24-05-1995        |
    | 2           | John     | User     | 01-12-1991        |
    If more business logic with role relies on create separate table for roles as **Role**.


- **Movie**
  
   | **movie_id** | **name** | **genre** | **rating** | **min_age** |
   |--------------|----------|-----------|------------|-------------|
   | 1            | Avatar   | Sci-Fi    | 9.7        | 12          |
   | 2            | KGF      | Violence  | 9.5        | 18          |

- **Theatre**

    | **theatre_id** | **theatre_name** | **capacity** | **screens** | **city** |
    |---------|--------------|------|----|----------|
    | 1 | PVR | 70 | 4  | Delhi    |
    | 2 | Mahalakshmi | 340 | 1  | Bengaluru |

- **Show**

  | **show_id** | **movie_id** | **theatre_id** | **time_slot** |
  |-------------|--------------|----------------|---------------|
   | 1           | 1            | 1              | 10AM          |
  | 2           | 1            | 1              | 12PM          |
  | 4           | 2            | 1              | 09PM          |
  | 5           | 1            | 2              | 09PM          |
  | 6           | 1            | 2              | 10AM          |
  | 6           | 2            | 1              | 04PM          |

  - **Seat**

      | **seat_id** | **row** | **row_id** | **is_active** | **category** | **base_price_in_rupees** | 
      |-------------|---------|------------|---------------|--------------|--------------------------|
      | 1           | A       | 1          | true          | LUX          | 600                      |
      | 2           | A       | 12         | true          | LUX          | 750                      |
      | 3           | BB      | 32         | true          | 4DX          | 500                      |
      | 4           | C       | 45         | true          | 2D           | 350                      |
      | 5           | DD      | 12         | true          | 2D           | 350                      |
- **Show_Seat**

    | **id** | **show_id** | **price_in_rs** |
    |--------|------------|-----------------|
     | 1      | 1          | 650             |
     | 2      | 1          | 950             |
 **Booking**

  | **booking_id** | **booking_ref** | **show_id** | **user_id** | **status** | **payment_id** | **total_amount** |
   |----------------|-----------------|-------------|-------------|------------|----------------|------------------|
   | 1              | JP76TUV         | 2           | 1           | Booked     | 1              | 1200             |
   | 2              | OH78IOP         | 1           | 2           | Pending    | 2              | 900              |
    
**Booking_Item**

   | **booking_item_id** | **booking_id** | **show_seat_id** | **price_in_rs** |
   |---------------------|----------------|------------------|-----------------|
    | 1                   | 2              | 1                | 300             |
    | 2                   | 2              | 2                | 700             |

**payment**

   | **payment_id** | **booking_id** | **provider** | **provider_txn_id** | **idempotent_key** | **amount** | **status** |
   |----------------|----------------|--------------|---------------------|--------------------|------------|------------|
   | 1              | 2              | Phonepay     | yuhgcx67nsdlc       | sdkjcjbskz89u      | 900        | Success    |
   | 2              | 1              | RAZORPAY     | lbjdvkjb787bc       | nsdnkjds689bh      | 1200       | Pending    |

### 2 Queries

The following SQL queries are based on the schema above. They use the same table and column names from this document.

#### 2.1 List all movies

```sql
SELECT movie_id, name, genre, rating, min_age
FROM Movie;
```

#### 2.2 List all theatres

```sql
SELECT theatre_id, theatre_name, capacity, screens, city
FROM Theatre;
```

#### 2.3 List all shows with movie and theatre details

```sql
SELECT
    s.show_id,
    m.name AS movie_name,
    t.theatre_name,
    t.city,
    s.time_slot
FROM Show s
JOIN Movie m ON s.movie_id = m.movie_id
JOIN Theatre t ON s.theatre_id = t.theatre_id;
```

#### 2.4 List all shows for a given theatre

```sql
SELECT
    s.show_id,
    m.name AS movie_name,
    s.time_slot
FROM Show s
JOIN Movie m ON s.movie_id = m.movie_id
WHERE s.theatre_id = 1;
```

#### 2.5 List all shows for a given movie

```sql
SELECT
    s.show_id,
    t.theatre_name,
    t.city,
    s.time_slot
FROM Show s
JOIN Theatre t ON s.theatre_id = t.theatre_id
WHERE s.movie_id = 1;
```

#### 2.6 List all shows in a city

```sql
SELECT
    s.show_id,
    m.name AS movie_name,
    t.theatre_name,
    s.time_slot
FROM Show s
JOIN Movie m ON s.movie_id = m.movie_id
JOIN Theatre t ON s.theatre_id = t.theatre_id
WHERE t.city = 'Delhi';
```

#### 2.7 List all active seats

```sql
SELECT seat_id, row, row_id, category, base_price_in_rupees
FROM Seat
WHERE is_active = true;
```

#### 2.8 List seats mapped to a show

```sql
SELECT
    ss.id,
    ss.show_id,
    ss.price_in_rs
FROM Show_Seat ss
WHERE ss.show_id = 1;
```

#### 2.9 List bookings of a user

```sql
SELECT
    b.booking_id,
    b.booking_ref,
    b.show_id,
    b.status,
    b.payment_id,
    b.total_amount
FROM Booking b
WHERE b.user_id = 1;
```

#### 2.10 List booking details with movie and theatre

```sql
SELECT
    b.booking_ref,
    u.name AS user_name,
    m.name AS movie_name,
    t.theatre_name,
    b.status,
    b.total_amount
FROM Booking b
JOIN User u ON b.user_id = u.user_id
JOIN Show s ON b.show_id = s.show_id
JOIN Movie m ON s.movie_id = m.movie_id
JOIN Theatre t ON s.theatre_id = t.theatre_id
WHERE b.booking_id = 1;
```

#### 2.11 List booking items for a booking

```sql
SELECT
    bi.booking_item_id,
    bi.booking_id,
    bi.show_seat_id,
    bi.price_in_rs
FROM Booking_Item bi
WHERE bi.booking_id = 2;
```

#### 2.12 List payment status for bookings

```sql
SELECT
    p.payment_id,
    p.booking_id,
    p.provider,
    p.provider_txn_id,
    p.idempotent_key,
    p.amount,
    p.status
FROM payment p;
```

#### 2.13 List successful payments only

```sql
SELECT
    p.payment_id,
    p.booking_id,
    p.provider,
    p.amount
FROM payment p
WHERE p.status = 'Success';
```

#### 2.14 List pending bookings

```sql
SELECT
    booking_id,
    booking_ref,
    user_id,
    show_id,
    payment_id,
    total_amount
FROM Booking
WHERE status = 'Pending';
```

#### 2.15 Count shows per theatre

```sql
SELECT
    t.theatre_id,
    t.theatre_name,
    COUNT(s.show_id) AS total_shows
FROM Theatre t
LEFT JOIN Show s ON t.theatre_id = s.theatre_id
GROUP BY t.theatre_id, t.theatre_name;
```

#### 2.16 Count bookings per user

```sql
SELECT
    u.user_id,
    u.name,
    COUNT(b.booking_id) AS total_bookings
FROM User u
LEFT JOIN Booking b ON u.user_id = b.user_id
GROUP BY u.user_id, u.name;
```

#### 2.17 Total revenue by theatre

```sql
SELECT
    t.theatre_name,
    SUM(b.total_amount) AS total_revenue
FROM Booking b
JOIN Show s ON b.show_id = s.show_id
JOIN Theatre t ON s.theatre_id = t.theatre_id
WHERE b.status = 'Booked'
GROUP BY t.theatre_name;
```

#### 2.18 Revenue by movie

```sql
SELECT
    m.name AS movie_name,
    SUM(b.total_amount) AS total_revenue
FROM Booking b
JOIN Show s ON b.show_id = s.show_id
JOIN Movie m ON s.movie_id = m.movie_id
WHERE b.status = 'Booked'
GROUP BY m.name;
```

#### 2.19 Find all inactive seats

```sql
SELECT *
FROM Seat
WHERE is_active = false;
```

#### 2.20 Detect duplicate show IDs

```sql
SELECT show_id, COUNT(*) AS cnt
FROM Show
GROUP BY show_id
HAVING COUNT(*) > 1;
```
