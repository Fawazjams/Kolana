# Larpus

## Backend: auth, Docker, CI/CD

- `POST /api/v1/auth/token {"wallet": "..."}` issues a short-lived HS256 JWT. Set `JWT_SECRET`; set `AUTH_REQUIRED=true` to require `Authorization: Bearer <token>` on the transactions, accounts and debts routes (off by default so current clients keep working). Tokens are issued per wallet address without a signature challenge, so treat this as session auth, not proof of key ownership.
- `docker build -t kolana-api backend` builds the API image.
- `.github/workflows/ci.yml` lints, runs the pytest suite (`cd backend && pytest`) and builds the image on every push and PR.
- `.github/workflows/deploy-cloud-run.yml` deploys to GCP Cloud Run after CI passes on `main`; it needs the GCP secrets and variables listed at the top of the file.
