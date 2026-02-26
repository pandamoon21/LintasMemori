# LintasMemori

Dashboard organizer Google Photos dengan backend native Python.

## Tujuan v1

- Organizer explorer-style (mirip file explorer): source, albums, media grid, multi-select.
- Core actions dengan guard **preview -> explicit confirm -> commit**.
- Upload via `gpmc` dari dashboard.
- Pipeline wizard `gp_disguise -> gpmc` dari dashboard.
- Advanced drawer untuk seluruh operasi non-core.
- Runtime produksi **tanpa Node sidecar**.

## Stack

- `services/api`: FastAPI + SQLite + worker job queue.
- `apps/web`: React (build ke static assets).
- `workers/python`: async job worker.
- `services/gptk-sidecar`: legacy (tidak dipakai runtime v2).

## API v2 utama

- Accounts/Auth: `/api/v2/accounts*`
- Explorer: `/api/v2/explorer/*`
- Actions preview/commit: `/api/v2/actions/*`
- Upload preview/commit: `/api/v2/uploads/*`
- Pipeline preview/commit: `/api/v2/pipeline/*`
- Jobs + SSE: `/api/v2/jobs*`
- Advanced operations: `/api/v2/advanced/*`

## Menjalankan (Native Launcher)

Prasyarat:

- Python 3.9+ (disarankan 3.11+)
- npm (hanya untuk build frontend static)
- Jika punya banyak Python, set `LM_PYTHON` ke executable Python yang ingin dipakai.

Start stack (1 klik):

```powershell
python start_all.py
```

Stop stack:

```powershell
python stop_all.py
```

Windows double-click:

- `start-all.cmd`
- `stop-all.cmd`

Output:

- API: `http://127.0.0.1:1453`
- UI: `http://127.0.0.1:1453/app`

Catatan:

- Launcher menyimpan PID di `.runtime/processes_py.json`.
- Log proses ada di `.runtime/logs/`.
- Port default launcher adalah `1453` (override dengan env `LM_API_PORT`).

## Menjalankan (Docker Compose)

```bash
docker compose up -d --build
docker compose logs -f
docker compose down
```

URL:

- API + UI static: `http://127.0.0.1:1453` (UI di `/app`)

## Alur penggunaan singkat

1. Buat account di Setup drawer.
2. Set `gpmc auth_data`.
3. Import cookies (paste/file), lalu refresh session.
4. Jalankan **Refresh Index**.
5. Browse explorer, pilih media, jalankan action core (preview -> confirm).
6. Untuk upload langsung, pakai Upload wizard.
7. Untuk disguise + upload, pakai Pipeline wizard.
8. Pantau progres di Task Center.

## Catatan keamanan

- Sesuai asumsi v1: single-user private server-hosted.
- Credential disimpan plain di SQLite lokal.
- Semua aksi massal dirancang lewat preview + explicit confirm.
