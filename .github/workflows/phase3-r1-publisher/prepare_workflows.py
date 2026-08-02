from __future__ import annotations

from common import OLD_A, OLD_B, PATTERN, PREFIX, ROOT, replace_or_assert

WORKFLOWS = (
    ".github/workflows/platform-ci.yml",
    ".github/workflows/platform-directory-invariants.yml",
    ".github/workflows/version-consistency.yml",
    ".github/workflows/secret-scan.yml",
    ".github/workflows/platform-0-9-2-audit.yml",
    ".github/workflows/platform-visual-baseline.yml",
    ".github/workflows/user-system-e2e.yml",
    ".github/workflows/hedge-board-e2e.yml",
    ".github/workflows/research-provider-smoke.yml",
)


def prepare_workflows() -> dict[str, bytes]:
    prepared: dict[str, bytes] = {}
    pair = f"      - {OLD_A}\n      - {OLD_B}"
    generic = f"      - {PATTERN}"
    for name in WORKFLOWS:
        text = (ROOT / name).read_text(encoding="utf-8")
        text = text.replace(pair, generic)
        text = text.replace(f"      - {OLD_A}\n", f"      - {PATTERN}\n")
        if OLD_A in text or OLD_B in text or PATTERN not in text:
            raise RuntimeError(f"invalid controlled branch conversion in {name}")
        prepared[name] = text.encode()

    name = ".github/workflows/platform-ci.yml"
    text = prepared[name].decode()
    text = replace_or_assert(
        text,
        "          PHASE3_ORIGINAL_HEAD: 735542b69c38b552fd3bb3109819b177e424b0fb\n",
        "          PHASE3_ORIGINAL_HEAD: 735542b69c38b552fd3bb3109819b177e424b0fb\n"
        "          PHASE_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}\n",
        "PR head audit SHA",
    )
    text = replace_or_assert(
        text, '--head "$GITHUB_SHA" \\', '--head "$PHASE_HEAD_SHA" \\', "history head"
    )
    text = replace_or_assert(
        text,
        f'if [ "$GITHUB_REF_NAME" = "{OLD_A}" ]; then',
        f'if [[ "$GITHUB_REF_NAME" == {PATTERN} ]]; then',
        "frontend debt branch",
    )
    prepared[name] = text.encode()

    name = ".github/workflows/platform-0-9-2-audit.yml"
    old = (
        "${{ always() && github.event_name == 'push' &&\n"
        f"          github.ref_name == '{OLD_A}' ||\n"
        f"          github.ref_name == '{OLD_B}' }}"
    )
    new = (
        "${{ always() && github.event_name == 'push' &&\n"
        f"          startsWith(github.ref_name, '{PREFIX}') }}"
    )
    prepared[name] = replace_or_assert(
        prepared[name].decode(), old, new, "baseline evidence condition"
    ).encode()

    name = ".github/workflows/platform-visual-baseline.yml"
    old = (
        "# Keep stale-run cancellation elsewhere, but allow retries for the exact 0.9.3 candidate branch.\n"
        f"  cancel-in-progress: ${{{{ github.ref_name != '{OLD_A}' && github.ref_name != '{OLD_B}' }}}}"
    )
    new = (
        "# Keep stale-run cancellation elsewhere, but allow retries for controlled Platform 0.9.3 phase branches.\n"
        f"  cancel-in-progress: ${{{{ !startsWith(github.ref_name, '{PREFIX}') }}}}"
    )
    prepared[name] = replace_or_assert(
        prepared[name].decode(), old, new, "visual concurrency condition"
    ).encode()
    return prepared
