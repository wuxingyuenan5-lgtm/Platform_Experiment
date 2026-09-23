"""Start only the isolated Playwright backend; never load operator dotenv settings."""
from pathlib import Path
import os
import sys


def main() -> None:
    service = sys.argv[1]
    if service not in {"backend", "runtime"}:
        raise RuntimeError("Expected backend or runtime")
    repo = Path(__file__).resolve().parents[2]
    root = repo / ("platform-api" if service == "backend" else "execution-runtime")
    sys.path.insert(0, str(root))
    from app.config import Settings, get_settings

    # pydantic-settings calls dotenv_values(), which does not honour
    # PYTHON_DOTENV_DISABLED. Disable its source before importing the application.
    Settings.model_config["env_file"] = None
    get_settings.cache_clear()
    settings = get_settings()
    run = os.environ["PLATFORM_VISUAL_E2E_RUN"]
    expected = (repo / ".e2e" / "platform-visual" / run).resolve()
    configured = Path(os.environ["PLATFORM_VISUAL_E2E_ROOT"]).resolve()
    if configured != expected or expected.parent != (repo / ".e2e" / "platform-visual").resolve():
        raise RuntimeError("Invalid isolated run directory")
    if settings.environment != "test":
        raise RuntimeError("Test environment required")
    if service == "backend":
        database = Path(settings.database_path).resolve()
        if database != expected / "platform.db" or database.exists():
            raise RuntimeError("Seed requires a new isolated database")
        if settings.live_trading_enabled or settings.research_refresh_enabled:
            raise RuntimeError("Live trading and research refresh must be disabled")
        if str(settings.runtime_base_url).rstrip("/") != os.environ["PLATFORM_VISUAL_RUNTIME_ORIGIN"]:
            raise RuntimeError("Backend must use the isolated Runtime")
        os.environ["PLATFORM_VISUAL_E2E_RESET"] = "0"
        sys.path.insert(0, str(root / "scripts"))
        from seed_platform_visual_e2e import main as seed
        seed()
    else:
        if settings.gateway_name != "fake" or settings.live_write_enabled:
            raise RuntimeError("Only a fake, read-only Runtime is allowed")
        if Path(settings.journal_path).resolve() != expected / "runtime.db":
            raise RuntimeError("Runtime journal must belong to this test run")
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=int(os.environ[f"PLATFORM_VISUAL_{service.upper()}_PORT"]))


if __name__ == "__main__":
    main()
