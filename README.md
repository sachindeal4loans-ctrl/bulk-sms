# Bulk SMS Manager

A FastAPI demo for preparing and tracking consent-based SMS campaigns. **This project does not send real SMS**; it records simulated campaign statuses. Real SMS requires a legitimate provider, credentials, opt-in consent, opt-out handling, and compliance with local messaging rules.

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD='choose-a-strong-password'
export APP_SECRET='use-a-long-random-secret'
uvicorn app:app --reload
```
Open http://127.0.0.1:8000

## Deploy on Render
Build command: `pip install -r requirements.txt`
Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
Add `ADMIN_PASSWORD` in the Render service's Environment settings. Add a long random `APP_SECRET` if not already configured. Commit the `app.py`, `templates/`, and `static/` paths to GitHub before deploying.

CSV should contain one phone number per row, optionally with a `phone` header. Only use recipients who agreed to receive messages.
