from __future__ import annotations

import importlib.util
import shutil
import subprocess
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
    backend = ci_scope.classify_paths(["platform-api/app/example.py"])
    runtime = ci_scope.classify_paths(["execution-runtime/app/example.py"])
    frontend = ci_scope.classify_paths(["platform-web/src/example.ts"])

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
    (tmp_path / "platform-api/app").mkdir(parents=True)
    (tmp_path / "execution-runtime/app").mkdir(parents=True)
    (tmp_path / "platform-web").mkdir()
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "VERSION").write_text("0.8.0\n", encoding="utf-8")
    (tmp_path / "platform-api/pyproject.toml").write_text(
        '[project]\nversion = "0.8.0"\n', encoding="utf-8"
    )
    (tmp_path / "execution-runtime/pyproject.toml").write_text(
        '[project]\nversion = "0.8.0"\n', encoding="utf-8"
    )
    (tmp_path / "platform-web/package.json").write_text(
        '{\n  "name": "platform-web",\n  "version": "0.8.0",\n  "private": true\n}\n',
        encoding="utf-8",
    )
    for filename in (".env.development", ".env.production"):
        (tmp_path / f"platform-web/{filename}").write_text(
            'VITE_GLOB_APP_VERSION = "0.8.0"\n', encoding="utf-8"
        )
    (tmp_path / "platform-api/app/application.py").write_text(
        'PLATFORM_VERSION = "0.8.0"\n', encoding="utf-8"
    )
    (tmp_path / "execution-runtime/app/version.py").write_text(
        'PLATFORM_VERSION = "0.8.0"\n', encoding="utf-8"
    )
    (tmp_path / "docs/BASELINE.md").write_text(
        '- Stable baseline: Platform `0.8.0`.\n',
        encoding="utf-8",
    )

    bump_version.update_versions(tmp_path, "0.9.3")

    assert (tmp_path / "VERSION").read_text(encoding="utf-8") == "0.9.3\n"
    assert 'version = "0.9.3"' in (
        tmp_path / "platform-api/pyproject.toml"
    ).read_text(encoding="utf-8")
    assert 'version = "0.9.3"' in (
        tmp_path / "execution-runtime/pyproject.toml"
    ).read_text(encoding="utf-8")
    assert '"version": "0.9.3"' in (
        tmp_path / "platform-web/package.json"
    ).read_text(encoding="utf-8")
    for filename in (".env.development", ".env.production"):
        assert 'VITE_GLOB_APP_VERSION = "0.9.3"' in (
            tmp_path / f"platform-web/{filename}"
        ).read_text(encoding="utf-8")
    assert 'PLATFORM_VERSION = "0.9.3"' in (
        tmp_path / "platform-api/app/application.py"
    ).read_text(encoding="utf-8")
    assert 'PLATFORM_VERSION = "0.9.3"' in (
        tmp_path / "execution-runtime/app/version.py"
    ).read_text(encoding="utf-8")
    assert '- Stable baseline: Platform `0.9.3`' in (
        tmp_path / "docs/BASELINE.md"
    ).read_text(encoding="utf-8")


def test_permanent_workflows_have_distinct_long_term_responsibilities() -> None:
    platform = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    quality = (ROOT / ".github/workflows/repository-quality.yml").read_text(
        encoding="utf-8"
    )
    secret = (ROOT / ".github/workflows/secret-scan.yml").read_text(encoding="utf-8")

    assert "refactor/platform-0-9-3-" not in platform + quality + secret
    assert "python scripts/scan-secrets.py" not in platform
    assert "python scripts/scan-secrets.py" in secret
    assert "python scripts/check-version-consistency.py" in quality
    assert "name: platform-api" in platform
    assert "name: execution-runtime" in platform
    assert "name: platform-web" in platform


@pytest.mark.parametrize("case", ["local_tmp", "tracked_tmp", "unknown_root"])
def test_local_outputs_do_not_hide_tracked_artifacts_or_unknown_roots(
    tmp_path: Path, monkeypatch, case: str,
) -> None:
    structure = load_script("repository_structure", "scripts/check-repository-structure.py")
    monkeypatch.setattr(structure, "ROOT", tmp_path)
    services = {name: tmp_path / name for name in structure.EXPECTED_SERVICES}
    for path in services.values():
        path.mkdir()
    monkeypatch.setattr(structure, "EXPECTED_SERVICES", services)
    (tmp_path / "tmp").mkdir()
    (tmp_path / "tmp/kept.html").write_text("reference", encoding="utf-8")
    if case == "unknown_root":
        (tmp_path / "fourth-service").mkdir()

    def tracked_files(command, **kwargs):
        assert command == ["git", "ls-files", "-z", "--", "tmp/"]
        assert kwargs["cwd"] == tmp_path
        output = b"tmp/kept.html\0tmp/moved.html\0" if case == "tracked_tmp" else b""
        return subprocess.CompletedProcess(command, 0, stdout=output)

    monkeypatch.setattr(structure.subprocess, "run", tracked_files)
    errors: list[str] = []
    structure.check_root_directories(errors)
    if case == "local_tmp":
        assert errors == []
    elif case == "tracked_tmp":
        assert len(errors) == 1 and "tracked temporary output" in errors[0]
    else:
        assert len(errors) == 1 and "fourth-service: unregistered" in errors[0]


@pytest.mark.parametrize(
    "case", ["large_owner", "missing_owner", "sample_reintroduced", "windows_newlines"]
)
def test_frontend_size_advice_preserves_real_boundary_failures(case: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the frontend boundary runner")
    runner = r"""
const fs = require('node:fs');
const read = fs.readFileSync;
const exists = fs.existsSync;
const mode = process.argv[1];
fs.readFileSync = function(file, ...args) {
  let value = read.call(this, file, ...args);
  const name = String(file).replaceAll('\\', '/');
  if (mode === 'large_owner' && name.endsWith('/charts/LocalChartWidget.ts')) {
    value += '\n'.repeat(1000);
  }
  if (mode === 'sample_reintroduced' && name.endsWith('/spread-carry/index.vue')) {
    value = String(value).replace(
      '../shared/StrategyResearchWorkspace.vue', '@/data/sample/spread',
    );
  }
  if (mode === 'windows_newlines' && name.includes('/router/routes/modules/')) {
    value = String(value).replace(/\r?\n/g, '\r\n');
  }
  return value;
};
fs.existsSync = function(file) {
  const name = String(file).replaceAll('\\', '/');
  if (mode === 'missing_owner' && name.endsWith('/charts/LocalChartWidget.ts')) {
    return false;
  }
  return exists.call(this, file);
};
require('./platform-web/scripts/check-codebase-boundaries.cjs');
const manifest = require('./platform-web/scripts/formal-route-manifest.cjs').generateManifest();
if (manifest.modules.some(item => item.path.includes('\\'))) {
  throw new Error('Manifest paths depend on host separators');
}
"""
    result = subprocess.run(
        [node, "-e", runner, case], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", check=False,
    )
    if case in {"large_owner", "windows_newlines"}:
        assert result.returncode == 0, result.stderr
        assert "[maintenance]" in result.stderr
    elif case == "missing_owner":
        assert result.returncode != 0 and "Hedge Board owner is missing" in result.stderr
    else:
        assert result.returncode != 0 and "without sample data" in result.stderr
