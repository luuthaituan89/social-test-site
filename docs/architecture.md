# SocialN Architecture

```text
React/Vite
    |
    | REST / JSON + multipart
    v
FastAPI
    |-- JWT authentication
    |-- Posts / likes / comments / shares
    |-- Users / profile / privacy
    |-- Friends / blocking
    |-- Password settings
    |-- WebSocket chat
    |
    v
SQLAlchemy
    |
    v
MySQL 8
```

## Main tables

- users
- friendships
- blocks
- posts
- likes
- comments
- conversations
- messages

## Privacy rule

`public`: any non-blocked authenticated user can see it.

`friends`: only accepted friends can see it.

`only_me`: only the author can see it.

## Production checklist

- Add Alembic migrations.
- Use Redis for WebSocket presence/pub-sub when horizontally scaling.
- Store uploads in S3/MinIO.
- Add rate limiting and CSRF strategy if cookie auth is introduced.
- Add refresh token rotation and device/session management.
- Add content moderation and upload scanning.
- Add pagination/cursors instead of fixed feed limits.
- Add notifications.
- Add automated tests and CI.
