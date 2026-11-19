# Ubuntu Talks Voice Studio — deployment record

## Current stage: preview only

This repository is an ATW-Global fork of [OpenSpeakers](https://github.com/attevon-llc/OpenSpeakers), licensed AGPL-3.0-only.

The dedicated Render service deploys **only** the real OpenSpeakers Svelte frontend from `frontend/Dockerfile.render`. It is password-protected with Nginx Basic Authentication. Both `/api/` and `/ws/` intentionally return HTTP 503 until the backend and GPU worker are separately deployed and access-controlled. Thus UI availability is **not** TTS readiness.

Render service configuration:
- Runtime: Docker
- Docker context: `frontend`
- Dockerfile path: `frontend/Dockerfile.render`
- Plan: free staging
- Port: `10000`
- Required secret environment variables: `STUDIO_AUTH_USER`, `STUDIO_AUTH_PASSWORD`.
- Do **not** add `VAST_API_KEY` to the static frontend container.

## Next production milestones

1. Design production identity/access (Cloudflare Access or another proper SSO solution); Basic Auth is limited preview protection.
2. Set up managed PostgreSQL and Redis, or a securely hosted OpenSpeakers stack. Do not assume existing Ubuntu Supabase schema is compatible with OpenSpeakers migrations.
3. Deploy the real FastAPI backend with database and queue connectivity; configure public /api/ and /ws/ routing only after authentication and authorization are verified.
4. Implement a **separate** Vast.ai GPU-worker adapter. OpenSpeakers does not natively dispatch its Celery jobs to Vast.ai API merely because `VAST_API_KEY` is set. Keep instance creation disabled by default and enforce cost controls.
5. Validate model/weights/dataset/voice licenses and native-speaker isiZulu quality before commercial use.
6. Connect Ubuntu course source and Cloudflare R2 after the TTS chain passes tests; preserve script approval gates.

## Safety
- Never store Vast API credentials or studio passwords in Git.
- Never deploy backend unauthenticated on the public internet.
- No GPU instances, paid resources, or audio generation are initiated by this staging configuration.

## 2026-11-16/17 deployment inventory

The following *independent* ATW-Global Render resources have been created in Oregon:

- Frontend: `ubuntu-talks-voice-studio` (service `srv-dbtql9ifngtc739uek90`), URL `https://ubuntu-talks-voice-studio.onrender.com`; public route protected by Nginx Basic Auth.
- Backend: `ubuntu-talks-voice-studio-api` (service `srv-dbttr1psrm7s73e17im0`), URL `https://ubuntu-talks-voice-studio-api.onrender.com`; protects API and websocket endpoints with `X-Voice-Studio-Internal-Key` and includes `GET /health`.
- PostgreSQL 17: `ubuntu-voice-studio-db` (`dpg-dbttmmek1f9s739nrs00-a`), free tier, expires **2026-12-17** unless upgraded.
- Redis-compatible Valkey 8: `ubuntu-voice-studio-queue` (`red-dbttmmrm8hqs73dhbhi0`), free tier, 25 MB RAM, non-persistent.
- The backend uses its own DB login and key; no existing Ubuntu curriculum database was migrated or altered.
- API origin requires a secret gateway token; the frontend injects the matching token in Nginx, never into browser JavaScript.
- `VAST_API_KEY` is **not yet verified present** on the dedicated backend. It must be stored only in backend environment, then validated using the read-only `/api/ubuntu/vast/status` route.
- GPU worker is **not deployed**. On the backend `VOICE_STUDIO_GENERATION_ENABLED` defaults to false, which blocks mutating API endpoints rather than enqueueing jobs without workers.
- Do not assume model registration implies runnable voices: no GPU checkpoint or native-language QA is complete.

All plans above were created as free test resources. Backend/preview may restart or spin down. Do not enable generation until commercial voice licenses, compute pricing, storage, and audio persistence are verified.

## MCP client credentials

The versioned endpoint is `POST /api/ubuntu/mcp/v1` on the existing API origin. It does not use `STUDIO_BACKEND_GATEWAY_TOKEN`. Machine credentials are environment variables on `ubuntu-talks-voice-studio-api` only:

- `UBUNTU_MCP_BOOTSTRAP_TOKEN` — read and verify
- `UBUNTU_MCP_READ_TOKENS` — additional read and verify credentials, comma-separated
- `UBUNTU_MCP_ADMIN_TOKEN` — separate admin credential; publication remains gated

Do not commit the values. The specification is `docs/VOICE_STUDIO_MCP.md`.

ChatGPT OAuth uses a separate owner secret on the same API service. Set `UBUNTU_MCP_OAUTH_OWNER_SECRET` there after this OAuth commit is deployed. Do not copy the gateway token or `UBUNTU_MCP_BOOTSTRAP_TOKEN` into that variable, and do not add it to the frontend service. The connector URL remains `https://ubuntu-talks-voice-studio-api.onrender.com/api/ubuntu/mcp/v1` with OAuth selected. The consent page is served by this API. No new Render service is required.
