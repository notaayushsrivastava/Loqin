import os
import json
import tempfile
from unittest.mock import patch
import pytest

import app as loqin_app


def test_default_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_config_file = os.path.join(tmpdir, "Loqin_config.json")
        with patch.object(loqin_app, "APPDATA_DIR", tmpdir), \
             patch.object(loqin_app, "CONFIG_FILE", tmp_config_file):
            cfg = loqin_app.ConfigManager.load_config()
            assert cfg["username"] == ""
            assert cfg["interval"] == 30
            assert cfg["auto_connect"] is True
            assert cfg["last_wifi_ssid"] == ""
            assert os.path.exists(tmp_config_file)


def test_save_and_reload_config():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_config_file = os.path.join(tmpdir, "Loqin_config.json")
        with patch.object(loqin_app, "APPDATA_DIR", tmpdir), \
             patch.object(loqin_app, "CONFIG_FILE", tmp_config_file):
            cfg = {
                "username": "21BCE0001",
                "interval": 45,
                "auto_connect": False,
                "last_wifi_ssid": "VIT_WiFi",
            }
            loqin_app.ConfigManager.save_config(cfg)

            loaded = loqin_app.ConfigManager.load_config()
            assert loaded["username"] == "21BCE0001"
            assert loaded["interval"] == 45
            assert loaded["auto_connect"] is False
            assert loaded["last_wifi_ssid"] == "VIT_WiFi"


def test_legacy_password_migration():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_config_file = os.path.join(tmpdir, "Loqin_config.json")
        # Pre-seed config with legacy plaintext password
        legacy_data = {
            "username": "legacy_user",
            "password": "legacy_secret_password",
            "interval": 20,
        }
        with open(tmp_config_file, "w") as f:
            json.dump(legacy_data, f)

        with patch.object(loqin_app, "APPDATA_DIR", tmpdir), \
             patch.object(loqin_app, "CONFIG_FILE", tmp_config_file), \
             patch.object(loqin_app.ConfigManager, "set_password") as mock_set_pwd:
            loaded = loqin_app.ConfigManager.load_config()

            # Ensure set_password was called to migrate the password to keyring
            mock_set_pwd.assert_called_once_with("legacy_user", "legacy_secret_password")
            # Ensure plaintext password was stripped from config dictionary
            assert "password" not in loaded
            # Ensure file on disk no longer contains password
            with open(tmp_config_file, "r") as f:
                saved_on_disk = json.load(f)
            assert "password" not in saved_on_disk
