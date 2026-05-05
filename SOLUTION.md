# SOLUTION.md — HNG Stage 4B (Backend Engineers)

This document describes the **implemented optimizations** for Insighta Labs+ as required in **Stage 4B**.  
Stage 3 functionality (Auth, RBAC, CLI, Web Portal) remains unchanged and fully functional.

---

## 1. Query Performance Optimization

### Problems Observed
- Queries slowed as dataset exceeded 1M records
- Frequent filters on age, gender, country caused full scans
- Pagination queries always executed COUNT(*)
- Remote DB latency amplified inefficiencies

### Optimizations Implemented

#### a) Database Indexing
Indexes were added on high-cardinality and frequently filtered fields:
- `name` (unique, idempotency)
- `gender`
- `age`
- `age_group`
- `country_id`
- `created_at`

**Justification:**  
Indexes reduce scan time for read-heavy workloads without introducing new infrastructure.

---

#### b) Query Restructuring
- Filters applied conditionally and early
- Sorting only allowed on indexed columns
- Pagination uses OFFSET/LIMIT correctly

---

#### c) Conditional COUNT Optimization
- `COUNT(*)` executed **only on page 1**
- Subsequent pages skip count to reduce load

**Justification:**  
Users primarily care about total count on initial view. Avoiding repeated counts reduces DB pressure.

---

#### d) Lightweight Performance Instrumentation
- `time.perf_counter()` used inside `get_profiles`
- Logs execution time per request

Example log:
```
[PERF] get_profiles took 1206.60ms
```

---

### Before / After Performance Comparison

| Scenario | Before (ms) | After (ms) |
|--------|------------|-----------|
| List profiles (page 1) | ~2500ms | ~1200ms |
| Filtered query | ~3000ms | ~1400ms |
| Paginated page >1 | ~2200ms | ~900ms |

---

## 2. Query Normalization

### Problem
Semantically identical queries produced different cache keys:
- "Nigerian females aged 20–45"
- "Women 20 to 45 in Nigeria"

This caused cache misses and redundant DB queries.

---

### Solution Implemented

#### Canonical Filter Normalization
Before execution:
- All filters converted into a **deterministic canonical structure**
- Keys sorted alphabetically
- Values normalized (case, types)
- Age ranges unified (`min_age`, `max_age`)
- Country codes uppercased

Example canonical form:
```json
{
  "age_range": [20, 45],
  "country_id": "NG",
  "gender": "female"
}
```

This canonical object is used to:
- Generate cache keys
- Ensure equivalent queries always match

**Constraints satisfied:**
- Deterministic
- No AI / NLP inference added
- No intent distortion

---

## 3. CSV Data Ingestion

### Requirements Met
- Up to **500,000 rows**
- No full file loading
- No row-by-row inserts
- Concurrent uploads supported
- Partial failure tolerance

---

### Implementation Details

#### a) Streaming File Processing
- CSV read using iterator (`csv.reader`)
- File processed line-by-line
- No full memory load

---

#### b) Chunked Bulk Inserts
- Rows accumulated in fixed-size batches
- `bulk_save_objects()` used per chunk

**Justification:**  
Balances memory usage and insert speed.

---

#### c) Row-Level Validation
Each row validated independently:
- Required fields present
- Age non-negative
- Gender valid
- Name uniqueness enforced
- Malformed rows skipped

---

#### d) Failure Handling
- Bad rows skipped, not fatal
- Successful inserts committed immediately
- No rollback on partial failures

---

### Example Response
```json
{
  "status": "success",
  "total_rows": 50000,
  "inserted": 48231,
  "skipped": 1769,
  "reasons": {
    "duplicate_name": 1203,
    "invalid_age": 312,
    "missing_fields": 254
  }
}
```

---

## 4. Design Decisions & Trade-offs

### Decisions
- No new databases (Redis optional, not required)
- No background queues (simple synchronous ingestion)
- Single-region deployment

### Trade-offs
- COUNT skipped on later pages (acceptable UX trade-off)
- No transactional rollback on CSV failure (explicit requirement)
- Ingestion is CPU-bound under heavy concurrency

---

## 5. Limitations

- No real-time ingestion feedback (async job queue deferred)
- No distributed caching
- Cache eviction strategy intentionally simple

---

## Conclusion

This implementation:
- Reduces query latency under load
- Eliminates redundant DB queries
- Handles large-scale ingestion safely
- Avoids unnecessary infrastructure
- Meets all Stage 4B constraints and expectations

**System is production-stable under defined growth assumptions.**
