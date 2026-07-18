from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "platform-backend",
        "environment": settings.environment,
    }


@app.get(f"{settings.api_prefix}/system/info", tags=["system"])
def system_info() -> dict[str, str]:
    return {
        "service": "platform-backend",
        "version": "0.1.0",
        "apiVersion": "v1",
    }
