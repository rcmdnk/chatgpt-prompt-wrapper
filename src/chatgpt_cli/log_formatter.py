import logging
import sys


class LogFormatter(logging.Formatter):
    """Formatter to add color to log messages."""

    def __init__(self) -> None:
        self.default_format = "%(message)s"
        self.formats = {
            logging.DEBUG: f"{self.default_format}",
            logging.INFO: f"{self.default_format}",
            logging.WARNING: f"{self.default_format}",
            logging.ERROR: f"{self.default_format}",
            logging.CRITICAL: f"{self.default_format}",
        }
        if sys.stdout.isatty():
            colors = {
                logging.WARNING: "33",
                logging.ERROR: "31",
                logging.CRITICAL: "31",
            }
            for level in colors:
                self.formats[
                    level
                ] = f"\033[{colors[level]};1m{self.formats[level]}\033[m"

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        fmt = self.formats.get(record.levelno, self.default_format)
        formatter = logging.Formatter(fmt)
        return formatter.format(record)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Get a logger with a custom formatter."""
    log = logging.getLogger(name)
    log.setLevel(level)
    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(LogFormatter())
    log.addHandler(ch)
    return log
