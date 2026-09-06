from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, Float, DateTime, select, update, func
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-in-production")

# Render: set DATABASE_URL to your Render Postgres Internal Database URL.
# Local development: if DATABASE_URL is absent, SQLite is used.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///rheintransit.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
metadata = MetaData()

requests_table = Table(
    "requests", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(160), nullable=False),
    Column("email", String(255), nullable=False),
    Column("phone", String(80)),
    Column("service", String(80), nullable=False),
    Column("rooms", Integer, default=1),
    Column("distance", Integer, default=0),
    Column("floor", Integer, default=0),
    Column("elevator", String(20), default="Ja"),
    Column("extras", Text),
    Column("estimated_price", Float, nullable=False),
    Column("date", String(40)),
    Column("message", Text),
    Column("status", String(40), default="Neu"),
    Column("created_at", DateTime, nullable=False),
)

reviews_table = Table(
    "reviews", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String(160), nullable=False),
    Column("service", String(80), nullable=False),
    Column("rating", Integer, nullable=False),
    Column("comment", Text, nullable=False),
    Column("status", String(40), default="Neu", nullable=False),
    Column("created_at", DateTime, nullable=False),
)

PRICES = {"umzug": 120, "transport": 80, "reinigung": 70, "entruempelung": 100}
SERVICE_LABELS = {
    "umzug": "Umzug",
    "transport": "Transport",
    "reinigung": "Reinigung",
    "entruempelung": "Entrümpelung",
}


def init_db():
    metadata.create_all(engine)


def calculate(service, rooms, distance, floor, elevator, extras):
    price = PRICES.get(service, 100)
    price += max(0, rooms - 1) * (45 if service == "reinigung" else 55)
    price += distance * (1.80 if service in ("umzug", "transport") else 0.40)
    price += floor * 25
    if elevator == "Nein":
        price += 45
    price += sum({"abbau": 55, "aufbau": 65, "verpackung": 40}.get(x, 0) for x in extras)
    return round(price, 2)


def public_reviews(limit=12):
    with engine.connect() as con:
        rows = con.execute(
            select(reviews_table)
            .where(reviews_table.c.status == "Freigegeben")
            .order_by(reviews_table.c.created_at.desc())
            .limit(limit)
        ).mappings().all()
        stats = con.execute(
            select(func.count(reviews_table.c.id), func.coalesce(func.avg(reviews_table.c.rating), 0))
            .where(reviews_table.c.status == "Freigegeben")
        ).one()
    return rows, int(stats[0] or 0), float(stats[1] or 0)


@app.route("/")
def index():
    reviews, review_count, review_average = public_reviews()
    return render_template("index.html", reviews=reviews, review_count=review_count, review_average=review_average)


@app.post("/bewertung")
def add_review():
    name = request.form.get("name", "").strip()
    service = request.form.get("service", "").strip()
    comment = request.form.get("comment", "").strip()
    try:
        rating = int(request.form.get("rating", "0"))
    except ValueError:
        rating = 0

    if not name or not comment or service not in SERVICE_LABELS or rating not in range(1, 6):
        flash("Bitte Name, Leistung, Bewertung und Kommentar korrekt ausfüllen.")
        return redirect(url_for("index") + "#bewertungen")
    if len(name) > 160 or len(comment) > 2000:
        flash("Der Name oder Kommentar ist zu lang.")
        return redirect(url_for("index") + "#bewertung")

    with engine.begin() as con:
        con.execute(reviews_table.insert().values(
            name=name, service=service, rating=rating, comment=comment,
            status="Neu", created_at=datetime.now()
        ))
    flash("Vielen Dank! Ihre Bewertung wurde gespeichert und wird nach kurzer Prüfung veröffentlicht.")
    return redirect(url_for("index") + "#bewertungen")


@app.route("/angebot", methods=["GET", "POST"])
def quote():
    if request.method == "POST":
        name = request.form["name"].strip(); email = request.form["email"].strip()
        service = request.form["service"]; rooms = int(request.form.get("rooms", 1))
        distance = int(request.form.get("distance", 0)); floor = int(request.form.get("floor", 0))
        elevator = request.form.get("elevator", "Ja"); extras = request.form.getlist("extras")
        price = calculate(service, rooms, distance, floor, elevator, extras)
        with engine.begin() as con:
            con.execute(requests_table.insert().values(
                name=name, email=email, phone=request.form.get("phone", ""), service=service,
                rooms=rooms, distance=distance, floor=floor, elevator=elevator,
                extras=",".join(extras), estimated_price=price, date=request.form.get("date", ""),
                message=request.form.get("message", ""), status="Neu", created_at=datetime.now()
            ))
        return render_template("success.html", name=name, price=price)
    return render_template("quote.html")


