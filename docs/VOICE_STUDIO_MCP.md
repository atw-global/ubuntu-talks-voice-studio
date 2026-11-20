# Voice Studio MCP

Versioned Streamable HTTP endpoint on the existing API service `ubuntu-talks-voice-studio-api` (`srv-dbttr1psrm7s73e17im0`). No new recording service, database, or course is created.

The route is deployed. An unauthenticated `POST` returns HTTP 401 with `WWW-Authenticate`. ChatGPT custom connectors can use OAuth only, so this service also publishes OAuth 2.1 discovery on the same origin. A connector is connected only after the owner approves it and `studio_health` succeeds with the issued token.

## Endpoint

`https://ubuntu-talks-voice-studio-api.onrender.com/api/ubuntu/mcp/v1`

Use the API origin. The website `https://ubuntu-talks-voice-studio.onrender.com` is nginx basic auth and its proxy clears `Authorization`, so it is not the MCP connection.

Transport: Streamable HTTP. `POST` a single JSON-RPC message with `Accept` of `application/json`. `GET` returns 405 because the server does not open an SSE stream. `DELETE` closes the session. Send `MCP-Session-Id` after `initialize`.

The internal header `X-Voice-Studio-Internal-Key` is not accepted as an MCP credential and is not sent to the client.

## Authentication

Send `Authorization: Bearer <token>`. The API stores only the SHA-256 of each token in `ubuntu_mcp_credentials` on the existing Postgres database. Audit rows go to `ubuntu_mcp_audit` and record the credential id, tool, and result. They do not record the token.

Set the token values on the API service in Render. Do not put them in GitHub, in this repository, or in a browser cookie.

| Environment variable | Profile | Rotation |
| --- | --- | --- |
| `UBUNTU_MCP_BOOTSTRAP_TOKEN` | `read`, `verify` | Change the value. The previous bootstrap hash is revoked on the next request. |
| `UBUNTU_MCP_READ_TOKENS` | one `read`, `verify` credential per comma-separated token | Remove a token from the list to revoke it. |
| `UBUNTU_MCP_ADMIN_TOKEN` | all scopes, including `admin` | Change the value to revoke the previous admin hash. |

A browser `Origin` is rejected unless it is `https://chatgpt.com`, `https://chat.openai.com`, the API origin, or listed in `UBUNTU_MCP_ALLOWED_ORIGINS`. Machine clients omit `Origin`.

## ChatGPT OAuth

ChatGPT’s custom MCP form offers OAuth or no authentication. Use OAuth. The connector URL is the MCP endpoint above. Do not select “No authentication”.

The API origin is the authorization server. These routes are public and do not accept the gateway token or the bootstrap token:

| URL | Purpose |
| --- | --- |
| `/.well-known/oauth-protected-resource/api/ubuntu/mcp/v1` | Protected-resource metadata. The 401 `resource_metadata` parameter points here. |
| `/.well-known/oauth-authorization-server` | Issuer, authorization, token, registration, and revocation endpoints. PKCE `S256` only. |
| `POST /oauth/register` | Dynamic client registration for an allowlisted redirect. The issued client is a public PKCE client even if the request names `private_key_jwt`. |
| `GET` and `POST /oauth/authorize` | Owner consent. No code is issued unless the owner password matches. |
| `POST /oauth/token` | Authorization code or refresh token, public client (`none`). |
| `POST /oauth/revoke` | Revoke an access or refresh token. The response is empty. |

Allowed redirects are `https://chatgpt.com/connector_platform_oauth_redirect` and `https://chatgpt.com/connector/oauth/{callback_id}`. A client metadata document is accepted only at `https://chatgpt.com/oauth/client.json` or `https://chatgpt.com/oauth/{callback_id}/client.json`. The server fetches that HTTPS URL itself, refuses redirects, and checks `client_id` and `redirect_uris`.

Every issued token has scopes `read` and `verify`, including when the request asks for more. Access tokens expire after one hour. Refresh tokens expire after 30 days and are replaced on use; the previous refresh token stops working. Sessions still expire after 12 hours. Authorization, token, and revocation events are written to `ubuntu_mcp_audit` without the token or the owner password.

Set these names on `ubuntu-talks-voice-studio-api` (`srv-dbttr1psrm7s73e17im0`) only. Do not put the values in GitHub, the frontend service, or chat.

| Environment variable | Required | Effect |
| --- | --- | --- |
| `UBUNTU_MCP_OAUTH_OWNER_SECRET` | yes, before a client can connect | Consent password. If it is unset, authorization fails closed. Use a new value, different from the gateway token and the bootstrap token. |
| `UBUNTU_MCP_OAUTH_REVOKED_BEFORE` | no | ISO-8601 timestamp. Access and refresh tokens issued at or before that time are rejected. Set it to the current UTC time to revoke every OAuth token. |
| `UBUNTU_MCP_OAUTH_REDIRECTS` | no | Extra exact redirect URIs, comma-separated. Leave unset for ChatGPT. |
| `UBUNTU_MCP_PUBLIC_ORIGIN` | no | Defaults to `https://ubuntu-talks-voice-studio-api.onrender.com`. Set it only if the public API origin changes. |

