# Deploying HarvestWatch on Render

We deploy the whole app (FastAPI backend and React frontend) as one Docker web service on Render's free plan. The image uses the saved models in `models/` and `food_security_dataset.csv`; nothing is retrained.

## What is in the repo

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the frontend with Node, then runs FastAPI with Python 3.13 on Render's `PORT`. |
| `.dockerignore` | Keeps `.env`, data, notebooks and local environments out of the image. |
| `api/requirements.txt` | App dependencies only. `scikit-learn==1.9.0` must not change, or the saved models will not load. |
| `render.yaml` | Render Blueprint: free web service, Frankfurt region, health check on `/api/health`. |

## Steps

1. **Push the code to GitHub.** The Dockerfile needs these files in the repo: `api/`, `frontend/` (with `package-lock.json`), `models/`, `food_security_dataset.csv`, `Dockerfile`, `.dockerignore`, `render.yaml`. Never commit `.env`.
2. **Create the service.** In Render, choose **New → Blueprint**, connect the GitHub repo and select it. Render reads `render.yaml`.
3. **Enter the secrets** when Render asks for them: `OPENROUTER_API_KEY` and `TAVILY_API_KEY`. The other settings (`HW_LLM_MODEL`, `SEARCH_DEPTH`, AI limits) come from `render.yaml` and can be changed in the dashboard under **Environment**.
4. **Wait for the first build** (about 5-10 minutes). The app is live at `https://harvestwatch.onrender.com` (or the name Render gives). `/api/health` should return `{"status": "ok", ...}`.
5. **Keep it awake.** Free services sleep after 15 minutes without traffic, and the next visit then takes about a minute. We create a free monitor on [UptimeRobot](https://uptimerobot.com) (or [cron-job.org](https://cron-job.org)) that calls `https://<your-app>.onrender.com/api/health` every 10 minutes. The free plan's 750 hours a month cover one service running all month.

Every push to the connected branch redeploys automatically.

## AI request limits

The AI endpoints spend OpenRouter and Tavily credits, so the public app limits them: 5 requests per visitor per hour and 60 per day for the whole app (`HW_AI_LIMIT_PER_HOUR`, `HW_AI_LIMIT_PER_DAY`). Repeated questions are answered from memory and do not count. The memory is cleared when the service restarts.

## Test the image locally

```bash
docker compose up --build      # open http://localhost:8000; stop with docker compose down
```

`docker-compose.yml` is for local runs only (Render reads `render.yaml`). It uses the same `Dockerfile`, reads keys from `.env` if present, and caps memory at 512 MB like Render's free plan.

## Notes

- The free plan has 512 MB of memory. The app uses about 350 MB after loading the models and SHAP values.
- Render does not cut off long requests, so AI analyses (up to about 2.5 minutes) complete.
- Free-plan rules change; check https://render.com/docs/free before relying on them.
