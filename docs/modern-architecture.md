# SocialN modular architecture

## Frontend

- `features/feed`, `profile`, `messages`, `groups`, `settings`: route-level modules.
- `services/api.js`: authenticated HTTP client and media URL resolution.
- `services/auth.js`: session token lifecycle.
- `services/websocket.js`: authenticated realtime connections.
- `hooks`: notification preferences, realtime subscriptions and query helpers.
- TanStack Query owns remote cache; React Router owns URL navigation.

Legacy components remain compatible while they are progressively moved out of
`main.jsx`; new features must be implemented inside the corresponding module.

## Backend

- Alembic is the only schema migration mechanism.
- Redis provides cache, distributed presence, WebSocket pub/sub and rate limits.
- Celery handles thumbnails, notification delivery, email and data exports.
- MinIO provides S3-compatible object storage. `CDN_BASE_URL` can replace its
  public origin without changing stored database URLs.
- Prometheus metrics are exposed at `/metrics`; JSON request logs carry an
  `X-Request-ID`; Sentry is enabled when `SENTRY_DSN` is configured.

## Deployment flow

1. `alembic upgrade head`
2. start the API replicas
3. start one or more Celery workers
4. expose MinIO through a CDN/reverse proxy in production
5. scrape `/metrics` and collect JSON logs
