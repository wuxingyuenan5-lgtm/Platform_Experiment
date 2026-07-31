from pathlib import Path

from app.config import Settings, default_mt5_bridge_file_path


def test_mt5_bridge_path_uses_appdata_on_windows_hosts(monkeypatch, tmp_path: Path) -> None:
    appdata = tmp_path / "Roaming"
    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.delenv("VG_RUNTIME_MT5_BRIDGE_FILE_PATH", raising=False)

    expected = (
        appdata
        / "MetaQuotes"
        / "Terminal"
        / "Common"
        / "Files"
        / "variable_global_mt5_bridge.json"
    )

    assert default_mt5_bridge_file_path() == str(expected)
    assert Settings(_env_file=None).mt5_bridge_file_path == str(expected)


def test_mt5_bridge_path_has_portable_non_windows_fallback(monkeypatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("VG_RUNTIME_MT5_BRIDGE_FILE_PATH", raising=False)

    expected = str(Path("data") / "variable_global_mt5_bridge.json")

    assert default_mt5_bridge_file_path() == expected
    assert Settings(_env_file=None).mt5_bridge_file_path == expected


def test_mt5_bridge_path_preserves_explicit_operator_override(
    monkeypatch,
    tmp_path: Path,
) -> None:
    override = tmp_path / "approved" / "bridge.json"
    monkeypatch.setenv("VG_RUNTIME_MT5_BRIDGE_FILE_PATH", str(override))

    assert Settings(_env_file=None).mt5_bridge_file_path == str(override)
