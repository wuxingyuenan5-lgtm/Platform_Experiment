from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.request
from pathlib import Path

from common import git_blob_sha
from prepare_tests import prepare_tests
from prepare_workflows import prepare_workflows


def create_blob(repository: str, token: str, data: bytes) -> str:
    body = json.dumps({"content": base64.b64encode(data).decode(), "encoding": "base64"}).encode()
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/git/blobs",
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "phase3-r1-blob-publisher",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["sha"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepared = {**prepare_workflows(), **prepare_tests()}
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    result = []
    for path in sorted(prepared):
        data = prepared[path]
        expected = git_blob_sha(data)
        actual = expected if args.prepare_only else create_blob(repository, token, data)
        if actual != expected:
            raise RuntimeError(f"blob SHA mismatch for {path}: expected {expected}, got {actual}")
        result.append({"path": path, "sha": actual, "bytes": len(data)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
