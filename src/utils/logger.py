import logging
import sys

from src.core.config import settings


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("hh_skills_finder")
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    return logger


logger = setup_logger()
