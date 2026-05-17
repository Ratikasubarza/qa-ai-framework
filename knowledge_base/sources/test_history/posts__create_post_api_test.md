# Test file: features/posts/steps/api/create_post_api_test.py

Suite: Posts API | Endpoint: POST /v1/posts
Tests: TC-POST-API-001 through TC-POST-API-016 (16 tests)
Requires: post_token fixture (authenticated user Bearer token)

## Test IDs covered
- TC-POST-API-001 | Smoke | Create post with valid minimal data → 200/201, code=OK, has "id"
- TC-POST-API-002 | Smoke | Create post with S3 media URL → 200/201, code=OK
- TC-POST-API-003 | Functional | Create anonymous post → is_anonymous=true in response
- TC-POST-API-004 | Functional | Create post with 3 topic_ids → topics array not empty
- TC-POST-API-005 | Smoke | Response schema: id, content, visibility, is_anonymous, topics, engagement, created_at
  - engagement: like_count=0, comment_count=0, repost_count=0
- TC-POST-API-006 | Boundary | visibility=EVERYONE accepted
- TC-POST-API-007 | Security | No auth token → 401
- TC-POST-API-008 | Security | No x-api-key → 401
- TC-POST-API-009 | Negative | Empty topic_ids → 422, code=NOKUNPROC, error contains "topic"
- TC-POST-API-010 | Negative | Empty content → 400/422
- TC-POST-API-011 | Negative | Missing content field → 400/422
- TC-POST-API-012 | Negative | Invalid visibility → 400/422
- TC-POST-API-013 | Negative | Missing topic_ids field → 400/422
- TC-POST-API-014 | Boundary | 5000-char content → 200/201/400/422 (documents limit)
- TC-POST-API-015 | Boundary | Empty body {} → 400/422
- TC-POST-API-016 | Performance | Response time under 3000ms (CreatePostTestData.MAX_RESPONSE_MS)

## Key test data (CreatePostTestData)
- SUCCESS_CODE = "OK"
- VALIDATION_CODE = "NOKUNPROC"
- VISIBILITY_INVALID = "INVALID_VISIBILITY"
- MAX_RESPONSE_MS = 3000
- REQUIRED_RESPONSE_KEYS = {"id", "content", "visibility", "is_anonymous", "topics", "engagement", "created_at"}
- REQUIRED_ENGAGEMENT_KEYS = {"like_count", "comment_count", "repost_count"}

## CreatePostPayload builders
- .valid() — minimal valid post with 1 topic
- .with_media() — includes S3 media URL
- .anonymous() — is_anonymous=True
- .multiple_topics() — 3 topic_ids
- .with_visibility(v) — sets visibility field
- .no_topics() — empty topic_ids []
- .empty_content() — content=""
- .long_content(n) — content of n chars
- .without(field) — removes a field from dict
