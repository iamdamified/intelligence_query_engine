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
GET /api/profiles?q=male adults from Nigeria
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

## Natural Language Parsing Approach

### Overview

The system uses a lightweight **rule-based NLP parser** implemented in `nlp_parser.py`.

Its purpose is to convert natural language input into structured database filters.

---

### How the Parser Works

#### 1. Text Normalization
- Converts input to lowercase
- Trims whitespace

Example:
```
"Male Adults From Nigeria"
→ "male adults from nigeria"
```

---

#### 2. Keyword Detection

The parser scans the query string for predefined keywords and maps them to filters.

---

## Supported Keywords and Mappings

### Gender Keywords

| Keyword(s) | Applied Filter |
|----------|---------------|
| male, man, men | gender = "male" |
| female, woman, women | gender = "female" |

---

### Age Group Keywords

| Keyword | Applied Filter |
|--------|--------------|
| child | age_group = "child" |
| teen, teenager | age_group = "teen" |
| adult | age_group = "adult" |
| senior, elderly | age_group = "senior" |

---

### Country Keywords

| Keyword | Country Code |
|-------|--------------|
| nigeria | NG |
| ghana | GH |
| kenya | KE |
| united kingdom, uk | GB |
| united states, usa | US |

Only predefined countries are supported.

---

### Parser Output Example

```json
{
  "gender": "male",
  "age_group": "adult",
  "country_id": "NG"
}
```

This output is passed directly into SQLAlchemy filters.

---

## Filter Application Logic

All extracted filters are applied using **AND logic**.

---

## Limitations and Edge Cases

### 1. No Advanced NLP
- Does not use machine learning or LLMs
- Pure keyword-based matching

---

### 2. No Numeric Reasoning
Unsupported:
- “older than 30”
- “between 20 and 40”

Only predefined age groups are supported.

---

### 3. Limited Country Support
- Only countries defined in `COUNTRY_MAP` are recognized

---

### 4. No Typo Handling
- Misspellings are not detected
- Example: `nigria`

---

### 5. No Logical Operators
- Does not support OR / NOT
- No nested or compound logic

---

### 6. Stateless Queries
- Each query is independent
- No session or conversational memory

---

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

## Summary

The Profile Intelligence Query Engine combines structured filtering with lightweight natural language parsing to provide flexible, efficient profile search functionality while maintaining clarity, predictability, and performance.

---

## Author Notes

Built as part of the **Stage 2 submission** for the Profile Intelligence API challenge.


---

## Author

**Emmanuel Adekoya**  
HNG Internship — Backend Engineering Track