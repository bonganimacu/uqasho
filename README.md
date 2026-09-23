# Room Rental Platform — South Africa (MVP)

A production-style room-rental marketplace implementing the MVP of the SRS:
guest browsing & search, listing pages, auth (browse freely / register to interact),
tenant favourites + messaging + viewing requests, landlord property/room management
with image uploads, notifications, reporting, and admin moderation.

## Quick start (local)

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

## Quick start (Docker — recommended for hosting)

```bash
docker compose up --build
# open http://localhost:8000
```

## Demo accounts (seeded when DB is empty, SEED_DEMO=1)

| Role     | Email                 | Password      |
|----------|-----------------------|---------------|
| Admin    | admin@roomrental.co.za| admin123      |
| Landlord | thabo@example.co.za   | password123   |
| Landlord | naledi@example.co.za  | password123   |
| Tenant   | sipho@example.co.za   | password123   |

Change via `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars. Delete `roomrental.db` (and the
`data/` volume in Docker) to reseed.

## Hosting options

- **VPS (Ubuntu)**: clone repo, `docker compose up -d`, put Nginx in front with TLS
  (certbot). Set `ADMIN_PASSWORD` and keep the `uploads` + `data` volumes backed up.
- **Render / Railway / Fly.io**: deploy the Dockerfile as a web service; add a persistent
  disk mounted at `/app/data` and `/app/uploads` (SQLite + local disk need persistence).
- For horizontal scaling or serverless hosting, swap SQLite for PostgreSQL (schema in the
  SRS §25 maps 1:1) and local uploads for S3 — the app is structured to allow that.

## Feature map vs SRS

| SRS area | Status in this build |
|---|---|
| Guest search/filters/sort | ✅ |
| Listing detail, pricing transparency, amenities | ✅ |
| Interaction gate (login → return to listing) | ✅ via ?next= redirect |
| Tenant: favourites, messaging, viewings, notifications | ✅ |
| Landlord: dashboard, properties, rooms, images, lifecycle | ✅ |
| Admin: stats, listing approval, report triage, user suspend | ✅ |
| Email verification / payments / maps / verification | ❌ future (see SRS §40) |

## Security notes (MVP build)

- bcrypt password hashing, HttpOnly session cookies, server-side session expiry.
- SQL injection: parameterized queries throughout.
- XSS: Jinja auto-escaping on all rendered output.
- Uploads: magic-byte validation, type/size caps, EXIF stripped by Pillow re-encode,
  1600px max dimension, UUID filenames.
- Exact street addresses are never rendered publicly — shown to tenants only when a
  viewing is ACCEPTED.
- **Before real production use**: enforce HTTPS (secure cookie flag activates
  automatically), set a strong `ADMIN_PASSWORD`, put the app behind a reverse proxy,
  and add rate limiting at the proxy level.

## Project layout

```
app.py               # entire application (routes, DB schema, auth, seed data)
templates/           # Jinja2 UI (18 pages)
static/style.css     # styling
uploads/             # room images (runtime)
roomrental.db        # SQLite database (created on first run)
Dockerfile / docker-compose.yml / requirements.txt
```

## Target architecture migration

The repository now contains the first target-stack foundation described in the
SRS alongside the working FastAPI MVP:

```text
backend/       # Java 17 / Spring Boot API foundation
frontend/      # React / TypeScript / Vite web foundation
app.py         # Existing MVP reference implementation
```

Run the frontend foundation locally:

```bash
cd frontend
npm install
npm run dev
```

The Spring Boot module requires Java 17 and Maven. Its API is versioned under
`/api/v1`; the first health endpoint is `/api/v1/health`. Domain modules,
PostgreSQL migrations, authentication, and API integration are being migrated
incrementally from the MVP according to
`Room_Rental_Platform_SRS_and_System_Design.md`.

The target container stack is defined in `docker-compose.target.yml`. Set a
strong `POSTGRES_PASSWORD` and run `docker compose -f docker-compose.target.yml
up --build` when Docker is available. The target frontend is then served at
`http://localhost:8080` and proxies `/api/` requests to the Spring Boot service.

The full SRS & System Design Document for this platform is available alongside this
codebase (Room_Rental_Platform_SRS_and_System_Design.md).
