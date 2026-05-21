import json

from localditado import config


def test_load_settings_has_defaults():
    s = config.load_settings(config_path=None)
    assert "whisper_model" in s
    assert s["language"] == "pt"


def test_profile_overrides_defaults(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"active_profile": "rapido"}), encoding="utf-8")
    s = config.load_settings(config_path=cfg, profile_name="rapido")
    assert s["beam_size"] == 1
    assert s["whisper_model"] == "base"


def test_overrides_win_over_profile_and_config(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"language": "pt"}), encoding="utf-8")
    s = config.load_settings(config_path=cfg, overrides={"language": "en"})
    assert s["language"] == "en"


def test_none_overrides_are_ignored(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"language": "es"}), encoding="utf-8")
    s = config.load_settings(config_path=cfg, overrides={"language": None})
    assert s["language"] == "es"


def test_update_config_roundtrip(tmp_path):
    cfg = tmp_path / "config.json"
    config.update_config({"hotkey": "ctrl+shift+x"}, config_path=cfg)
    s = config.load_settings(config_path=cfg)
    assert s["hotkey"] == "ctrl+shift+x"


def test_list_profiles_contains_known():
    profiles = config.list_profiles()
    assert {"precisao", "equilibrado", "rapido"}.issubset(set(profiles))
