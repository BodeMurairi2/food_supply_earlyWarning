# Deploying HarvestWatch

## On AWS EC2, with HTTPS

We run two containers with Docker Compose: the app, and Caddy in front of it. Caddy gets and renews the Let's Encrypt certificate by itself, and redirects `http://` to `https://`. The app's port 8000 is open to the server only, so the public can only reach it through Caddy.

### 1. Create the server

In the EC2 console, launch an instance:

- **Image:** Ubuntu Server 24.04 LTS
- **Type:** `t3.small` (2 GB of memory). The image build can run out of memory on 1 GB.
- **Storage:** 20 GB
- **Security group:** allow SSH (22) from your IP only, and HTTP (80) and HTTPS (443) from anywhere. Do not open 8000. Port 80 must stay open: Let's Encrypt uses it to check the domain.

Then allocate an **Elastic IP** and associate it with the instance, so the address does not change when the server restarts.

### 2. Point the domain at the server

At your DNS provider, for `bodemurairi.me`:

- Set the **A record** (host `@`) to the Elastic IP.
- **Delete the AAAA record.** Let's Encrypt often tries IPv6 first, and a record pointing to another server makes the certificate fail.

Check it from your computer before continuing. The first command must print only the Elastic IP, and the second must print nothing:

```bash
dig +short A bodemurairi.me
dig +short AAAA bodemurairi.me
```

### 3. Install Docker and the app

```bash
ssh ubuntu@<elastic-ip>

curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit                               # log in again so the group applies

ssh ubuntu@<elastic-ip>
git clone https://github.com/BodeMurairi2/food_supply_earlyWarning.git
cd food_supply_earlyWarning
cp .env.example .env
nano .env                          # add your keys
```

### 4. Start it

```bash
docker compose --profile prod up -d --build
docker compose --profile prod logs -f caddy    # watch for "certificate obtained successfully"
```

The first build takes several minutes. Then open https://bodemurairi.me and https://bodemurairi.me/api/health.

### Updating

```bash
git pull
docker compose --profile prod up -d --build
```

### Good to know

- **Another address:** to use another name, such as `harvestwatch.bodemurairi.me`, point that name at the server and add `DOMAIN=harvestwatch.bodemurairi.me` to a `.env` file next to `docker-compose.yml`, which is the one Compose reads.
- **Certificate problems:** Let's Encrypt limits repeated failures, so fix the DNS or the firewall before restarting many times. `docker compose --profile prod logs caddy` shows the reason.
- **Restarts:** both containers come back by themselves after a crash or a reboot.
- **Cost:** the instance, its storage and the Elastic IP are billed while they exist. Delete all three when the submission is over.

### Run the same setup locally

```bash
DOMAIN=localhost HTTP_PORT=8081 HTTPS_PORT=8443 docker compose --profile prod up -d --build
curl -k https://localhost:8443/api/health
docker compose --profile prod down
```

Caddy uses its own test certificate for `localhost`, so browsers show a warning.

---

## On Render

We deploy the whole app (FastAPI backend and React frontend) as one Docker web service on Render's free plan. The image uses the saved models in `models/` and `food_security_dataset.csv`; nothing is retrained.

### What is in the repo

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the frontend with Node, then runs FastAPI with Python 3.13 on Render's `PORT`. |
| `.dockerignore` | Keeps `.env`, data, notebooks and local environments out of the image. |
| `api/requirements.txt` | App dependencies only. `scikit-learn==1.9.0` must not change, or the saved models will not load. |
| `render.yaml` | Render Blueprint: free web service, Frankfurt region, health check on `/api/health`. |

### Steps

1. **Push the code to GitHub.** The Dockerfile needs these files in the repo: `api/`, `frontend/` (with `package-lock.json`), `models/`, `food_security_dataset.csv`, `Dockerfile`, `.dockerignore`, `render.yaml`. Never commit `.env`.
2. **Create the service.** In Render, choose **New → Blueprint**, connect the GitHub repo and select it. Render reads `render.yaml`.
3. **Enter the secrets** when Render asks for them: `OPENROUTER_API_KEY` and `TAVILY_API_KEY`. The other settings (`HW_LLM_MODEL`, `SEARCH_DEPTH`, AI limits) come from `render.yaml` and can be changed in the dashboard under **Environment**.
4. **Wait for the first build** (about 5-10 minutes). The app is live at `https://harvestwatch.onrender.com` (or the name Render gives). `/api/health` should return `{"status": "ok", ...}`.
5. **Keep it awake.** Free services sleep after 15 minutes without traffic, and the next visit then takes about a minute. We create a free monitor on [UptimeRobot](https://uptimerobot.com) (or [cron-job.org](https://cron-job.org)) that calls `https://<your-app>.onrender.com/api/health` every 10 minutes. The free plan's 750 hours a month cover one service running all month.

Every push to the connected branch redeploys automatically.

### AI request limits

The AI endpoints spend OpenRouter and Tavily credits, so the public app limits them: 5 requests per visitor per hour and 60 per day for the whole app (`HW_AI_LIMIT_PER_HOUR`, `HW_AI_LIMIT_PER_DAY`). Repeated questions are answered from memory and do not count. The memory is cleared when the service restarts.

### Test the image locally

```bash
docker compose up --build      # open http://localhost:8000; stop with docker compose down
```

Render reads `render.yaml`, not `docker-compose.yml`. Compose uses the same `Dockerfile` and reads keys from `.env` if present.

### Notes

- The free plan has 512 MB of memory. The app uses about 350 MB after loading the models and SHAP values.
- Render does not cut off long requests, so AI analyses (up to about 2.5 minutes) complete.
- Free-plan rules change; check https://render.com/docs/free before relying on them.
