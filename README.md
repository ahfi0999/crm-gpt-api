# CRM GPT API

Read-only FastAPI bridge from a Custom GPT to Digital Edify's PostgreSQL CRM.

## Confirmed schema

The inspector found `public.lead`, keyed by `work_item_id`. It joins `public.work_item` for the lead number, creation timestamp, party, and assignee; `public.party` supplies name, phone, email, and assignee name. Status is supported by `lead_status`, `stage`, and `stage_label`. Queries are restricted to tenant `Digital Edify` with `CRM_TENANT_ID`.

## Local setup and testing

Edit `.env`: enter the PostgreSQL password and replace `CRM_API_KEY=CHANGE_ME` with a strong random key from `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Never commit or share `.env`.

```powershell
pip install -r requirements.txt
python inspect_db.py
uvicorn app.main:app --reload --port 8000
```

Test:

```powershell
curl.exe http://localhost:8000/health
curl.exe -H "Authorization: Bearer YOUR_API_KEY" "http://localhost:8000/leads/latest?limit=10"
curl.exe -H "Authorization: Bearer YOUR_API_KEY" "http://localhost:8000/leads/today?limit=20"
curl.exe -H "Authorization: Bearer YOUR_API_KEY" "http://localhost:8000/leads/count/today"
curl.exe -H "Authorization: Bearer YOUR_API_KEY" "http://localhost:8000/leads/search?query=9876543210&limit=20"
curl.exe -H "Authorization: Bearer YOUR_API_KEY" "http://localhost:8000/leads/status/converted?limit=20"
curl.exe -H "Authorization: Bearer YOUR_API_KEY" "http://localhost:8000/leads/assigned/Satya?limit=20"
```

Swagger is at `http://localhost:8000/docs`. Click **Authorize**, enter the bearer key, and invoke an endpoint.

## GitHub and Render Free deployment

1. On GitHub, create an empty repository named `crm-gpt-api`; do not add a README or `.gitignore there.
2. In this directory run `git init`, `git add .`, then verify `.env` is absent with `git status --short` and `git check-ignore .env`.
3. Run `git commit -m "Build CRM GPT bridge"`, `git branch -M main`, `git remote add origin YOUR_REPOSITORY_URL`, and `git push -u origin main`.
4. Sign in to Render, choose **New → Web Service**, connect GitHub, and select the repository.
5. Choose the **Free** instance. Build command: `pip install -r requirements.txt`. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
6. Add `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `CRM_TENANT_ID`, `CRM_TIMEZONE`, and `CRM_API_KEY` as environment variables. Use exactly the same API key later in the GPT Action.
7. Deploy, then copy the service's HTTPS `onrender.com` URL. Replace the placeholder server URL in `openapi-gpt.yaml` with it.

Render Free services can sleep after inactivity, so the first Action call may take approximately a minute. Test the deployment:

```powershell
curl.exe https://YOUR-SERVICE.onrender.com/health
curl.exe -H "Authorization: Bearer YOUR_API_KEY" "https://YOUR-SERVICE.onrender.com/leads/latest?limit=10"
```

## Azure PostgreSQL firewall

If Render reports a database timeout, open the Render service, select **Connect → Outbound**, and copy every displayed CIDR range. In Azure Portal, open the PostgreSQL Flexible Server, select **Networking**, add firewall rules covering those Render outbound ranges, and save. Keep SSL enabled and allow only the listed ranges—do not enable unrestricted public access or `0.0.0.0/0`. Render's shared ranges can change, so recheck the service's Outbound tab if connectivity later fails.

## Custom GPT Action

1. In the GPT editor, open **Actions → Create new action**.
2. Configure authentication as **API key → Bearer** and paste the same `CRM_API_KEY` stored in Render.
3. Paste `openapi-gpt.yaml` into the schema editor and test each operation in Preview.
4. Paste `CUSTOM_GPT_INSTRUCTIONS.md` into the GPT's Instructions.
5. Keep the GPT private unless you also provide the privacy policy required for a public GPT.

## Security guarantees

- All lead routes require Bearer authentication; `/health` is public.
- SQL is predefined, parameterized, read-only, tenant-scoped, and capped at 100 rows.
- No arbitrary SQL or write/schema-changing endpoint exists.
- Responses expose only selected lead/contact fields, not full database rows.
- Database connections require SSL and credentials never appear in source or Action schemas.
