import os
from pathlib import Path
import pytest
import yaml
from config import load_config, Settings


def test_load_config_reads_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "email:\n  to: user@gmail.com\n  from: tool@gmail.com\n"
        "  smtp_host: smtp.gmail.com\n  smtp_port: 587\n"
        "scraper:\n  posts_per_topic_per_run: 15\n  save_top_per_topic: 5\n"
        "paths:\n  output: ~/info/interested-raw-posts\n"
        "  buffer: buffer\n  seen_urls: seen_urls.txt\n  preferences: preferences.md\n"
        "topics: {}\nschedule: {}\n"
    )
    config = load_config(config_file)
    assert config["email"]["to"] == "user@gmail.com"
    assert config["scraper"]["posts_per_topic_per_run"] == 15


def test_settings_from_env(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "email:\n  to: user@gmail.com\n  from: tool@gmail.com\n"
        "  smtp_host: smtp.gmail.com\n  smtp_port: 587\n"
        "scraper:\n  posts_per_topic_per_run: 15\n  save_top_per_topic: 5\n"
        "paths:\n  output: ~/info/interested-raw-posts\n"
        "  buffer: buffer\n  seen_urls: seen_urls.txt\n  preferences: preferences.md\n"
        "topics: {}\nschedule: {}\n"
    )
    monkeypatch.setenv("TWITTER_USERNAME", "testuser")
    monkeypatch.setenv("TWITTER_PASSWORD", "testpass")
    monkeypatch.setenv("GMAIL_ADDRESS", "tool@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "apppass")

    settings = Settings.load(config_file)
    assert settings.twitter_username == "testuser"
    assert settings.gmail_app_password == "apppass"
    assert settings.config["email"]["to"] == "user@gmail.com"


def test_settings_missing_env_raises(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "email:\n  to: x\n  from: x\n  smtp_host: x\n  smtp_port: 587\n"
        "scraper:\n  posts_per_topic_per_run: 15\n  save_top_per_topic: 5\n"
        "paths:\n  output: ~/info\n  buffer: buffer\n"
        "  seen_urls: seen_urls.txt\n  preferences: preferences.md\n"
        "topics: {}\nschedule: {}\n"
    )
    monkeypatch.delenv("TWITTER_USERNAME", raising=False)
    monkeypatch.delenv("TWITTER_PASSWORD", raising=False)
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)

    with pytest.raises(KeyError):
        Settings.load(config_file)
