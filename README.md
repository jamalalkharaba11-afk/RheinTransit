# RheinTransit V5 – Persistent Reviews on Render

This version uses **Render PostgreSQL** when `DATABASE_URL` is configured. Local development automatically falls back to SQLite.

## Render
1. Create a Render Postgres database in the same region as the web service.
2. Add the database connection string to the web service as `DATABASE_URL` (prefer the Internal Database URL).
3. Add `SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` as environment variables.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`

The app automatically creates the `requests` and `reviews` tables on startup.

## Reviews
Customers submit 1–5 stars, service and a comment. New reviews are saved with status `Neu` and do not appear publicly until an admin changes them to `Freigegeben`.

Admin: `/admin`
