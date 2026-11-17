# Vast.ai integration — read-only mode

Ubuntu Talks Voice Studio provides `GET /api/ubuntu/vast/status` in its private API backend.

The route checks only `GET https://console.vast.ai/api/v0/users/current/` with `Authorization: Bearer $VAST_API_KEY`. The result contains a `connected` boolean and, if authenticated, an account identifier. It does **not** create any GPU instances or report a balance.

## Configure

1. Store `VAST_API_KEY` **only** in the Render service `ubuntu-talks-voice-studio-api` environment. Never place it in GitHub or the frontend service.
2. Use a restricted Vast.ai key permitting user-read and instances-read, with instance-write, billing-write and all other write scopes disabled for this connectivity test.
3. Keep GPU provisioning code disabled. Setting `VAST_API_KEY` alone is not enough for actual TTS inference and never launches GPUs.
4. Visit the studio URL with its owner credentials and call the backend's `/api/ubuntu/vast/status` route once the authenticated frontend proxy has been enabled.
5. A true result verifies only API authentication. Selecting and deploying a commercially licensed African-language TTS model is a separate validation.

## Backend security
The public Render API origin is protected by a different random gateway token shared only with the Nginx frontend proxy. The backend refuses all HTTP and WebSocket requests without that token, except for the `/health` probe.

## Important deployment prerequisites
- OpenSpeakers database migrations need the dedicated PostgreSQL credentials configured in the backend.
- Redis/Valkey hostname and port must point to the dedicated internal queue. Free queue has no persistence.
- `ENVIRONMENT=staging`, `SECRET_KEY` and `STUDIO_BACKEND_GATEWAY_TOKEN` are required.
- Frontend requires matching `STUDIO_BACKEND_GATEWAY_TOKEN` and `STUDIO_BACKEND_URL=https://ubuntu-talks-voice-studio-api.onrender.com`.
- The frontend entrypoint enables backend proxy only if all gateway variables are populated. Otherwise the existing API HTTP 503 preview stays in effect.
- No fee-bearing GPUs are created by this deployment.
