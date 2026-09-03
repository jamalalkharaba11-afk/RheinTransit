from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-this-secret-in-production"
DB = os.path.join(os.path.dirname(__file__), "rheintransit.db")

PRICES = {"umzug":120, "transport":80, "reinigung":70, "entruempelung":100}

def db():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row; return con

def init_db():
    con=db()
    con.execute("""CREATE TABLE IF NOT EXISTS requests(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,email TEXT NOT NULL,phone TEXT,
      service TEXT NOT NULL,rooms INTEGER DEFAULT 1,distance INTEGER DEFAULT 0,floor INTEGER DEFAULT 0,
      elevator TEXT DEFAULT 'Ja',extras TEXT,estimated_price REAL NOT NULL,date TEXT,message TEXT,
      status TEXT DEFAULT 'Neu',created_at TEXT NOT NULL)""")
    con.commit(); con.close()

def calculate(service,rooms,distance,floor,elevator,extras):
    price=PRICES.get(service,100)
    price+=max(0,rooms-1)*(45 if service=="reinigung" else 55)
    price+=distance*(1.80 if service in ("umzug","transport") else 0.40)
    price+=floor*25
    if elevator=="Nein": price+=45
    price+=sum({"abbau":55,"aufbau":65,"verpackung":40}.get(x,0) for x in extras)
    return round(price,2)

@app.route("/")
def index(): return render_template("index.html")

@app.route("/angebot",methods=["GET","POST"])
def quote():
    if request.method=="POST":
        name=request.form["name"].strip(); email=request.form["email"].strip()
        service=request.form["service"]; rooms=int(request.form.get("rooms",1))
        distance=int(request.form.get("distance",0)); floor=int(request.form.get("floor",0))
        elevator=request.form.get("elevator","Ja"); extras=request.form.getlist("extras")
        price=calculate(service,rooms,distance,floor,elevator,extras)
        con=db(); con.execute("""INSERT INTO requests
        (name,email,phone,service,rooms,distance,floor,elevator,extras,estimated_price,date,message,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",(name,email,request.form.get("phone",""),service,rooms,distance,floor,
        elevator,",".join(extras),price,request.form.get("date",""),request.form.get("message",""),
        datetime.now().strftime("%Y-%m-%d %H:%M"))); con.commit(); con.close()
        return render_template("success.html",name=name,price=price)
    return render_template("quote.html")

@app.post("/api/calculate")
def api_calculate():
    d=request.get_json() or {}
    return jsonify(price=calculate(d.get("service","umzug"),int(d.get("rooms",1)),int(d.get("distance",0)),
                                    int(d.get("floor",0)),d.get("elevator","Ja"),d.get("extras",[])))

@app.route("/leistungen/<service>")
def service_page(service):
    titles={"umzug":"Umzug in Duisburg","transport":"Transport in Duisburg",
            "reinigung":"Wohnungsreinigung in Duisburg","entruempelung":"Entrümpelung in Duisburg"}
    if service not in titles: return redirect(url_for("index"))
    return render_template("service.html",service=service,title=titles[service])

@app.route("/kontakt")
def contact(): return render_template("contact.html")

@app.route("/impressum")
def impressum(): return render_template("impressum.html")

@app.route("/datenschutz")
def privacy(): return render_template("privacy.html")

@app.route("/robots.txt")
def robots():
    r=f"""User-agent: *
Allow: /
Sitemap: {request.url_root.rstrip('/')}/sitemap.xml
"""
    return make_response(r,200,{"Content-Type":"text/plain"})

@app.route("/sitemap.xml")
def sitemap():
    pages=["/","/angebot","/kontakt","/impressum","/datenschutz",
           "/leistungen/umzug","/leistungen/transport","/leistungen/reinigung","/leistungen/entruempelung"]
    xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for p in pages: xml+=f"<url><loc>{request.url_root.rstrip('/')}{p}</loc></url>"
    xml+="</urlset>"
    return make_response(xml,200,{"Content-Type":"application/xml"})

@app.route("/admin/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form.get("username")=="admin" and request.form.get("password")=="rhein2026":
            session["admin"]=True; return redirect(url_for("dashboard"))
        flash("Benutzername oder Passwort falsch.")
    return render_template("admin/login.html")

@app.route("/admin")
def dashboard():
    if not session.get("admin"): return redirect(url_for("login"))
    con=db(); rows=con.execute("SELECT * FROM requests ORDER BY id DESC").fetchall()
    stats=(len(rows),sum(r["status"]=="Neu" for r in rows),sum(r["estimated_price"] for r in rows))
    con.close(); return render_template("admin/dashboard.html",requests=rows,stats=stats)

@app.post("/admin/status/<int:req_id>")
def status(req_id):
    if not session.get("admin"): return redirect(url_for("login"))
    con=db(); con.execute("UPDATE requests SET status=? WHERE id=?",(request.form["status"],req_id))
    con.commit(); con.close(); return redirect(url_for("dashboard"))

@app.route("/admin/logout")
def logout(): session.clear(); return redirect(url_for("login"))

if __name__=="__main__":
    init_db(); app.run(debug=True)
