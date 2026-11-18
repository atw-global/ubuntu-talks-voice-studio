# Persistent Whop company API integration — Ubuntu Talks isiZulu Beginner I

## Purpose
Replace repeated Voni Google sign-ins for routine product media updates with a server-to-server API-key integration. This applies only to the **new hidden** Whop pilot and never publishes, modifies legacy courses, charges customers, or edits the separately owned React storefront.

## Account setup (one-time owner action)
1. In Whop's Ubuntu Talks account Developer area, create a new **account-scoped API key** named `ubuntu-talks-course-factory`.
2. Grant **minimum permissions necessary** to read the Whop pilot product, create/upload public image files, and update its product media (the Whop product update API documents `access_pass:update`). Do not grant payouts or payment actions.
3. In the existing Render `ubuntu-talks-voice-studio-api` service, set environment variable `WHOP_API_KEY` to that key. Set it as a secret in Render only. Never include the value in chat, GitHub, screenshots, frontend code, or the Voni browser.
4. Save and deploy the Render environment. Existing R2 and Azure secrets remain unchanged.

## Prepared backend (do not publish without verification)
- `backend/app/api/endpoints/whop_course_factory.py`
- `GET /api/ubuntu/whop/course-factory/status`: protected by existing StudioGateway; checks key presence, reads and validates product account + hidden visibility; returns only public IDs and status, never token.
- `POST /api/ubuntu/whop/course-factory/cover/apply`: protected by StudioGateway; restricted to `biz_E1ClvLpPiPOdSj` product `prod_EBSCxcpCQvcgI` and the approved 1672x941 PNG. Verifies source bytes and PNG dimensions; creates public Whop gallery file through API; does a signed PUT without leaking API key; waits for ready; patches gallery and verifies readback. It **does not publish the product**.
- Both routes are protected by `STUDIO_BACKEND_GATEWAY_TOKEN`. The integration is NOT publicly callable without the independent gateway credential.
- Approved master cover: `https://cdn.shopify.com/s/files/1/0712/9500/8877/files/ubuntu-talks-everyday-isizulu-beginner-i-hd.png?v=1795026974`.
- Existing blurry gallery file to replace: `file_YrbXTD2X1rWSC`.

## Release plan
1. After key deployment, authenticate via backend-only gateway and run **status**; verify scoped product, hidden state, and gallery.
2. Trigger approved cover replacement **once** via backend privileged operator and verify Whop API readback plus unauthenticated public product page, including correct full resolution.
3. Only after native-speaking QA and Azure commercial rights confirmation: attach the private master to correct Whop lesson `lesn_p61ZUtWXJkEie`, and configure a separate no-login preview for the 85.08-second greeting clip.
4. Test a paid `plan_KhrZ8JGb2YWRt` account entitlement and completion path without making any unauthorized charges.
5. Do not change visibility until owner explicitly approves final release.

## Caveat
Server-side Whop cover code is deployed separately from actual execution. A successful GitHub commit or Render deploy does NOT mean artwork was uploaded or that course audio was approved. The Whop company API key, permissions, and upload path must be tested before any success claim.
