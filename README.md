# Bulk SMS Manager

A small FastAPI project you can upload to GitHub and deploy on Render.

**Important:** This is a demo. It does not send real SMS. It simulates campaigns and stores recipient statuses. Actual SMS requires a legitimate provider, credentials, recipient consent, opt-out handling, and compliance with local messaging rules.

## Features
- Password-protected dashboard
- Paste numbers or upload CSV (one phone number per row)
- Compose a message and confirm recipient consent
- Remove duplicate numbers and validate basic phone formats
- SQLite campaign history and simulated delivery statuses
- `/health` endpoint

## Run on Mac
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD='use-a-strong-password'
export APP_SECRET='use-a-long-random-secret'
uvicorn app:app --reload
```
Open http://127.0.0.1:8000

## GitHub
Create a repository named `bulk-sms-manager` and upload all files/folders. Do not commit passwords, API keys, `.env`, or `bulk_sms.db`.

## Render
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Add environment variable `ADMIN_PASSWORD` with a strong password.
- Set `APP_SECRET` to a long random secret.
- Deploy, then open the Render URL and sign in.

## CSV example
```csv
phone
+919876543210
+14155552671
```
Only use contact lists for which recipients have given permission. Before enabling real SMS, implement provider integration, opt-outs, rate limits, delivery callbacks, and any required regional registrations/templates.
