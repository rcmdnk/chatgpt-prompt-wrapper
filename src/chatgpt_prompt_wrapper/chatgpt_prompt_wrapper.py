import json
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from typing import Any

from .__version__ import __version__
from .arg_parser import cli_help, non_chatgpt_params, parse_arg
from .chatgpt import ChatGPT, Messages
from .chatgpt_prompt_wrapper_exception import ChatGPTPromptWrapperError
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
) -> tuple[dict[str, Any], Messages, bool, bool]:
    if "messages" not in config:
        config["messages"] = []
    if args.message:
        config["messages"].append(
            {"role": "user", "content": " ".join(args.message)}
        )
    if "show" in config:
        pass
    elif "hide" in config:
        config["show"] = not config["hide"]
    if args.show:
        config["show"] = True
    elif args.hide:
        config["show"] = False

    show_cost = False
    show_cost = config["show_cost"] if "show_cost" in config else False
    if args.show_cost:
        show_cost = True

    chat = config["chat"] if "chat" in config else False

    for arg in vars(args):
        if arg in non_chatgpt_params:
            continue
        if (param := getattr(args, arg)) is not None:
            config[arg] = param

    chatgpt_params = {
        k: v
        for k, v in config.items()
        if k not in ["messages", "description", "hide", "chat", "show_cost"]
    }
    return chatgpt_params, config["messages"], chat, show_cost


def chatgpt_prompt_wrapper() -> None:
    args = parse_arg()
    cmd = args.subcommand[0]

    if cmd == "help":
        log.info(cli_help())
        return

    if cmd == "version":
        log.info(f"{__package__} {__version__}")
        return

    config_file = (
        Path(args.conf) if args.conf else get_config("cg", "config.toml")
    )
    cost = get_config("cg", "cost.json")

    if cmd == "init":
        init(config_file)
        log.info(f"Created config file at {config_file}.")
        return
    if cmd == "cost":
        if not cost.exists():
            log.info("No cost data.")
            return
        with open(cost, "r") as f:
            cost_data = json.load(f)
        log.info("Month, EstimatedCost(USD)")
        for k, v in cost_data.items():
            log.info(f"{k}, {v:.6f}")
        return

    if not args.key:
        raise ChatGPTPromptWrapperError(
            "Set OPEN_AI_API_KEY environment variable or give it by -k (--key) argument."
        )

    if not config_file.is_file():
        raise ChatGPTPromptWrapperError(
            f"Config file {config_file} does not exist"
        )
    with open(config_file, "rb") as f:
        config = tomllib.load(f)

    if cmd == "list":
        log.info("Available subcommands:")
        log.info("  Reserved commands:")
        log.info(
            f"    {'init':<10s}: Initialize config file with an example command."
        )
        log.info(f"    {'cost':<10s}: Show estimated cost used until now.")
        log.info(f"    {'list':<10s}: List up subcommands (show this).")
        log.info(f"    {'version':<10s}: Show version.")
        log.info(f"    {'help':<10s}: Show help.")
        log.info("  User commands:")
        for cmd in config:
            log.info(f"    {cmd:<10s}: {config[cmd].get('description', '')}")
        return

    if cmd not in config:
        raise ChatGPTPromptWrapperError(f"Subcommand: {cmd} is not defined.")

    cmd_config = config[cmd]
    chatgpt_params, messages, chat, show_cost = check_args(cmd_config, args)

    cg = ChatGPT(**chatgpt_params)
    if not chat:
        cost_data_this = cg.ask(messages)
    else:
        cost_data_this = cg.chat(messages)
    if show_cost:
        log.info(f"\nEstimated cost: ${cost_data_this:.6f}")

    cost_data = {}
    if cost.exists():
        with open(cost, "r") as f:
            cost_data = {k: v for k, v in sorted(json.load(f).items())}
    month = datetime.now().strftime("%Y%m")
    cost_data[month] = cost_data.get(month, 0) + cost_data_this
    with open(cost, "w") as f:
        json.dump(cost_data, f)


def main() -> int:
    try:
        chatgpt_prompt_wrapper()
        return 0
    except ChatGPTPromptWrapperError as e:
        log.error(e)
        return 1
