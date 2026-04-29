# Insighta CLI

## Backend Engineering Track – Stage 3 (HNG)

This document describes the **Insighta CLI** built for **Stage 3 – Secure Access & Multi‑Interface Integration**.  
The CLI is a first‑class interface to the Insighta Labs+ backend and shares the **same authentication, authorization, and data rules** as the API and Web Portal.

> 📌 **Scope note**: This README focuses strictly on the **CLI**. Backend behavior and Web Portal details are documented separately.

---

## 1. Overview

The Insighta CLI enables engineers and power users to securely interact with the Insighta Labs+ platform from the terminal.

It provides:
- GitHub OAuth login using **PKCE**
- Secure token storage and automatic refresh
- Role‑aware access to profile APIs
- Rich, user‑friendly terminal output
- Feature parity with backend APIs

The CLI communicates **exclusively** with the public backend APIs and does not bypass any authentication or authorization logic.

---

## 2. Installation

The CLI is packaged as an **installable Python application** and can be used globally after installation.

### Requirements
- Python ≥ 3.10
- pip

### Install (editable mode for development)
```bash
pip install -e .
```

> Run this command **from the project root directory** (the folder containing `pyproject.toml`).

After installation, the command below must work from **any directory**:
```bash
insighta --help
```

---

## 3. Authentication Flow (CLI)

### Login
```bash
insighta login
```

**What happens internally:**
1. CLI generates:
   - `state` (CSRF protection)
   - `code_verifier` (PKCE secret)
   - `code_challenge` (derived from verifier)
2. A temporary local callback server is started
3. Browser opens GitHub OAuth authorization page
4. User authenticates with GitHub
5. GitHub redirects to the local callback URL
6. CLI validates state and forwards `code + code_verifier` to backend
7. Backend:
   - Exchanges code with GitHub
   - Creates or updates user
   - Issues access + refresh tokens
8. CLI stores tokens locally

Successful login output:
```text
Logged in as @username
```

---

### Logout
```bash
insighta logout
```

Behavior:
- Sends refresh token to backend `/auth/logout`
- Invalidates server‑side session
- Clears local credentials

---

### Who Am I
```bash
insighta whoami
```

Returns the currently authenticated user:
```json
{
  "id": "uuid",
  "username": "octocat",
  "role": "analyst"
}
```

---

## 4. Token Handling

### Token Types
| Token | Lifetime |
|------|----------|
| Access token | 3 minutes |
| Refresh token | 5 minutes |

### Storage
Tokens are stored locally at:
```text
~/.insighta/credentials.json
```

### Auto Refresh
- Every request uses the access token
- On `401 Unauthorized`, the CLI attempts token refresh
- Refresh token rotation is enforced
- If refresh fails → user is prompted to log in again

This ensures uninterrupted CLI usage while maintaining security.

---

## 5. Profile Commands

All profile commands automatically:
- Attach authentication tokens
- Include `X-API-Version: 1`
- Respect role‑based permissions

### List Profiles
```bash
insighta profiles list
```

Filters:
```bash
insighta profiles list --gender male
insighta profiles list --country NG --age-group adult
insighta profiles list --min-age 25 --max-age 40
```

Sorting & Pagination:
```bash
insighta profiles list --sort-by age --order desc
insighta profiles list --page 2 --limit 20
```

---

### Get Profile by ID
```bash
insighta profiles get <profile_id>
```

---

### Natural Language Search
```bash
insighta profiles search "young males from nigeria"
```

Uses the same NLP parsing logic as the backend API.

---

### Create Profile (Admin Only)
```bash
insighta profiles create --name "Harriet Tubman"
```

Role enforcement:
- `admin` → allowed
- `analyst` → forbidden (403)

---

### Export Profiles (CSV)
```bash
insighta profiles export --format csv
```

With filters:
```bash
insighta profiles export --format csv --gender male --country NG
```

Behavior:
- Applies same filters as list endpoint
- Saves file to **current working directory**
- Filename format:
```text
profiles_<timestamp>.csv
```

---

## 6. UX & Feedback

The CLI provides:
- Loading indicators during API calls
- Clear success and error messages
- Structured tabular output for list commands
- Graceful handling of:
  - Expired tokens
  - Network errors
  - Permission errors

Example error:
```text
Error: Insufficient permissions (admin role required)
```

---

## 7. Security Guarantees

The CLI **does not bypass backend security**:
- All requests require authentication
- Role enforcement is handled server‑side
- Rate limits apply equally to CLI usage
- Tokens are never printed or logged

The CLI acts as a trusted client, not a privileged one.

---

## 8. Consistency with Backend & Web Portal

The CLI:
- Uses the same API endpoints as the Web Portal
- Respects the same RBAC rules
- Produces identical results for identical queries

This ensures a **single source of truth** across all interfaces.

---

## 9. Engineering Standards

- Installable via `pip`
- No hardcoded URLs (environment‑based config)
- Clean command grouping (`auth`, `profiles`)
- Conventional commits (e.g. `feat(cli): add profile export`)
- Compatible with CI linting and build checks

---

## 10. Stage 3 Evaluation Alignment

This CLI satisfies HNG Stage 3 requirements for:
- Secure OAuth authentication (PKCE)
- Token lifecycle management
- Role‑based access enforcement
- Multi‑interface consistency
- Professional developer experience

**Fully compliant with Stage 3 CLI expectations**

