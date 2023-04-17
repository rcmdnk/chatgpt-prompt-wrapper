import logging
from typing import Any


def commands(config: dict[str, Any], log: logging.Logger) -> None:
    log.info("Available subcommands:")
    log.info("  Reserved commands:")
    log.info(f"    {'ask':<10s}: Ask w/o predefined prompt.")
    log.info(f"    {'chat':<10s}: Start chat w/o predefined prompt.")
    log.info(
        f"    {'discuss':<10s}: Start a discussion between GPTs. Give a them as a message."
    )
    log.info(
        f"    {'init':<10s}: Initialize config file with an example command."
    )
    log.info(f"    {'cost':<10s}: Show estimated cost used until now.")
    log.info(f"    {'commands':<10s}: List up subcommands (show this).")
    log.info(f"    {'version':<10s}: Show version.")
    log.info(f"    {'help':<10s}: Show help.")
    log.info("  User commands:")
    for cmd in config:
        if cmd in ["global", "ask", "chat"]:
            continue
        log.info(f"    {cmd:<10s}: {config[cmd].get('description', '')}")
