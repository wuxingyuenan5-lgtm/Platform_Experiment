from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ci_scope = load_script("ci_scope", "scripts/ci-scope.py")
bump_version = load_script("bump_version", "scripts/bump-version.py")


def test_docs_only_change_skips_application_jobs() -> None:
    assert ci_scope.classify_paths(["README.md"]) == {
        "backend": False,
        "runtime": False,
        "frontend": False,
        "docs_only": True,
    }


def test_single_module_changes_select_only_affected_job() -> None:
    backend = ci_scope.classify_paths(["platform-backend/app/example.py"])
    runtime = ci_scope.classify_paths(["execution-runtime/app/example.py"])
    frontend = ci_scope.classify_paths(["admin-risk/src/example.ts"])

    assert backend["backend"] and not backend["runtime"] and not backend["frontend"]
    assert runtime["runtime"] and not runtime["backend"] and not runtime["frontend"]
    assert frontend["frontend"] and not frontend["backend"] and not frontend["runtime"]


def test_shared_workflow_change_forces_full_matrix() -> None:
    assert ci_scope.classify_paths([".github/workflows/platform-ci.yml"]) == {
        "backend": True,
        "runtime": True,
        "frontend": True,
        "docs_only": False,
    }


def test_main_push_can_force_full_matrix() -> None:
    result = ci_scope.classify_paths([], force_full=True)
    assert result == {
        "backend": True,
        "runtime": True,
        "frontend": True,
        "docs_only": False,
    }


def test_bump_version_updates_all_maintained_declarations(tmp_path: Path) -> None:
    (tmp_path / "platform-backend").mkdir()
    (tmp_path / "execution-runtime").mkdir()
    (tmp_path / "admin-risk").mkdir()
    (tmp_path / "VERSION").write_text("0.8.0\n", encoding="utf-8")
    (tmp_path / "platform-backend/pyproject.toml").write_text(
        '[project]\nversion = "0.8.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "execution-runtime/pyproject.toml").write_text(
        '[project]\nversion = "0.8.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "admin-risk/.env").write_text(
        'VITE_GLOB_APP_VERSION = "0.8.0"\n',
        encoding="utf-8",
    )

    bump_version.update_versions(tmp_path, "0.9.0")

    assert (tmp_path / "VERSION").read_text(encoding="utf-8") == "0.9.0\n"
    assert 'version = "0.9.0"' in (
        tmp_path / "platform-backend/pyproject.toml"
    ).read_text(encoding="utf-8")
    assert 'version = "0.9.0"' in (
        tmp_path / "execution-runtime/pyproject.toml"
    ).read_text(encoding="utf-8")
    assert 'VITE_GLOB_APP_VERSION = "0.9.0"' in (
        tmp_path / "admin-risk/.env"
    ).read_text(encoding="utf-8")


def test_platform_ci_is_pr_scoped_and_secret_scan_is_not_duplicated() -> None:
    workflow = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    assert "- 'feature/**'" not in workflow
    assert "python scripts/scan-secrets.py" not in workflow
    assert "needs.changes.outputs.backend" in workflow
    assert "needs.changes.outputs.runtime" in workflow
    assert "needs.changes.outputs.frontend" in workflow
