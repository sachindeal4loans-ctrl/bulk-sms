# Bulk SMS Manager

Responsive FastAPI dashboard for preparing and tracking consent-based SMS campaigns.

**Important:** This version is a demo. It records campaigns as `SIMULATED` and does not send real SMS. Real delivery requires a legitimate SMS provider, approved credentials, opt-in consent, opt-out handling, and compliance with local laws and provider rules.

## Local run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD='choose-a-strong-password'
export APP_SECRET='replace-with-a-long-random-secret'
uvicorn app:app --reload
```
Open http://127.0.0.1:8000

## Render deployment
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Set `ADMIN_PASSWORD` to a strong password in the Render service's Environment settings.
- Set `APP_SECRET` to a long random secret, or use the generated value configured by `render.yaml`.
- Commit `app.py`, `requirements.txt`, `render.yaml`, `templates/`, and `static/` to the repository root.

## CSV
One phone number per row. A first-row header such as `phone` or `mobile` is accepted. Only include recipients who explicitly agreed to receive messages.
