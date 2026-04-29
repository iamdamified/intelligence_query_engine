# Insighta Labs+ Backend

**Backend Engineering Track — Stage 3: Secure Access & Multi‑Interface Integration**

---

## Overview

This repository contains the **backend implementation for Stage 3 of Insighta Labs+**.  
It extends the Stage 2 Profile Intelligence System into a **secure, production‑ready platform** that supports:

- Authentication via **GitHub OAuth (PKCE)**
- **Role‑Based Access Control (RBAC)**
- Secure session and token lifecycle management
- Multi‑interface consumption (API, CLI, Web)
- Rate limiting, logging, and API hardening

All functionality from **Stage 2** (filtering, sorting, pagination, and natural language search) is preserved with **no regressions**.

---

## Stage 3 Objectives (Backend Scope)

The backend is responsible for:

- Enforcing **authentication on all protected endpoints**
- Managing **users, roles, and permissions**
- Acting as the **single source of truth** for:
  - API consumers
  - CLI tool
  - Web portal
- Securing access with centralized guards and middleware

---

## Architecture Summary

```
Client (CLI / Web)
      ↓
Authentication Layer (OAuth + Tokens)
      ↓
Authorization (RBAC Guards)
      ↓
API Layer (/api/*)
      ↓
Database (Profiles + Users)
```

Key architectural principles:

- **Centralized security enforcement** (no scattered checks)
- **Stateless access tokens** + **rotating refresh tokens**
- Clear separation between authentication, authorization, and business logic

---

## Authentication System

### OAuth Provider

- **GitHub OAuth** with **PKCE**
- Supports:
  - Browser‑based authentication (Web portal)
  - CLI‑initiated authentication with callback capture

### Auth Endpoints

| Method | Endpoint | Description |
|------|--------|-------------|
| GET | `/auth/github` | Redirects user to GitHub OAuth |
| GET | `/auth/github/callback` | Handles OAuth callback, issues tokens |
| POST | `/auth/refresh` | Rotates access & refresh tokens |
| POST | `/auth/logout` | Invalidates refresh token |

### Token Policy

| Token | Expiry |
|-----|-------|
| Access Token | 3 minutes |
| Refresh Token | 5 minutes |

- Refresh tokens are **single‑use**
- Old refresh tokens are **invalidated immediately**
- New access + refresh tokens are issued on every refresh

---

## User System

A dedicated **users table** is introduced.

### User Model

| Field | Description |
|----|----|
| `id` | UUID v7 primary key |
| `github_id` | Unique GitHub identifier |
| `username` | GitHub username |
| `email` | GitHub email (if available) |
| `avatar_url` | GitHub avatar URL |
| `role` | `admin` or `analyst` |
| `is_active` | Soft‑disable flag |
| `last_login_at` | Timestamp |
| `created_at` | Timestamp |

### Default Role

- New users default to: **`analyst`**

---

## Role‑Based Access Control (RBAC)

RBAC is enforced using **dependency‑based guards**.

### Roles

| Role | Permissions |
|----|------------|
| `admin` | Full access (create, delete, read, export) |
| `analyst` | Read‑only access |

### Enforcement Strategy

- All `/api/*` endpoints require authentication
- Role checks are applied **centrally** using dependencies
- Disabled users (`is_active = false`) receive **403 Forbidden**

This prevents authorization logic from being duplicated across endpoints.

---

## API Security Enhancements

### API Versioning (Required)

All profile endpoints require the header:

```
X-API-Version: 1
```

Requests without this header are rejected:

```json
{
  "status": "error",
  "message": "API version header required"
}
```

---

## Profile APIs (Stage 3 Compliance)

### Create Profile (Admin Only)

- Endpoint: `POST /api/profiles`
- Calls external enrichment APIs
- Transforms and stores profile data
- RBAC enforced (`admin` only)

### Read & Search Profiles

- Filtering, sorting, pagination preserved from Stage 2
- Natural language querying supported
- Available to `admin` and `analyst`

### Pagination Response Format

All paginated responses include:

```json
{
  "status": "success",
  "page": 1,
  "limit": 10,
  "total": 2026,
  "total_pages": 203,
  "links": {
    "self": "/api/profiles?page=1&limit=10",
    "next": "/api/profiles?page=2&limit=10",
    "prev": null
  },
  "data": []
}
```

---

## CSV Export

- Endpoint: `GET /api/profiles/export?format=csv`
- Applies same filters and sorting as profile listing
- Returns a downloadable CSV file

### CSV Columns (Exact Order)

```
id,
name,
gender,
gender_probability,
age,
age_group,
country_id,
country_name,
country_probability,
created_at
```

---

## Rate Limiting

| Scope | Limit |
|----|----|
| `/auth/*` | 10 requests / minute |
| All other endpoints | 60 requests / minute per user |

- Exceeded limits return **429 Too Many Requests**
- Implemented at the backend layer

---

## Logging

Every request logs:

- HTTP method
- Endpoint path
- Response status code
- Response time

This provides observability and auditability for production usage.

---

## Environment Configuration

- All secrets and URLs are managed via **environment variables**
- `.env` is used for local development
- No credentials or API URLs are hardcoded

---

## Multi‑Interface Consistency

The backend serves as the **single source of truth** for:

- API consumers
- CLI tool
- Web portal

All interfaces:

- Use the same authentication system
- Share the same authorization rules
- Consume the same API contracts

---

## Engineering Standards

- Conventional commits (scoped)
- Feature branches and PRs before merge
- CI checks for linting and builds
- Clean separation of concerns

---

## Scope Clarification

This README **documents backend responsibilities only**.

- CLI usage and UX are documented in the **CLI repository**
- Web portal UI details are documented in the **Web repository**

---

## Status

Stage 3 backend requirements fully implemented

The system is secure, role‑aware, rate‑limited, and ready for multi‑interface consumption.

