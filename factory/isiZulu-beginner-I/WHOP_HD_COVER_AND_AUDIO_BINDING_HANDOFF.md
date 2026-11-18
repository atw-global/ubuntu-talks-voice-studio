# Everyday isiZulu Beginner I — Approved HD Whop cover and sample binding handoff

Updated 2026-11-18. Keep the existing new course and product hidden. Do not create a duplicate and do not touch legacy courses or the other agent's custom storefront code.

## Approved cover
- Original approved hero: **Ubuntu Talks — Everyday isiZulu | Beginner I**.
- Original 1672×941 PNG available in Canva media asset `MAHbSkFb9Ro`.
- Permanent full-size CDN transfer source (tested from inside Whop browser): `https://cdn.shopify.com/s/files/1/0712/9500/8877/files/ubuntu-talks-everyday-isizulu-beginner-i-hd.png?v=1795026974`.
- Size 2,637,013 bytes; actual image dimensions 1672×941; MIME image/png.
- Destination: existing Whop product `prod_EBSCxcpCQvcgI`, NOT a new product.
- Current Whop gallery source is a blurry Canva 200px thumbnail (`file_YrbXTD2X1rWSC`) and **has not been replaced**. A Whop admin session is required for media upload.
- Voni default browser Whop authentication expired. A private same-profile OAuth login handoff link must be used. Do not send or request passwords or MFA codes in chat.

## Exact browser-upload steps (only when Whop admin is authenticated)
1. Open `https://whop.com/dashboard/biz_E1ClvLpPiPOdSj/products/prod_EBSCxcpCQvcgI/`.
2. Select **Add media** in the product editor. The previous editor used `input[type=file][name=gallery]` and a **Use image** confirmation.
3. Fetch the permanent CDN full resolution image in the Whop page and create a browser File (not a reduced Canva thumbnail). If using Voni evaluation, one may use `fetch(url).blob()`, `new File([blob], "everyday-isizulu-beginner-i-hd.png", {type:"image/png"})`, `new DataTransfer()`, assign the selected `File` to the gallery file input and dispatch a bubbling `change` event. Confirm the upload UI actually receives the image.
4. Click **Use image**, then **Save product**. Read back the product gallery with Whop API, confirm its new media file ID differs from `file_YrbXTD2X1rWSC`.
5. Open the visitor-facing product page in an unauthenticated browser profile and confirm the hero is visually sharp. Only remove the old thumbnail after new cover is confirmed and the presentation is correct.
6. Keep existing product visibility hidden; keep $29.99 one-time plan `plan_KhrZ8JGb2YWRt` visible as an offer. Do not expose the existing free testing plan on the public sales page.
7. Use matching art for Whop course/lesson thumbnail and checkout where native Whop supports it. Do not invent an image API shape; use authenticated native image attachment UI.

## Audio and safe media gate
- Existing approved 139-cue Azure Lesson 1 master: `r2://ubuntu-talks-instructor-masters/courses/zu/beginner-i/lesson-01/v1/master.mp3`, 7,401,068 bytes, SHA256 `ef9078dcb41fa0a43b4f2ca0c40d364ae2be66dbc13fe832ef1d117a0ea32a9a`.
- Existing 85.08-second greeting excerpt: `r2://ubuntu-talks-instructor-masters/courses/zu/beginner-i/lesson-01/v1/sample-greetings-85s-qa.mp3`, 1,021,292 bytes, SHA256 `d8a87dde1a3e92c3e6727e8dab2106eac1739a02e34597a1f6da6cb73640c7e0`.
- R2 readback and assembly technically PASS. Neither file has a public URL or Whop media attachment.
- Native-speaker pronunciation, pacing and cultural-register QC plus commercial Azure rights are pending. Do not publish the public MP3 or market final completed lesson before these gates pass.
- Lesson 1 ID `lesn_p61ZUtWXJkEie`, course `cors_EYwVx1BwLtuXB`, Courses experience `exp_N2y6r4fBZQ7qOv`. Whop lesson includes seven-stage written content; audio attachment remains missing. Other lessons are placeholders; no premature publication.
- After QA approvals: issue a dedicated public, limited-scope 85-second sample URL; embed it on the product sales page without login, then attach full master securely as learner-only Whop media. Do not expose raw private master URL.
- Perform logged-out preview and actual paid learner access test before launch; avoid spending live funds just for testing unless user authorizes payment.
