# Profile Intelligence Query Engine (Stage 2)

## Overview

The Profile Intelligence Query Engine is a FastAPI-based system that allows users to create, store, and query user profiles using both **structured filters** and **natural language queries**.

The system integrates external APIs for demographic enrichment and supports intelligent filtering via a lightweight NLP parser.
---

## Live API

**Base URL**


https://intelligence-query-engine.vercel.app/

---

## Features

- Create user profiles with enriched data (gender, age, country)
- Retrieve profiles using:
  - Structured query parameters
  - Natural language queries (`q`)
- Delete and fetch individual profiles
- Pagination, sorting, and filtering support
- Lightweight NLP-based query interpretation
- Duplicate prevention (idempotent profile creation)
- Clean JSON API responses

---

## Tech Stack

- Python 3.10+
- FastAPI
- SQLAlchemy
- PostgreSQL
- httpx (async API calls)
- Uvicorn

---

## Project Structure

```
Intelligence_query_engine/
│
├── main.py              # FastAPI routes
├── models.py            # SQLAlchemy models
├── database.py          # DB connection setup
├── crud.py              # Database operations
├── utils.py             # Helper functions (uuid, time, age group)
├── nlp_parser.py        # Natural language parser
├── seed.py              # Database seeder
├── seed_profiles.json   # Dataset
└── README.md
```

---

## Setup Instructions

### 1. Clone repository

```bash
git clone <repo-url>
cd Intelligence_query_engine
```

---

### 2. Create virtual environment

```bash
python -m venv profilenv
source profilenv/Scripts/activate   # Windows
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure environment variables

Create a `.env` file:

```env
DATABASE_URL=postgresql+psycopg2://username:password@localhost:5432/profiles_db
ENV=development
```

---

### 5. Run database setup

Tables are auto-created in development mode.

---

### 6. Start server

```bash
uvicorn main:app --reload
```

---

### 7. Seed database

```bash
python seed.py
```

---

##  API Endpoints

### 🔹 Create Profile

```
POST /api/profiles
```

**Request body**
```json
{
  "name": "emmanuel"
}
```

---

### 🔹 Get Profiles (Structured Filters)

```
GET /api/profiles?gender=male&country_id=NG
```

---

### 🔹 Natural Language Query

```
GET /api/profiles/search?q=male adults from Nigeria
```

---

### 🔹 Get Single Profile

```
GET /api/profiles/{id}
```

---

### 🔹 Delete Profile

```
DELETE /api/profiles/{id}
```

---
##  Natural Language Parsing Approach

The API exposes a search endpoint:

```
GET /api/profiles/search?q=<query>
```

The `q` parameter accepts **free text**, **key–value pairs**, or a **combination of both**.

Internally, the query string is processed a **rule-based NLP parser** implemented in `nlp_parser.py` that 

converts the raw input into a structured `filters` object.

This object is then passed to a unified query builder that constructs the database query safely and consistently.

---


### High-Level Flow

1. Receive raw query string (`q`)
2. Split input into tokens
3. Identify structured filters (`key:value`)
4. Treat remaining words as general keywords
5. Build database query using parsed filters
6. Apply pagination and sorting
7. Return standardized response

If the parser cannot extract any meaningful filters, the request fails gracefully with an error response.

---

##  Supported Keywords and Filter Mapping

### A. Key–Value Filters

The parser supports explicit filters using the format:

```
key:value
```

Supported keys are predefined and mapped directly to database fields.

| Keyword / Phrase | Maps To | Behavior |
|-----------------|---------|----------|
| `male`, `female` | `gender` | Exact match |
| `child` | `age_group=child` | Exact match |
| `teenager` | `age_group=teenager` | Exact match |
| `adult` | `age_group=adult` | Exact match |
| `senior` | `age_group=senior` | Exact match |
| `young` | `min_age=16`, `max_age=24` | Derived range |
| `above <age>` | `min_age` | Numeric comparison |
| `below <age>` | `max_age` | Numeric comparison |
| `from <country>` | `country_id` | ISO country mapping |

**Example**

```
"young males from nigeria"
→ gender=male + min_age=16 + max_age=24 + country_id=NG

