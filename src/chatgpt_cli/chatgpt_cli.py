from argparse import Namespace
from pathlib import Path
from typing import Any

from .__version__ import __version__
from .arg_parser import cli_help, non_chatgpt_params, parse_arg
from .chatgpt import ChatGPT, Messages
from .chatgpt_cli_exception import ChatGPTCliError
from .config import get_config
from .init_cmd import init
from .log_formatter import get_logger

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


log = get_logger(__name__.split(".")[0])


def check_args(
    config: dict[str, Any], args: Namespace
) -> tuple[dict[str, Any], Messages]:
    if "messages" not in config:
        config["messages"] = []
    if args.message:
        config["messages"].append(
            {"role": "user", "content": " ".join(args.message)}
        )

    for arg in vars(args):
        if arg in non_chatgpt_params:
            continue
        if (param := getattr(args, arg)) is not None:
            config[arg] = param

    chatgpt_params = {"key": args.key}
    chatgpt_params.update(
        {
            k: v
            for k, v in config.items()
            if k not in ["messages", "description"]
        }
    )
    return chatgpt_params, config["messages"]


def cg() -> None:
    args = parse_arg()
    cmd = args.subcommand[0]

    if cmd == "help":
        log.info(cli_help())
        return

    if cmd == "version":
        log.info(f"{__package__} {__version__}")
        return

    config_file = Path(args.conf) if args.conf else get_config("cg")

    if cmd == "init":
        init(config_file)
        log.info(f"Created config file at {config_file}.")
        return

    if not args.key:
        raise ChatGPTCliError(
            "Set OPEN_AI_API_KEY environment variable or give it by -k (--key) argument."
        )

    if not config_file.is_file():
        raise ChatGPTCliError(f"Config file {config_file} does not exist")
    with open(config_file, "rb") as f:
        config = tomllib.load(f)

    if cmd == "list":
        log.info("Available subcommands:")
        log.info("  Reserved commands:")
        log.info(
            f"    {'init':<10s}: Initialize config file with an example command."
        )
        log.info(f"    {'list':<10s}: List up subcommands (show this).")
        log.info(f"    {'version':<10s}: Show version.")
        log.info(f"    {'help':<10s}: Show help.")
        log.info("  User commands:")
        for cmd in config:
            log.info(f"    {cmd:<10s}: {config[cmd].get('description', '')}")
        return

    if cmd not in config:
        raise ChatGPTCliError(f"Subcommand: {cmd} is not defined.")

    cmd_config = config[cmd]
    chatgpt_params, messages = check_args(cmd_config, args)

    cg = ChatGPT(**chatgpt_params)
    response = cg.chat(messages)
    log.info(response)


def main() -> int:
    try:
        cg()
        return 0
    except ChatGPTCliError as e:
        log.error(e)
        return 1
