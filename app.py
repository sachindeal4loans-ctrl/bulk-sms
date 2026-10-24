import csv, io, os, re, sqlite3
from datetime import datetime, timezone
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

DB_PATH = os.getenv("DB_PATH", "bulk_sms.db")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
app = FastAPI(title="Bulk SMS Manager")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET", "change-this-before-deploying"), https_only=True, same_site="lax")
templates = Jinja2Templates(directory="templates")

def connect():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row; return c

with connect() as c:
    c.execute("CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY, created_at TEXT, message TEXT, total INTEGER, status TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS recipients (id INTEGER PRIMARY KEY, campaign_id INTEGER, phone TEXT, status TEXT, detail TEXT)")

def logged_in(r): return bool(r.session.get("logged_in"))
def phone_ok(s):
    s = re.sub(r"[() .-]", "", s.strip())
    if s.startswith("00"): s = "+" + s[2:]
    if s.startswith("+") and s[1:].isdigit() and 8 <= len(s[1:]) <= 15: return s
    if s.isdigit() and 8 <= len(s) <= 15: return s
    return None

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return """<!doctype html><meta name="viewport" content="width=device-width"><link rel="stylesheet" href="/static/style.css"><main><h1>Bulk SMS Manager</h1><p>Admin sign-in</p><form method="post"><label>Password</label><input type="password" name="password" required><button>Sign in</button></form></main>"""

@app.post("/login")
def login(request: Request, password: str = Form(...)):
    if not ADMIN_PASSWORD: return HTMLResponse("Set ADMIN_PASSWORD in your hosting environment.", status_code=503)
    if password != ADMIN_PASSWORD: return HTMLResponse("Incorrect password. <a href='/login'>Try again</a>", status_code=401)
    request.session["logged_in"] = True
    return RedirectResponse("/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear(); return RedirectResponse("/login", status_code=303)

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not logged_in(request): return RedirectResponse("/login", status_code=303)
    with connect() as c: rows = c.execute("SELECT * FROM campaigns ORDER BY id DESC LIMIT 25").fetchall()
    return templates.TemplateResponse("index.html", {"request":request, "campaigns":rows})

@app.post("/campaign", response_class=HTMLResponse)
async def campaign(request: Request, message: str = Form(...), numbers_text: str = Form(""), consent: str = Form(""), contacts_file: UploadFile = File(None)):
    if not logged_in(request): return RedirectResponse("/login", status_code=303)
    if consent != "yes": return HTMLResponse("Confirm that all recipients opted in before creating a campaign.", status_code=400)
    message = message.strip()
    if not message or len(message) > 1000: return HTMLResponse("Message must be 1–1000 characters.", status_code=400)
    raw = [x for x in re.split(r"[,;\\s]+", numbers_text) if x]
    if contacts_file and contacts_file.filename:
        data = (await contacts_file.read()).decode("utf-8-sig", errors="replace")
        for row in csv.reader(io.StringIO(data)):
            if row and row[0].strip().lower() not in {"phone","mobile","number","phone_number"}: raw.append(row[0].strip())
    valid, seen = [], set()
    for x in raw:
        p = phone_ok(x)
        if p and p not in seen: valid.append(p); seen.add(p)
    if not valid: return HTMLResponse("No valid phone numbers found. Use numbers like +919876543210.", status_code=400)
    if len(valid) > 500: return HTMLResponse("Maximum 500 unique contacts per demo campaign.", status_code=400)
    with connect() as c:
        cur = c.execute("INSERT INTO campaigns(created_at,message,total,status) VALUES(?,?,?,?)", (datetime.now(timezone.utc).isoformat(), message, len(valid), "DEMO ONLY — not sent"))
        cid = cur.lastrowid
        c.executemany("INSERT INTO recipients(campaign_id,phone,status,detail) VALUES(?,?,?,?)", [(cid,p,"SIMULATED","No SMS was sent; demo mode only.") for p in valid])
    return RedirectResponse(f"/campaign/{cid}", status_code=303)

@app.get("/campaign/{cid}", response_class=HTMLResponse)
def details(request: Request, cid: int):
    if not logged_in(request): return RedirectResponse("/login", status_code=303)
    with connect() as c:
        campaign = c.execute("SELECT * FROM campaigns WHERE id=?", (cid,)).fetchone()
        recipients = c.execute("SELECT * FROM recipients WHERE campaign_id=? ORDER BY id", (cid,)).fetchall()
    if not campaign: return HTMLResponse("Campaign not found", status_code=404)
    return templates.TemplateResponse("campaign.html", {"request":request, "campaign":campaign, "recipients":recipients})
