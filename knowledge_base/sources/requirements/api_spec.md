# Hono API Spec — Staging (api-dev.thehono.com)

Auth: every request needs `x-api-key` header. Authenticated endpoints also need `Authorization: Bearer <token>`.

## POST /v1/users/register
Required: fullname, email, phone_number, phone_country_code, linkedin
200 = success | 400 = validation | 422 = duplicate email or phone

## POST /v1/users/login
Required: email, password. Optional: resource="admin" for CMS.
200 + accessToken | 401 = invalid credentials

## GET /v1/users/me
Auth required. Returns: id, name, email, role, phone, onboarding_completed_at
401 = unauthorized

## GET /v1/users/me/account
Auth required. Returns: email, phone_number, phone_code, phone_country_iso, nationality (nullable)
Known bug: nationality key omitted in some responses [DEV-BUG-002]

## PUT /v1/users/me/account
Required: email, phone_number, phone_code. Optional: nationality_id
200 = saved | 400 = invalid | 422 = invalid phone code

## PUT /v1/users/me/email
Required: new_email
200 = saved | 422 = already exists

## GET /v1/users/verify-email?code=...
200 = updated | 410 = expired | 422 = invalid code
Known bug: returns 404 on staging [DEV-BUG-001]

## PUT /v1/users/me/password
Required: current_password, new_password
200 = changed | 400 = invalid current | 401 = unauthorized | 422 = invalid payload

## GET /v1/users (CMS)
Admin auth. Params: page, size, orderBy, order, status(1=PENDING,2=APPROVED,3=REJECTED)
200 = list | 401 = unauthorized

## POST /v1/users/{id}/approve (CMS)
Admin auth. 200 = approved | 401 | 404 = not found
Known bug: approves unverified users [BUG-007]

## POST /v1/users/{id}/reject (CMS)
Admin auth. Optional body: reason
200 = rejected | 401 | 404 = not found
Known bugs: approve-then-reject ambiguous [DEV-BUG-003]; double reject idempotency [DEV-BUG-004]

## PUT /v1/users/onboarding
Auth required. Fields: full_name, current_role, company_organisation, nationality_id, city_id,
industry_ids (1–2), business_area_ids (2–5), personal_interest_ids (2–5), social_cause_ids (2–5)
200 + onboarding_completed_at | 401

## POST /v1/posts
Auth required (Bearer token). Required: content (string), topic_ids (array, min 1), visibility.
Optional: is_anonymous, media (array of URLs), mentions.
200 = OK code + post object with id, content, visibility, is_anonymous, topics, engagement, created_at
engagement: like_count, comment_count, repost_count, view_count (all 0 on creation)
422 NOKUNPROC = empty topics, mention disabled by user
400/422 = empty content, missing fields, invalid visibility
401 = no token or no api-key
