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
    environment: str = "development"
    account_deletion_grace_days: int = 30
    backup_retention_days: int = 30
    web_push_public_key: str = ""
    web_push_private_key: str = ""
    web_push_subject: str = "mailto:admin@socialn.local"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
