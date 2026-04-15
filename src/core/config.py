import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    telegram_token: str
    redis_host: str
    redis_port: int
    log_level: str
    hh_api_base_url: str
    hh_user_agent: str
    
    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            telegram_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            hh_api_base_url=os.getenv("HH_API_URL", "https://api.hh.ru"),
            hh_user_agent=os.getenv("HH_USER_AGENT", "SkillsFinderBot/1.0"),
        )
    
    def validate(self) -> bool:
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        return True


settings = Settings.from_env()
