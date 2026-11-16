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