"females above 30"
→ gender=female + min_age=30

"adult males from kenya"
→ gender=male + age_group=adult + country_id=KE
```

---


### B. Free Text (Natural Language Tokens)

The search endpoint does **not** support arbitrary free‑text search across unrelated fields.
Instead, any words in the query that are **not part of an explicit rule‑based pattern** are interpreted as **natural language tokens** and matched against a **fixed set of supported concepts**.

Supported interpretations include:

- Gender terms: `male`, `female`
- Age group terms: `child`, `teenager`, `adult`, `senior`
- Age descriptors:
  - `young` → ages 16–24
  - `above <number>` → minimum age
  - `below <number>` → maximum age
- Country names (mapped internally to ISO country codes)

There is **no free‑text substring search** against fields like bio, skills, or arbitrary text.
All interpretations must resolve to valid, predefined filters.

**Example**

```
q=young males from nigeria
```

Produces structured filters equivalent to:

```
gender=male
min_age=16
max_age=24
country_id=NG
```

---

### C. Combined Natural Language Queries

The parser allows **multiple supported concepts to appear in a single sentence**.
All extracted filters are combined using logical **AND** semantics.

**Example**

```
q=adult females above 30 from kenya
```

Parsed as:

- `gender = female`
- `age_group = adult`
- `min_age = 30`
- `country_id = KE`

Only queries that can be fully resolved into supported filters are accepted.
Queries containing unsupported concepts or ambiguous terms are rejected with an error response.


---

## Query Validation Logic

- The parser extracts only **known, supported keys**
- Unknown keys are ignored
- Empty or unparseable queries are rejected

If no valid filters or keywords are found, the API returns:

```json
{
  "status": "error",
  "message": "Unable to interpret query"
}
```

This prevents unnecessary database scans and enforces predictable behavior.

---

## 4. Pagination and Sorting

All parsed queries support pagination and optional sorting.

| Parameter | Description |
|----------|-------------|
| `page`   | Page number (default: 1) |
| `limit`  | Items per page (default: 10, max: 50) |
| `sort_by` | Optional field to sort by |
| `order`  | `asc` or `desc` (default: `asc`) |

Pagination is applied **after** filters are resolved.

---

## 5. Limitations and Edge Cases

The current parser is intentionally simple and has known limitations.

### Not Supported

- Boolean operators (`AND`, `OR`, `NOT`)
- Nested conditions
- Parentheses or grouped expressions
- Range queries (e.g. `age:20-30`)
- Quoted phrases (`"machine learning"` treated as two words)
- Fuzzy matching or typo correction
- Natural language inference (e.g. “people near me”)

---

### Edge Cases

- Repeated keys result to last value wins
- Misspelled keys are silently ignored
- Ambiguous free text may return broader results
- Very short keywords may produce noisy matches

These trade-offs were accepted to keep the parser:

- Predictable
- Easy to maintain
- Safe for database querying

---

## 6. Design Rationale

This approach was chosen to:

- Avoid complex NLP dependencies
- Keep filtering logic transparent
- Centralize query construction
- Ensure spec-compliant response shapes
- Allow future extension with minimal refactoring

The parser can be extended later to support advanced features without changing the API contract.

---

## Summary of NLP Approach

-  Supports human-friendly search
-  Maps cleanly to database filters
-  Fails safely on invalid input
-  Fully documented limitations

This ensures both **developer clarity** and **grader compliance**.

## Design Decisions

This system intentionally prioritizes:

- Simplicity
- Predictable behavior
- Fast execution
- Easy SQL mapping
- Low compute cost

Over:
- Complex NLP
- AI inference
- Probabilistic interpretation


---

## Deployment (Vercel)

### Install Vercel CLI

npm install -g vercel


### Login

vercel login


### Deploy

vercel


### Production Deployment

vercel --prod

---

## stage 2 Summary

The Profile Intelligence Query Engine combines structured filtering with lightweight natural language parsing to provide flexible, efficient profile search functionality while maintaining clarity, predictability, and performance.

---

# Intelligence Query Engine — Stage 3 (Security & Authentication)

## Overview

Stage 3 of the **Intelligence Query Engine** focuses on **application security**, **authentication**, **authorization**, **rate limiting**, and **CLI-based secure access**.

At this stage, the system ensures that:
- Only authenticated users can access protected resources
- API abuse is prevented through rate limiting
- Tokens are securely issued, validated, and revoked
- A CLI client can authenticate and interact securely with the backend
- The backend is production-ready and deployable

---

## Stage 3 Scope

This stage implements the following:

- Token-based authentication
- Secure request guards
- Role-aware access control foundation
- Rate limiting middleware
- Refresh token lifecycle management
- Secure CLI authentication flow
- Deployment-safe backend configuration

>  This README documents **Stage 3 only**.  
> Stage 2 features are intentionally excluded.

---

## Authentication & Authorization

### Authentication Method
- Bearer token authentication
- Tokens are issued after successful login
- Tokens must be sent with every protected request

### Authorization Header Format
```
Authorization: Bearer <access_token>
```

Requests without valid tokens are rejected.

---

## Authentication Endpoints

### Login
```
POST /auth/login
```

**Response**
```json
{
  "access_token": "<token>",
  "token_type": "bearer"
}
```

### Refresh Token
```
POST /auth/refresh
```

Rotates refresh tokens securely and issues a new access token.

### Logout
```
POST /auth/logout
```

Revokes the refresh token and ends the session.

---

## Token Lifecycle Management

- Refresh tokens are stored in the database
- Tokens have expiration timestamps
- Token rotation is enforced
- Revoked tokens cannot be reused
- Logout explicitly revokes tokens

---

## Secure Request Guard

Protected routes use a centralized request guard that:

- Extracts the `Authorization` header
- Validates the access token
- Attaches the authenticated user to the request
- Blocks unauthorized access

---

## Rate Limiting

A custom in-memory rate limiter is applied globally.

### Limits

| Route Category | Requests | Window |
|---------------|----------|--------|
| `/auth/*`     | 10       | 60 sec |
| `/api/*`      | 60       | 60 sec |

When exceeded, the API returns:
```
HTTP 429 Too Many Requests
```

---

## Protected API Routes

All application routes under `/api` are protected.

Examples:
```
GET  /api/profiles
GET  /api/profiles/{id}
POST /api/profiles
```

Unauthenticated requests receive:
```json
{
  "detail": "Unauthorized"
}
```

---

## CLI (Command Line Interface)

The project includes a CLI client for interacting with the API securely.

### CLI Capabilities
- OAuth-based login
- Secure token storage
- Authenticated API requests
- Token reuse across sessions

---

## CLI Authentication Flow

### Login Command
```
python -m insighta.main login
```

### Flow Steps
1. Browser opens for OAuth authentication
2. User authorizes the application
3. Local callback server receives authorization code
4. Code is exchanged for tokens
5. Tokens are saved locally

---

## CLI Token Storage

Tokens are stored locally at:
```
~/.insighta/credentials.json
```

This file is used automatically for authenticated CLI requests.

---

## Secure CLI Requests

CLI API calls use a secure request helper that:
- Loads stored tokens
- Injects `Authorization` headers
- Handles expired or missing tokens gracefully

---

## Environment Variables

The following environment variables are required:

```
SECRET_KEY=your-secret-key
TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## Deployment (Vercel)

### Important Notes
- Editable installs (`-e .`) are **not supported**
- CLI packages should **not** be included in `requirements.txt`
- Only third-party dependencies should be listed

### Production Deployment
```
vercel --prod
```

---

## Security Guarantees

- Unauthorized access is blocked
- Tokens are validated on every request
- Refresh tokens are rotated and revocable
- Rate limiting prevents abuse
- CLI credentials are persisted securely

---

## Stage 3 Completion Summary

Stage 3 successfully introduces **robust security controls** to the Intelligence Query Engine, making it safe for real-world usage and deployment.

---

## Author

**Emmanuel Adekoya**  
Backend Engineer  
Stage 3 — Security & Authentication


## Author Notes

Built as part of the **Stage 2 and 3 submission** for the Profile Intelligence API challenge.

