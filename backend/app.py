"""TGCA SARL.AU - lightweight lead API for separate static website hosting.

Requires a persistent storage path in production. A free host with an ephemeral
filesystem may lose saved requests on restart; configure SMTP as a second channel.
"""
import hmac
import logging
import os
import re
import secrets
import smtplib
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

LOG = logging.getLogger("tgca")
DB_PATH = Path(os.getenv("TGCA_DB_PATH", "./data/tgca-leads.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ORIGINS = [o.strip() for o in os.getenv(
    "TGCA_SITE_ORIGINS",
    "https://raw.githack.com,https://rawcdn.githack.com,https://ucef90.github.io",
).split(",") if o.strip()]
ADMIN_TOKEN = os.getenv("TGCA_ADMIN_TOKEN", "")
app = FastAPI(title="TGCA – Réception des devis", docs_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-TGCA-Admin-Token"],
)
last_submissions = {}

@contextmanager
def database():
    cn = sqlite3.connect(str(DB_PATH), timeout=20)
    cn.row_factory = sqlite3.Row
    cn.execute("PRAGMA busy_timeout=20000")
    try:
        yield cn
        cn.commit()
    finally:
        cn.close()

with database() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL,
          name TEXT NOT NULL,
          email TEXT NOT NULL,
          phone TEXT NOT NULL,
          project_type TEXT NOT NULL,
          city TEXT NOT NULL,
          budget TEXT NOT NULL,
          message TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'nouveau'
        )
    """)

class Quote(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    phone: str = Field(min_length=6, max_length=40)
    project_type: str = Field(default="Autre", max_length=100)
    city: str = Field(default="", max_length=100)
    budget: str = Field(default="", max_length=100)
    message: str = Field(min_length=10, max_length=4000)
    consent: bool
    website: str = Field(default="", max_length=300)

class StatusUpdate(BaseModel):
    status: str

def authorize(token):
    if not ADMIN_TOKEN or len(ADMIN_TOKEN) < 32:
        raise HTTPException(503, "Administrateur non configuré")
    if not token or not hmac.compare_digest(token, ADMIN_TOKEN):
        raise HTTPException(401, "Accès refusé")

def notify(lead_id, item):
    host = os.getenv("SMTP_HOST")
    address = os.getenv("NOTIFICATION_EMAIL")
    if not host or not address:
        return
    email = EmailMessage()
    email["Subject"] = f"[TGCA] Nouvelle demande de devis #{lead_id}"
    email["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER") or address
    email["To"] = address
    email.set_content(
        f"Nouvelle demande #{lead_id}\n\nNom: {item.name}\nEmail: {item.email}\n"
        f"Téléphone: {item.phone}\nType: {item.project_type}\n"
        f"Ville: {item.city}\nBudget: {item.budget}\n\n{item.message}"
    )
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=12) as smtp:
            smtp.starttls()
            if os.getenv("SMTP_USER"):
                smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD", ""))
            smtp.send_message(email)
    except Exception:
        LOG.exception("Notification email impossible ; devis conservé en base")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TGCA devis"}

@app.post("/api/devis", status_code=201)
def submit(request: Request, item: Quote):
    if item.website:
        raise HTTPException(400, "Envoi refusé")
    if item.consent is not True:
        raise HTTPException(422, "Le consentement est nécessaire")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", item.email):
        raise HTTPException(422, "Adresse e-mail invalide")
    peer = request.client.host if request.client else "unknown"
    now = time.monotonic()
    last = last_submissions.get(peer, 0)
    if now - last < 20:
        raise HTTPException(429, "Veuillez réessayer dans quelques instants")
    last_submissions[peer] = now
    with database() as conn:
        cur = conn.execute(
            """INSERT INTO leads
               (created_at, name, email, phone, project_type, city, budget, message)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
            (datetime.now(timezone.utc).isoformat(), item.name.strip(),
             item.email.strip(), item.phone.strip(), item.project_type.strip(),
             item.city.strip(), item.budget.strip(), item.message.strip()),
        )
        lead_id = cur.lastrowid
    notify(lead_id, item)
    return {"ok": True, "reference": f"TGCA-{lead_id:05d}"}

@app.get("/api/admin/leads")
def list_leads(x_tgca_admin_token: str | None = Header(default=None)):
    authorize(x_tgca_admin_token)
    with database() as conn:
        rows = conn.execute(
            "SELECT * FROM leads ORDER BY id DESC LIMIT 500"
        ).fetchall()
    return {"leads": [dict(row) for row in rows]}

@app.patch("/api/admin/leads/{lead_id}")
def change_status(
    lead_id: int, item: StatusUpdate,
    x_tgca_admin_token: str | None = Header(default=None),
):
    authorize(x_tgca_admin_token)
    allowed = {"nouveau", "à traiter", "contacté", "devis envoyé", "clos"}
    if item.status not in allowed:
        raise HTTPException(422, "Statut invalide")
    with database() as conn:
        cur = conn.execute("UPDATE leads SET status=? WHERE id=?", (item.status, lead_id))
        if not cur.rowcount:
            raise HTTPException(404, "Demande introuvable")
    return {"ok": True, "id": lead_id, "status": item.status}