@app.post("/api/calculate")
def api_calculate():
    d = request.get_json() or {}
    return jsonify(price=calculate(d.get("service", "umzug"), int(d.get("rooms", 1)), int(d.get("distance", 0)),
                                  int(d.get("floor", 0)), d.get("elevator", "Ja"), d.get("extras", [])))


@app.route("/leistungen/<service>")
def service_page(service):
    titles = {"umzug": "Umzugsunternehmen in Duisburg | RheinTransit", "transport": "Möbeltransport & Transport in Duisburg | RheinTransit",
              "reinigung": "Wohnungsreinigung in Duisburg | RheinTransit", "entruempelung": "Entrümpelung in Duisburg | RheinTransit"}
    if service not in titles: return redirect(url_for("index"))
    images = {"umzug": "/static/images/photos/moving.jpg", "transport": "/static/images/photos/transport.jpg",
              "reinigung": "/static/images/photos/cleaning.jpg", "entruempelung": "/static/images/photos/decluttering.jpg"}
    return render_template("service.html", service=service, title=titles[service], service_image=images[service])


@app.route("/einsatzgebiet")
def service_area(): return render_template("service_area.html")
@app.route("/kontakt")
def contact(): return render_template("contact.html")
@app.route("/impressum")
def impressum(): return render_template("impressum.html")
@app.route("/datenschutz")
def privacy(): return render_template("privacy.html")

@app.route("/robots.txt")
def robots():
    r = f"""User-agent: *\nAllow: /\nSitemap: {request.url_root.rstrip('/')}/sitemap.xml\n"""
    return make_response(r, 200, {"Content-Type": "text/plain"})

@app.route("/sitemap.xml")
def sitemap():
    pages = ["/", "/angebot", "/einsatzgebiet", "/kontakt", "/impressum", "/datenschutz",
             "/leistungen/umzug", "/leistungen/transport", "/leistungen/reinigung", "/leistungen/entruempelung"]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for p in pages: xml += f"<url><loc>{request.url_root.rstrip('/')}{p}</loc></url>"
    xml += "</urlset>"
    return make_response(xml, 200, {"Content-Type": "application/xml"})


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == os.environ.get("ADMIN_USERNAME", "admin") and request.form.get("password") == os.environ.get("ADMIN_PASSWORD", "rhein2026"):
            session["admin"] = True; return redirect(url_for("dashboard"))
        flash("Benutzername oder Passwort falsch.")
    return render_template("admin/login.html")


@app.route("/admin")
def dashboard():
    if not session.get("admin"): return redirect(url_for("login"))
    with engine.connect() as con:
        rows = con.execute(select(requests_table).order_by(requests_table.c.id.desc())).mappings().all()
        review_rows = con.execute(select(reviews_table).order_by(reviews_table.c.id.desc())).mappings().all()
    stats = (len(rows), sum(r["status"] == "Neu" for r in rows), sum(r["estimated_price"] for r in rows))
    return render_template("admin/dashboard.html", requests=rows, reviews=review_rows, stats=stats)


@app.post("/admin/status/<int:req_id>")
def status(req_id):
    if not session.get("admin"): return redirect(url_for("login"))
    with engine.begin() as con:
        con.execute(update(requests_table).where(requests_table.c.id == req_id).values(status=request.form["status"]))
    return redirect(url_for("dashboard"))


@app.post("/admin/review-status/<int:review_id>")
def review_status(review_id):
    if not session.get("admin"): return redirect(url_for("login"))
    allowed = {"Neu", "Freigegeben", "Abgelehnt"}
    new_status = request.form.get("status", "Neu")
    if new_status not in allowed: new_status = "Neu"
    with engine.begin() as con:
        con.execute(update(reviews_table).where(reviews_table.c.id == review_id).values(status=new_status))
    return redirect(url_for("dashboard") + "#bewertungen-admin")


@app.route("/admin/logout")
def logout(): session.clear(); return redirect(url_for("login"))
with app.app_context():
    db.create_all()

init_db()

if __name__ == "__main__":
    app.run(debug=True)
