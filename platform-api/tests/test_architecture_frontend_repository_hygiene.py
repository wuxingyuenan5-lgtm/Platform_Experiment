from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = ROOT / "platform-web"
FORBIDDEN_LOCAL_ARTIFACTS = (
    FRONTEND_ROOT / "CNAME",
    FRONTEND_ROOT / ".gitpod.yml",
    FRONTEND_ROOT / "home-2560-check.png",
    FRONTEND_ROOT / "src" / "file_structure.txt",
)
NESTED_WORKFLOW_ROOT = FRONTEND_ROOT / ".github" / "workflows"
FRONTEND_GITIGNORE = FRONTEND_ROOT / ".gitignore"


@pytest.mark.architecture
def test_frontend_local_and_upstream_hosting_artifacts_do_not_return() -> None:
    existing = [
        str(path.relative_to(ROOT))
        for path in FORBIDDEN_LOCAL_ARTIFACTS
        if path.exists()
    ]
    assert not existing, f"Frontend local/upstream hosting artifacts returned: {existing}"

    nested_workflows = []
    if NESTED_WORKFLOW_ROOT.exists():
        nested_workflows = sorted(
            str(path.relative_to(ROOT))
            for path in NESTED_WORKFLOW_ROOT.iterdir()
            if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}
        )
    assert not nested_workflows, (
        "GitHub Actions workflows must live only under the repository root: "
        f"{nested_workflows}"
    )


@pytest.mark.architecture
def test_frontend_local_inspection_artifacts_are_ignored() -> None:
    ignore_source = FRONTEND_GITIGNORE.read_text(encoding="utf-8")
    assert "/home-*-check.png" in ignore_source
    assert "/src/file_structure.txt" in ignore_source
