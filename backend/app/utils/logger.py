from loguru import logger
import sys
from pathlib import Path
from app.config.settings import settings


def setup_logger():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.remove()

    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )

    logger.add(
        str(log_dir / "evolution_ai.log"),
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="7 days",
        compression="zip"
    )

    return logger


logger = setup_logger()