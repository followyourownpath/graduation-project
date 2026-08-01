# VPS production deployment

The Bread application is hosted at `https://aimeshlabs.au/bread`.

## Architecture

- Host Nginx terminates HTTPS and owns the `/bread` path.
- The frontend container listens on `127.0.0.1:3001` only.
- The backend container listens on `127.0.0.1:5001` only.
- Nginx forwards `/bread/api/*` to the Flask `/api/*` routes.
- Supabase Auth, Postgres, and Storage remain in the team's Supabase Cloud project.
- Production credentials remain in `/home/interndev/bread/.env` on the VPS.

## Prerequisites

- The deployment user belongs to the `docker` group.
- Docker Engine, Docker Compose, Git, and curl are installed.
- The VPS can read the GitHub repository using a read-only deploy key.
- An administrator has installed `deploy/nginx-bread.conf` in the existing HTTPS server block.
- Cloudflare has a proxied DNS record for `aimeshlabs.au` pointing to the VPS.
- Supabase Auth allows the `https://aimeshlabs.au/bread` callback URLs.

## One-time VPS bootstrap

Clone the repository as the deployment user:

```bash
cd /home/interndev
git clone git@github.com:unsw-cse-comp99-3900/capstone-project-26t2-9900-w19b-bread.git bread
cd bread
git checkout main
```

Create the production environment file without committing it:

```bash
cp deploy/production.env.example .env
chmod 600 .env
```

Populate `.env` with the existing Supabase and Azure credentials. Validate the Nginx configuration before reloading it:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Manual deployment

```bash
cd /home/interndev/bread
git fetch origin main
git checkout main
git pull --ff-only origin main
./deploy/deploy.sh
```

The script validates the Compose configuration, rebuilds both images, starts the containers, and checks the backend and frontend health endpoints.

## GitHub Actions deployment

The `Deploy production` workflow is intentionally manual. Run it from the Actions tab and select the `main` branch. The workflow refuses to deploy another branch, runs both test suites, validates the Compose file, and then deploys through the `production` environment.

Pull requests that change application or deployment files also run `Production image CI`, which builds both production images before merge.

Configure these production environment secrets in GitHub:

| Secret | Purpose |
| --- | --- |
| `VPS_HOST` | VPS hostname or IP address |
| `VPS_USER` | Deployment account, normally `interndev` |
| `VPS_SSH_PRIVATE_KEY` | Private key dedicated to GitHub Actions deployment |
| `VPS_KNOWN_HOSTS` | Verified SSH host-key entry for the VPS |

Configure required reviewers on the GitHub `production` environment if the repository plan supports deployment protection rules. The VPS application secrets stay in `.env`; they are not copied into GitHub Actions.

## Verification and troubleshooting

```bash
curl http://127.0.0.1:5001/api/v1/health
curl -I http://127.0.0.1:3001/bread/login
curl -I https://aimeshlabs.au/bread/login
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 backend frontend
```

If a deployment fails, check out the last known-good commit on the VPS and run `./deploy/deploy.sh` again.
