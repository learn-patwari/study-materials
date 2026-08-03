# AKP Industry — S3 Folder Hierarchy API

> Source: learn-patwari/akp-industry (s3-redis-k8s)

## Overview

A **Spring Boot microservice** that organizes a flat AWS S3 folder structure (like `YYYYMMDD`) into a virtual year → month → day hierarchy. Designed to handle millions of S3 folders efficiently using Redis caching with a self-managed daily rebuild cycle.

---

## Key Features

- **Dynamic hierarchy**: Splits flat folders like `20240504` into `2024` → `05` → `04`
- **Fast**: Redis cache handles millions of records efficiently
- **Self-managed cache**: Clears daily at 3 AM KST, rebuilds automatically at 5 AM KST
- **Cloud-native**: Kubernetes-ready with ConfigMap, Secret, Deployment, and Service YAMLs

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Spring Boot 2.x (Java 8 compatible) |
| Cache | Redis |
| Storage | AWS S3 (via AWS SDK for Java) |
| Infra | Kubernetes (Helm + Bitnami Redis chart) |
| Utilities | Lombok |

---

## API

### `GET /folders`
Returns the year-level hierarchy root.

### `GET /folders/{year}`
Returns months under the given year.

### `GET /folders/{year}/{month}`
Returns days under the given month.

### `GET /folders/{year}/{month}/{day}`
Returns content (subfolders + files) for the given day.

**Response format**: `List<FolderDTO>`
```json
[
  {
    "name": "20240504",
    "subfolderCount": 3,
    "fileCount": 42
  }
]
```

---

## Caching Strategy

1. On first request: fetch from S3 → parse flat folder names → build hierarchy → cache in Redis
2. On subsequent requests: serve from Redis (sub-millisecond reads)
3. At 3 AM KST: scheduled job clears the Redis cache
4. At 5 AM KST: warm-up job rebuilds cache from S3 proactively

This avoids cold-start latency during business hours for Korean Standard Time operations.

---

## Kubernetes Deployment

```bash
# Install Redis (no auth for dev)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install my-redis bitnami/redis --namespace test_ns --set auth.enabled=false

# Apply manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

Includes:
- `ConfigMap` for S3 bucket name, region, cache TTL
- `Secret` for AWS credentials and Redis connection
- `Deployment` with multiple pods for HA
- `Service` for load-balanced access

---

## Design Considerations

- **Why Redis over DB**: S3 folder counts can reach millions; Redis sorted sets handle ordered traversal in O(log N)
- **Flat → hierarchy parsing**: `20240504` → split at positions 0-3, 4-5, 6-7 → year/month/day
- **Cache coherence**: Nightly rebuild (not real-time) is acceptable because S3 folder structure for historical data is immutable; only the current day's folder grows
- **Java 8 compatibility**: Chosen for compatibility with enterprise environments still on JDK 8
