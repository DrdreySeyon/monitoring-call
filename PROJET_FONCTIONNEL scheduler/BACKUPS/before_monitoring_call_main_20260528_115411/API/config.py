from pydantic import BaseSettings


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/call_monitor"
    ari_url: str = "http://127.0.0.1:8088/asterisk/ari"
    ari_user: str = "ari_user"
    ari_password: str = "password"
    api_prefix: str = "/api"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "*"
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_max_bytes: int = 5_000_000
    log_backup_count: int = 5

    @property
    def cors_origins_list(self):
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return origins or ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

API_TITLE = "API ARI FastAPI avec DTMF"
API_DESCRIPTION = "Backend FastAPI connecté à Asterisk ARI et MySQL avec support DTMF"
API_VERSION = "2.0.0"