Owner steps after this commit is deployed:

1. On the API service, set `UBUNTU_MCP_OAUTH_OWNER_SECRET`. Save and let the service restart. Do not set `UBUNTU_MCP_RECORDING_ENABLED`, `UBUNTU_MCP_REPLACE_ENABLED`, or `UBUNTU_MCP_WHOP_STAGE_ENABLED`.
2. In ChatGPT, add a custom connector with the MCP URL and OAuth authentication.
3. When the consent page opens, confirm the client and the `chatgpt.com` redirect, then enter the owner password. Approve only a page you opened yourself.
4. Ask the connector to call `studio_health`. The result `ok: true` is the connection check. A token that asks for `publish` is denied.

Changing `UBUNTU_MCP_OAUTH_OWNER_SECRET` does not revoke tokens already issued. To revoke them, call `POST /oauth/revoke` with the token, or set `UBUNTU_MCP_OAUTH_REVOKED_BEFORE`.

## Authorization matrix

| Scope | Tools | Default read credential |
| --- | --- | --- |
| `read` | `studio_health`, `list_courses`, `list_lessons`, `get_recording_status`, `get_master_metadata`, `get_audio_manifest`, `get_cue_alignment`, `get_r2_archive_status`, `get_whop_attachment_status` | yes |
| `verify` | `verify_master_sha256` | yes |
| `export` | `export_verified_master` | no |
| `record` | `run_recording`, `replace_recording` | no |
| `attach` | `stage_audio_for_whop` | no |
| `publish` | `publish_course` | no |

`export_verified_master` returns a receipt only when the bytes were read, decoded, contain 139 cues, and match SHA-256 `ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a`. It does not return the audio or a public URL.

`run_recording` stays off unless `UBUNTU_MCP_RECORDING_ENABLED=true`. Even then it does not call Azure. `replace_recording` always refuses. `stage_audio_for_whop` stays off unless `UBUNTU_MCP_WHOP_STAGE_ENABLED=true`, and then still refuses while the release gates are open. `publish_course` refuses while any of these gates are open: verified master SHA-256, native-speaker sign-off, commercial-use permission, Mrs Ubuntu introduction approval, enrolled-learner test. The Whop course stays hidden.

## Client configuration

Cursor, or another Streamable HTTP client, connects to the endpoint above. The bearer token comes from the client secret store, matching one Render variable. Example shape, with the token supplied outside the repository:

```json
{
  "mcpServers": {
    "ubuntu-talks-voice-studio": {
      "url": "https://ubuntu-talks-voice-studio-api.onrender.com/api/ubuntu/mcp/v1",
      "headers": {
        "Authorization": "Bearer ${UBUNTU_MCP_BOOTSTRAP_TOKEN}"
      }
    }
  }
}
```

Cursor can keep using a bearer token from `UBUNTU_MCP_BOOTSTRAP_TOKEN` or `UBUNTU_MCP_READ_TOKENS`. ChatGPT uses the OAuth section above instead of a pasted bearer token. Do not reuse a browser login.

## Voni

Voni remains the browser for interactive review and owner approval. A browser session is not an MCP credential. This repository does not register a Voni connector. If Voni can add a remote MCP server, point it at the same URL with its own read token.

## Authenticated call in this workspace

An HTTP `initialize` and `tools/call` for `verify_master_sha256` succeeded against this code with a local read credential. The master object was not read:

- `available`: false
- `sha256`: null
- `duration_seconds`: null
- `cue_count`: null
- `decoded`: false
- `alignment_status`: `not_checked`
- `historical_reference_matches`: false
- `regenerated`: false
- `reason`: `database_unreachable`
- `object_key`: `courses/zu/beginner-i/lesson-01/v1/master.mp3`

This workspace has no connection to `ubuntu-voice-studio-db` and no `UBUNTU_R2_ACCESS_KEY_ID`. Orders 4, 5, and 6 in the source manifest are `Sanibonani.`, `Unjani?`, and `Ninjani?`. Their timing status is `manual_review`. No audio was generated.

## Owner actions before the endpoint can verify the master

1. Deploy this commit to the existing service `srv-dbttr1psrm7s73e17im0`. Do not create a service.
2. On that service, set `UBUNTU_MCP_BOOTSTRAP_TOKEN` to a new random value. Keep it out of GitHub and out of the frontend service.
3. Repeat a `tools/call` for `verify_master_sha256` with that token. A result is a verification only when `available` is true and `sha256`, `duration_seconds`, `decoded`, and `cue_count` come from the bytes.
4. Leave `UBUNTU_MCP_RECORDING_ENABLED`, `UBUNTU_MCP_REPLACE_ENABLED`, and `UBUNTU_MCP_WHOP_STAGE_ENABLED` unset.
