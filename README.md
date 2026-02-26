# LintasMemori

Dashboard operator-first untuk mengelola Google Photos dengan integrasi:
- Google Photos Toolkit (melalui gptk sidecar RPC)
- google_photos_mobile_client (gpmc)
- gp_disguise

## Struktur

- `apps/web`: React + Vite dashboard
- `services/api`: FastAPI API (accounts, jobs, SSE)
- `workers/python`: background worker untuk memproses job
- `services/gptk-sidecar`: Node service untuk RPC `batchexecute`

## Jalankan cepat (development)

### Opsi 1: One-click dari root (disarankan)

Windows:

- Double-click `start-all.cmd` dari folder root project.
- Untuk stop semua service, double-click `stop-all.cmd`.

Atau via terminal:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-all.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/stop-all.ps1
```

Catatan:
- `start-all.ps1` akan auto-prepare dependency bila belum ada.
- Mode prepare saja (tanpa start service): `scripts/start-all.ps1 -PrepareOnly`

### Opsi 2: Manual per service

1. API

```powershell
cd services/api
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -e .
uvicorn app.main:app --reload --port 8000
```

2. Worker (terminal baru)

```powershell
cd services/api
. .venv/Scripts/Activate.ps1
python ../../workers/python/worker.py
```

3. GPTK sidecar (terminal baru)

```powershell
cd services/gptk-sidecar
npm install
npm run dev
```

4. Web (terminal baru)

```powershell
cd apps/web
npm install
npm run dev
```

Web akan memakai API default `http://localhost:8000`.

## Fitur yang sudah tersedia

- Multi-account management.
- Job queue + background workers paralel lintas akun.
- Dry-run dan guard konfirmasi untuk operasi destruktif.
- Operation catalog (`/api/operations/catalog`) untuk preset:
  - gpmc ops
  - gp_disguise ops
  - gptk ops (preset RPC method dari GPTK api.ts) + `gptk.rpc_execute` manual.
