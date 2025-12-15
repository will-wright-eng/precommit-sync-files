import logging


def get_logger(name: str, debug_mode: bool) -> logging.Logger:
    level = logging.DEBUG if debug_mode else logging.INFO
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
