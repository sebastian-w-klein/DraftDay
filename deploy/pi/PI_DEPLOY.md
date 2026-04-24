# Raspberry Pi deployment (Docker Compose)

This deploy path runs DraftDay entirely on your Pi:

- Postgres
- FastAPI API
- Next.js frontend
- Caddy reverse proxy (single public port)

## 1) Pi prerequisites

- Raspberry Pi OS 64-bit (Bookworm recommended)
- Docker + Compose plugin installed
- Git installed

Install Docker quickly:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

## 2) Clone repo on the Pi

```bash
git clone <your-repo-url> DraftDay
cd DraftDay
```

## 3) Configure environment

```bash
cp deploy/pi/.env.pi.example deploy/pi/.env.pi
```

Set at least:

- `POSTGRES_PASSWORD` to a strong value
- `PUBLIC_HTTP_PORT` if 80 is unavailable

## 4) Build and run

From repo root:

```bash
docker compose --env-file deploy/pi/.env.pi -f deploy/pi/docker-compose.pi.yml up -d --build
```

## 5) Run migrations

```bash
docker compose --env-file deploy/pi/.env.pi -f deploy/pi/docker-compose.pi.yml exec api alembic upgrade head
```

## 6) Verify

- API health: `http://<pi-ip>/health`
- API docs: `http://<pi-ip>/docs`
- Frontend: `http://<pi-ip>/`

## Useful commands

Show running services:

```bash
docker compose --env-file deploy/pi/.env.pi -f deploy/pi/docker-compose.pi.yml ps
```

Follow logs:

```bash
docker compose --env-file deploy/pi/.env.pi -f deploy/pi/docker-compose.pi.yml logs -f
```

Restart only API:

```bash
docker compose --env-file deploy/pi/.env.pi -f deploy/pi/docker-compose.pi.yml up -d --build api
```

Stop stack:

```bash
docker compose --env-file deploy/pi/.env.pi -f deploy/pi/docker-compose.pi.yml down
```

## Public internet access (optional)

If you want external access without opening router ports, use Cloudflare Tunnel and point it at `http://localhost:<PUBLIC_HTTP_PORT>`.
