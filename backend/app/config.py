from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://socialn:socialn@db:3306/socialn"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "http://localhost:5173"
    upload_dir: str = "/app/uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
