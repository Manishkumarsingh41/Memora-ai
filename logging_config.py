import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    main_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "memora.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    main_handler.setLevel(logging.DEBUG)
    
    error_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "memora_errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
    )
    error_handler.setLevel(logging.ERROR)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    for handler in [main_handler, error_handler, console_handler]:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
