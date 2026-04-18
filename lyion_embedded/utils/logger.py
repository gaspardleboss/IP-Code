# =============================================================================
# logger.py — Centralised logging setup for the Ly-ion embedded system.
# Call get_logger(__name__) in every module to get a named logger instance.
# =============================================================================

import logging
import logging.handlers
import sys
import os
import config


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger with the given name.
    Logs go to both stdout and a rotating log file.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger is called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Console handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- Rotating file handler (5 MB × 3 backups) ---
    try:
        log_dir = os.path.dirname(config.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        # If we cannot open the log file, fall back to console-only logging
        logger.warning("Cannot open log file %s: %s — logging to console only", config.LOG_FILE, exc)

    return logger
