from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://socialn:socialn@db:3306/socialn"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 15
    refresh_token_days: int = 30
    auth_cookie_secure: bool = False
    auth_encryption_key: str = ""
    frontend_url: str = "http://localhost:5173"
    require_verified_email: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "SocialN <no-reply@socialn.local>"
    smtp_use_tls: bool = True
    cors_origins: str = "http://localhost:5173"
    upload_dir: str = "/app/uploads"
    giphy_api_key: str = ""
    redis_url: str = "redis://redis:6379/0"
    storage_backend: str = "local"
    s3_endpoint_url: str = "http://minio:9000"
    s3_public_url: str = "http://localhost:9000/socialn-media"
    s3_access_key: str = "socialn"
    s3_secret_key: str = "socialn-development"
    s3_bucket: str = "socialn-media"
    cdn_base_url: str = ""
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    sentry_dsn: str = ""
    log_level: str = "INFO"
    rate_limit_per_minute: int = 180
    auth_rate_limit_per_minute: int = 20
    upload_rate_limit_per_minute: int = 30
    search_rate_limit_per_minute: int = 90
    max_image_upload_mb: int = 100
    max_video_upload_mb: int = 2048
    max_file_upload_mb: int = 2048
    environment: str = "development"
    account_deletion_grace_days: int = 30
    backup_retention_days: int = 30
    web_push_public_key: str = ""
    web_push_private_key: str = ""
    web_push_subject: str = "mailto:admin@socialn.local"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def validate_runtime_settings() -> None:
    """Fail closed when a production deployment still uses development secrets."""
    if settings.environment.lower() not in {"production", "prod"}:
        return
    weak_values = {"", "change_me", "dev-secret-change-me", "replace_this_with_a_long_random_secret"}
    if settings.jwt_secret in weak_values or len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be a unique value of at least 32 characters in production")
    if not settings.auth_cookie_secure:
        raise RuntimeError("AUTH_COOKIE_SECURE must be true in production")
    if not settings.auth_encryption_key or len(settings.auth_encryption_key) < 32:
        raise RuntimeError("AUTH_ENCRYPTION_KEY must be a separate value of at least 32 characters in production")
