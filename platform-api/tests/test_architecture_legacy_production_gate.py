from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md"
GITLAB_AUDIT = ROOT / "docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md"
CURRENT_STATE = ROOT / "docs/codex/current-state.md"
TASK_PACKET = ROOT / "tasks/issue-136-platform-0-9-2-system-optimization.md"
PRODUCTION_ENV = ROOT / "platform-web/.env.production"
GITLAB_DEPLOY = ROOT / "platform-web/.gitlab-ci.yml"
INSTALL_SCRIPT = ROOT / "deploy/install-native.sh"
DEPLOY_README = ROOT / "deploy/README.md"
NGINX_CONFIG = ROOT / "deploy/nginx-variable-global.conf"
AUTH_SYSTEMD = ROOT / "deploy/systemd/variable-global-auth.service"
DATA_SYSTEMD = ROOT / "deploy/systemd/variable-global-data.service"
AUTH_HANDLER = (
    ROOT
    / "projects/risk-control/auth-service/internal/handler/auth_handler.go"
)
AUTH_REPOSITORY = (
    ROOT
    / "projects/risk-control/auth-service/internal/repository/mysql/user_repo.go"
)
DATA_HANDLER = (
    ROOT
    / "projects/risk-control/data-service/internal/handler/handler.go"
)
DATA_REPOSITORY = (
    ROOT
    / "projects/risk-control/data-service/internal/repository/mysql/repository.go"
)

REQUIRED_LEGACY_ASSETS = (
    AUDIT,
    GITLAB_AUDIT,
    CURRENT_STATE,
    TASK_PACKET,
    PRODUCTION_ENV,
    GITLAB_DEPLOY,
    INSTALL_SCRIPT,
    DEPLOY_README,
    NGINX_CONFIG,
    AUTH_SYSTEMD,
    DATA_SYSTEMD,
    AUTH_HANDLER,
    AUTH_REPOSITORY,
    DATA_HANDLER,
    DATA_REPOSITORY,
)


@pytest.mark.architecture
def test_legacy_production_assets_require_an_explicit_migration_gate() -> None:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_LEGACY_ASSETS if not path.is_file()]
    assert not missing, f"Legacy production assets changed without migration evidence: {missing}"

    audit = AUDIT.read_text(encoding="utf-8")
    gitlab_audit = GITLAB_AUDIT.read_text(encoding="utf-8")
    current_state = CURRENT_STATE.read_text(encoding="utf-8")
    task_packet = TASK_PACKET.read_text(encoding="utf-8")

    assert "Phase J / J0" in audit
    assert "不删除或重命名`projects/risk-control`" in audit
    assert "不删除或改写`deploy/`执行链" in audit
    assert "不修改`.env.production`的API路由" in audit
    assert "Legacy生产部署证据" in gitlab_audit
    assert "不删除或重命名`platform-web/.gitlab-ci.yml`" in gitlab_audit
    assert "PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md" in current_state
    assert "PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md" in task_packet


@pytest.mark.architecture
def test_production_frontend_still_targets_the_declared_legacy_proxy() -> None:
    production_env = PRODUCTION_ENV.read_text(encoding="utf-8")

    for declaration in (
        "VITE_GLOB_API_URL=/api/auth",
        "VITE_GLOB_API_URL_PLOY=/api/auth",
        "VITE_GLOB_API_URL_MONITOR=/api/data",
        "VITE_GLOB_API_URL_FUTURE=/api/data",
        "VITE_GLOB_API_URL_DATA=/api/data",
        "VITE_GLOB_API_URL_MONITOR_WS=/api/data/ws",
        "VITE_GLOB_API_URL_FUTURE_WS=/api/data/ws",
    ):
        assert declaration in production_env


@pytest.mark.architecture
def test_legacy_gitlab_deployment_path_remains_explicit() -> None:
    gitlab = GITLAB_DEPLOY.read_text(encoding="utf-8")

    for marker in (
        "build-test:",
        "build-prod:",
        "runner20",
        "pnpm run build:test",
        "pnpm run build",
        "/www/wwwroot/risk-web.rta-office.com/",
        "$CI_COMMIT_TAG =~ /^risk.*$/",
    ):
        assert marker in gitlab


@pytest.mark.architecture
def test_legacy_install_and_proxy_topology_remain_explicit() -> None:
    install_script = INSTALL_SCRIPT.read_text(encoding="utf-8")
    nginx = NGINX_CONFIG.read_text(encoding="utf-8")
    auth_systemd = AUTH_SYSTEMD.read_text(encoding="utf-8")
    data_systemd = DATA_SYSTEMD.read_text(encoding="utf-8")

    for marker in (
        "projects/risk-control/auth-service",
        "projects/risk-control/data-service",
        "/etc/variable-global/auth.env",
        "/etc/variable-global/data.env",
    ):
        assert marker in install_script

    assert "/api/data" in nginx
    assert "127.0.0.1:8080" in nginx
    assert "127.0.0.1:8082" in nginx
    assert "auth-service" in auth_systemd
    assert "data-service" in data_systemd


@pytest.mark.architecture
def test_legacy_http_and_mysql_owners_are_frozen_for_inventory() -> None:
    auth_handler = AUTH_HANDLER.read_text(encoding="utf-8")
    auth_repository = AUTH_REPOSITORY.read_text(encoding="utf-8")
    data_handler = DATA_HANDLER.read_text(encoding="utf-8")
    data_repository = DATA_REPOSITORY.read_text(encoding="utf-8")

    for endpoint in (
        'mux.HandleFunc("/register"',
        'mux.HandleFunc("/login"',
        'mux.HandleFunc("/refresh"',
        'mux.HandleFunc("/api/v1/users/registrations"',
    ):
        assert endpoint in auth_handler

    assert "CREATE TABLE IF NOT EXISTS users" in auth_repository
    assert "CREATE TABLE IF NOT EXISTS user_sessions" in auth_repository

    for endpoint in (
        'mux.HandleFunc("/api/v1/accounts"',
        'mux.HandleFunc("/api/v1/data/sync"',
        'mux.HandleFunc("/api/v1/data/net-value"',
        'mux.HandleFunc("/product/navplatformNetValueList"',
    ):
        assert endpoint in data_handler

    for table in (
        "CREATE TABLE IF NOT EXISTS users",
        "CREATE TABLE IF NOT EXISTS accounts",
        "CREATE TABLE IF NOT EXISTS assets",
    ):
        assert table in data_repository

    assert "api_key_encrypted" in data_repository
    assert "api_secret_encrypted" in data_repository
