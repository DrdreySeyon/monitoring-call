from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_prefix: str = "/api"
    app_name: str = "Monitoring d'Appels TCU - UX"
    api_mode: str = "demo"
    database_engine: str = "in-memory"
    ari_url: str = "http://IP_ASTERISK:8088/ari"
    ami_enabled: bool = True
    ami_host: str = "IP_ASTERISK"
    ami_port: int = 5039
    scheduler_timezone: str = "Europe/Paris"


settings = Settings()
