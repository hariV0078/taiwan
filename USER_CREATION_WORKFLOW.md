# User Creation and Git Persistence Workflow

## Overview

Users can be created in two ways:

1. **Frontend Registration** - Via `/auth/register` endpoint (real-time)
2. **Seed Fixtures** - Via `storage/seed_users.json` (committed to git, auto-loaded on startup)

## Workflow

### Creating a New User via Frontend

The frontend can POST to the register endpoint:

```bash
POST https://sound-guiding-mammoth.ngrok-free.app/auth/register
Content-Type: application/json

{
  "email": "user@company.com",
  "name": "User Name",
  "company": "Company Ltd",
  "country": "IN",
  "role": "manufacturer"
}
```

**Responses:**
- `201 Created`: User successfully created
  ```json
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "User Name",
    "email": "user@company.com",
    "role": "manufacturer",
    "company": "Company Ltd",
    "country": "IN",
    "is_active": true
  }
  ```
- `409 Conflict`: Email already exists
- `422 Unprocessable Entity`: Invalid data (e.g., bad email, missing fields)

**Note:** This creates a user in the local SQLite database (`circularx.db`) but **does NOT persist to git** automatically.

---

## Persisting Users to Git

To make user data reproducible and version-controlled, add users to the seed fixtures:

### Step 1: Edit `storage/seed_users.json`

Add your new users to the JSON fixture file:

```json
[
  {
    "name": "Raj Manufacturing",
    "email": "manufacturer@raj-plastics.com",
    "company": "Raj Plastics Ltd",
    "country": "IN",
    "role": "manufacturer"
  },
  {
    "name": "Your New User",
    "email": "newuser@company.com",
    "company": "New Company",
    "country": "IN",
    "role": "buyer"
  }
]
```

**Valid roles:**
- `manufacturer` - Creates and manages listings
- `buyer` - Maintains buyer profile, negotiates
- `tpqc` - Performs inspections and approvals
- `admin` - System administrator

### Step 2: Commit to Git

```bash
git add storage/seed_users.json
git commit -m "Add new test users: Your New User, etc"
git push
```

### Step 3: Auto-Load on Startup

When the backend starts:
1. `main.py` calls `seed_users()` during lifespan startup
2. `seed_users()` reads `storage/seed_users.json`
3. Any user in the JSON file that doesn't exist in the database is automatically created
4. Existing users are skipped (no duplicates)

---

## Data Persistence Strategy

### Database File (`circularx.db`)

- **Location:** Project root
- **Contains:** All user data created via frontend registration or seed fixtures
- **Git Status:** In `.gitignore` (not committed)
- **Why:** SQLite .db files are binary and change frequently; not suitable for git

### Seed Fixtures (`storage/seed_users.json`)

- **Location:** `storage/seed_users.json`
- **Contains:** Reproducible test user definitions
- **Git Status:** **Committed to git**
- **Why:** Plain JSON is human-readable, reviewable, and reproducible across environments

### Workflow Summary

```
Frontend Registration
    ↓
POST /auth/register
    ↓
User saved to circularx.db
    ↓
(NOT in git automatically)
    ↓
To persist: Copy to storage/seed_users.json → git add/commit
```

---

## Example: Complete User Creation Flow

### 1. Create User via Frontend

```bash
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@acme.com",
    "name": "Jane Smith",
    "company": "ACME Recycling",
    "country": "DE",
    "role": "buyer"
  }'
```

Response:
```json
{
  "id": "abc12345-def6-7890-ghij-klmn12345678",
  "name": "Jane Smith",
  "email": "jane@acme.com",
  "role": "buyer",
  "company": "ACME Recycling",
  "country": "DE",
  "is_active": true
}
```

### 2. Make User Permanent (Git-tracked)

Edit `storage/seed_users.json` and add:

```json
{
  "name": "Jane Smith",
  "email": "jane@acme.com",
  "company": "ACME Recycling",
  "country": "DE",
  "role": "buyer"
}
```

### 3. Commit to Git

```bash
git add storage/seed_users.json
git commit -m "Add Jane Smith (buyer) from ACME Recycling"
git push origin main
```

### 4. Next Deployment/Local Setup

When any environment (local, CI/CD, Vercel) starts the backend:
- Seed fixtures are loaded automatically
- Jane Smith's user is created if not already in the database
- No manual user creation needed—fully reproducible

---

## Managing Test Data

### View All Seeded Users

```bash
cat storage/seed_users.json
```

### View All Created Users (in database)

```bash
sqlite3 circularx.db "SELECT id, name, email, role, company FROM user;"
```

Or use the DB Browser for SQLite (GUI tool).

### Reset Database to Seed State

```bash
# Delete the database file
rm circularx.db

# Restart backend—seed fixtures will recreate all users
uvicorn main:app --reload
```

### Remove a User from Seed

1. Edit `storage/seed_users.json`
2. Delete the JSON object for that user
3. Commit:
   ```bash
   git add storage/seed_users.json
   git commit -m "Remove test user: [old user email]"
   git push
   ```
4. On next backend restart, only users in the JSON file will be created

---

## Best Practices

✅ **DO:**
- Add reproducible test users to `storage/seed_users.json`
- Commit seed changes to git
- Use seed fixtures for CI/CD and team collaboration
- Keep email addresses unique and recognizable (e.g., `john@company.com`)
- Document why you're adding a test user (use commit message)

❌ **DON'T:**
- Commit `circularx.db` to git (binary, noisy diffs)
- Forget to add important test users to seed fixtures
- Create users via frontend and expect them to be in git automatically
- Share `.db` files between developers (each has their own database)

---

## Integration with Frontend Testing

The frontend team can:

1. **Use existing seed users** for basic testing
   ```javascript
   // JavaScript example
   const user = await fetch('http://127.0.0.1:8000/auth/me', {
     headers: { 'x-test-role': 'manufacturer' }
   }).then(r => r.json());
   ```

2. **Create new test users via register endpoint** for specific scenarios
   ```javascript
   const newUser = await fetch('http://127.0.0.1:8000/auth/register', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify({
       email: 'scenario@test.com',
       name: 'Scenario Test User',
       company: 'Test Co',
       country: 'IN',
       role: 'buyer'
     })
   }).then(r => r.json());
   ```

3. **Request backend updates** to seed fixtures for commonly-needed test users
   - Submit a PR to add to `storage/seed_users.json`
   - Ensures consistent setup across all environments

---

## Troubleshooting

**Q: I created a user via frontend but it's gone after I restart?**
- A: The user is in the database but not in seed fixtures. Add it to `storage/seed_users.json` to make it persist.

**Q: Why doesn't my new seed user appear?**
- A: Check that:
  1. The JSON is valid (use `python -m json.tool storage/seed_users.json`)
  2. Email is unique (no duplicates)
  3. Role is valid: `manufacturer|buyer|tpqc|admin`
  4. Backend restarted after editing the JSON

**Q: Should we commit circularx.db to git?**
- A: **No**. Database files are binary and change constantly. Use seed fixtures instead.

**Q: How do we share test data between developers?**
- A: Edit and commit `storage/seed_users.json`. All developers get the same test users on startup.

