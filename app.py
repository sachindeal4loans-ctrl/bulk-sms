import csv
import io
import os
import re
import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(BASE_DIR, "bulk_sms.db"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
APP_SECRET = os.getenv("APP_SECRET", "replace-with-a-long-random-secret")

app = FastAPI(title="Bulk SMS Manager")
app.add_middleware(
    SessionMiddleware,
    secret_key=APP_SECRET,
    https_only=True,
    same_site="lax",
)

STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with connect() as conn:
    conn.execute("""CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        message TEXT NOT NULL,
        total INTEGER NOT NULL,
        status TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        phone TEXT NOT NULL,
        status TEXT NOT NULL,
        detail TEXT NOT NULL
    )""")


def logged_in(request: Request) -> bool:
    return bool(request.session.get("logged_in"))


def normalize_phone(value: str):
    value = re.sub(r"[()\s.-]", "", value.strip())
    if value.startswith("00"):
        value = "+" + value[2:]
    digits = value[1:] if value.startswith("+") else value
    if digits.isdigit() and 8 <= len(digits) <= 15:
        return ("+" if value.startswith("+") else "") + digits
    return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if not ADMIN_PASSWORD:
        return HTMLResponse(
            "Admin login is not configured. Set ADMIN_PASSWORD in your hosting environment.",
            status_code=503,
        )
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": ""}
    )


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, password: str = Form(...)):
    if not ADMIN_PASSWORD:
        return HTMLResponse(
            "Admin login is not configured. Set ADMIN_PASSWORD in your hosting environment.",
            status_code=503,
        )
    if password != ADMIN_PASSWORD:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Incorrect password. Please try again."},
            status_code=401,
        )
    request.session["logged_in"] = True
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    with connect() as conn:
        campaigns = conn.execute(
            "SELECT * FROM campaigns ORDER BY id DESC LIMIT 50"
        ).fetchall()
        total_campaigns = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        total_recipients = conn.execute(
            "SELECT COALESCE(SUM(total),0) FROM campaigns"
        ).fetchone()[0]
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "campaigns": campaigns,
            "total_campaigns": total_campaigns,
            "total_recipients": total_recipients,
        },
    )


@app.post("/campaign")
async def create_campaign(
    request: Request,
    message: str = Form(...),
    numbers_text: str = Form(""),
    consent: str = Form(""),
    contacts_file: UploadFile = File(None),
):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    if consent != "yes":
        return HTMLResponse("Please confirm that recipients opted in.", status_code=400)

    message = message.strip()
    if not message or len(message) > 1000:
        return HTMLResponse("Message must be between 1 and 1000 characters.", status_code=400)

    raw_numbers = [item for item in re.split(r"[,;\s]+", numbers_text) if item]
    if contacts_file and contacts_file.filename:
        content = (await contacts_file.read()).decode("utf-8-sig", errors="replace")
        for row in csv.reader(io.StringIO(content)):
            if row:
                candidate = row[0].strip()
                if candidate.lower() not in {
                    "phone", "mobile", "number", "phone_number", "mobile_number"
                }:
                    raw_numbers.append(candidate)

    valid_numbers, seen = [], set()
    invalid_count = 0
    for item in raw_numbers:
        phone = normalize_phone(item)
        if phone is None:
            invalid_count += 1
        elif phone not in seen:
            seen.add(phone)
            valid_numbers.append(phone)

    if not valid_numbers:
        return HTMLResponse(
            "No valid phone numbers were found. Enter numbers such as +919876543210.",
            status_code=400,
        )
    if len(valid_numbers) > 500:
        return HTMLResponse("A demo campaign is limited to 500 unique recipients.", status_code=400)

    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO campaigns(created_at,message,total,status) VALUES(?,?,?,?)",
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                message,
                len(valid_numbers),
                "DEMO ONLY — not sent",
            ),
        )
        campaign_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO recipients(campaign_id,phone,status,detail) VALUES(?,?,?,?)",
            [
                (campaign_id, phone, "SIMULATED", "Demo mode: no SMS was sent.")
                for phone in valid_numbers
            ],
        )
    return RedirectResponse(f"/campaign/{campaign_id}", status_code=303)


@app.get("/campaign/{campaign_id}", response_class=HTMLResponse)
def campaign_details(request: Request, campaign_id: int):
    if not logged_in(request):
        return RedirectResponse("/login", status_code=303)
    with connect() as conn:
        campaign = conn.execute(
            "SELECT * FROM campaigns WHERE id=?", (campaign_id,)
        ).fetchone()
        recipients = conn.execute(
            "SELECT * FROM recipients WHERE campaign_id=? ORDER BY id",
            (campaign_id,),
        ).fetchall()
    if campaign is None:
        return HTMLResponse("Campaign not found.", status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="campaign.html",
        context={"campaign": campaign, "recipients": recipients},
    )
