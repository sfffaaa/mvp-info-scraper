import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


@dataclass
class Settings:
    config: dict
    twitter_username: str
    twitter_password: str
    twitter_email: str
    twitter_email_password: str
    gmail_address: str
    gmail_app_password: str

    @classmethod
    def load(cls, config_path: Path, env_path: Path | None = None) -> "Settings":
        if env_path and env_path.exists():
            load_dotenv(env_path)
        config = load_config(config_path)
        return cls(
            config=config,
            twitter_username=os.environ["TWITTER_USERNAME"],
            twitter_password=os.environ["TWITTER_PASSWORD"],
            twitter_email=os.environ.get("TWITTER_EMAIL", ""),
            twitter_email_password=os.environ.get("TWITTER_EMAIL_PASSWORD", ""),
            gmail_address=os.environ["GMAIL_ADDRESS"],
            gmail_app_password=os.environ["GMAIL_APP_PASSWORD"],
        )

    @property
    def output_dir(self) -> Path:
        return Path(self.config["paths"]["output"]).expanduser()

    @property
    def buffer_dir(self) -> Path:
        return Path(self.config["paths"]["buffer"])

    @property
    def seen_urls_path(self) -> Path:
        return Path(self.config["paths"]["seen_urls"])

    @property
    def preferences_path(self) -> Path:
        return Path(self.config["paths"]["preferences"])
