# Hono App — Product Requirements

## User Authentication

### Login
- Users authenticate with email + password
- POST /v1/users/login returns accessToken on success
- Wrong password returns 401 Unauthorized
- Empty email or password returns 400 Bad Request
- Requests without x-api-key header return 401
- CMS admin login requires additional field: resource=admin

### Registration
- Users register with: fullname, email, phone_number, phone_country_code, linkedin
- POST /v1/users/register triggers email verification via Resend
- Duplicate email returns 400/409 error
- Duplicate phone number returns 400/409 error
- Invalid email format returns 422
- Successful registration creates user with status=PENDING

### Password Change
- PUT /v1/users/me/password requires bearer token
- Request body: { current_password, new_password }
- Wrong current_password returns 400/401
- Successful change invalidates old password immediately
- Missing required field returns 400/422

### Email Change
- PUT /v1/users/me/email requires bearer token
- New email must not already be registered
- Duplicate email request returns 409
- Verification email sent to new address after request

## User Account

### Account Information
- GET /v1/users/me/account requires bearer token
- Returns: email, phone_number, phone_code, fullname, nationality
- PUT /v1/users/me/account updates phone_number and phone_code
- Invalid phone_code returns 400 with specific error code

## CMS Admin Flows

### User Approval
- POST /v1/users/:id/approve requires CMS admin token (resource=admin)
- User must be email-verified before approval
- Successful approval changes status PENDING → APPROVED
- approved_at timestamp is set on approval

### User Rejection
- POST /v1/users/:id/reject requires CMS admin token
- Request body: { reason: string }
- Successful rejection changes status to REJECTED
- Rejecting nonexistent user returns 404/400

## Onboarding
- PUT /v1/users/onboarding requires bearer token
- Collects: professional title, company, country, city, industries
- Completes user profile post-registration

## Feed & Search
- GET /v1/search/posts requires bearer token
- Query param: q (search string)
- Empty query returns 200 or 400 depending on API config
- Response time target: < 3000ms
