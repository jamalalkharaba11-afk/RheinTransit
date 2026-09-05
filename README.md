# RheinTransit V5 – PostgreSQL Bewertungen

## Render dauerhaft einrichten
1. In Render ein **PostgreSQL**-Datenbank-Produkt anlegen.
2. Beim Web Service unter **Environment** die Variable `DATABASE_URL` mit der **Internal Database URL** der Render-PostgreSQL-Datenbank verbinden.
3. Zusätzlich setzen:
   - `SECRET_KEY` = langer zufälliger Wert
   - `ADMIN_USER` = gewünschter Admin-Benutzer
   - `ADMIN_PASSWORD` = starkes Admin-Passwort
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `gunicorn app:app`

Beim Start erstellt die Anwendung die Tabellen `requests` und `reviews` automatisch. Wenn `DATABASE_URL` gesetzt ist, werden die Daten in PostgreSQL gespeichert und bleiben bei Deployments/Restarts erhalten.

## Lokal
Ohne `DATABASE_URL` fällt die Anwendung automatisch auf SQLite zurück.
