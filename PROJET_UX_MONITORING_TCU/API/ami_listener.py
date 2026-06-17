from config import settings


def get_ami_status():
    return {
        "enabled": settings.ami_enabled,
        "connected": True,
        "host": settings.ami_host,
        "port": settings.ami_port,
        "status": "connected",
    }
