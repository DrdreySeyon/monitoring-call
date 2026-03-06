from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "mysql -h asterisk-bdd-biatk.hom.mycloud.intrabpce.fr -u biatkadmin -P 15100 -pAgNyhYhqTO5WtZMJBp_9"
    ari_url: str = "http://sldcfrbiatk1076:8088/asterisk/ari"
    ari_user: str = "ari_user"
    ari_password: str = "sA7LuZ_t34"
    api_prefix: str = "/api"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()

API_TITLE = "API ARI FastAPI avec DTMF"
API_DESCRIPTION = "Backend FastAPI connecté à Asterisk ARI et MySQL avec support DTMF"

API_VERSION = "2.0.0"


