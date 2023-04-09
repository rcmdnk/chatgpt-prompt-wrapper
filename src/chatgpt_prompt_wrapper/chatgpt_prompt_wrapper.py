from __future__ import annotations

import inspect
import json
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from typing import Any

from .__version__ import __version__
from .arg_parser import cli_help, non_chatgpt_params, parse_arg
from .chatgpt import Ask, Chat, Messages
from .chatgpt_prompt_wrapper_exception import ChatGPTPromptWrapperError
from .cmd import commands, cost, init
from .config import get_config
from .log_formatter import get_logger

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore


log = get_logger(__name__.split(".")[0])


def set_config_messages(config: dict[str, Any], args: Namespace) -> None:
    if "messages" not in config:
        config["messages"] = []
    if args.message:
        config["messages"].append(
            {"role": "user", "content": " ".join(args.message)}
        )


def set_config_show(config: dict[str, Any], args: Namespace) -> None:
    if "show" in config:
        pass
    elif "hide" in config:
        config["show"] = not config["hide"]
    if args.show:
        config["show"] = True
    elif args.hide:
        config["show"] = False


def set_config_multiline(config: dict[str, Any], args: Namespace) -> None:
    if "multiline" in config:
        pass
    elif "no_multiline" in config:
        config["multiline"] = not config["no_multiline"]
    if args.multiline:
        config["multiline"] = True
    elif args.no_multiline:
        config["multiline"] = False


def get_show_cost(config: dict[str, Any], args: Namespace) -> bool:
    show_cost = False
    show_cost = config["show_cost"] if "show_cost" in config else False
    if args.show_cost:
        show_cost = True
    return show_cost


def check_args(
    config: dict[str, Any], args: Namespace
) -> tuple[dict[str, Any], Messages, bool, bool]:
    set_config_messages(config, args)
    set_config_show(config, args)
    set_config_multiline(config, args)
    show_cost = get_show_cost(config, args)
    chat = config["chat"] if "chat" in config else False

    for arg in vars(args):
        if arg in non_chatgpt_params:
            continue
        if (param := getattr(args, arg)) is not None:
            config[arg] = param

    chatgpt_params = {
        k: v
        for k, v in config.items()
        if k
        not in [
            "messages",
            "description",
            "hide",
            "chat",
            "no_multi",
            "show_cost",
        ]
    }
    if not chat and not config["messages"]:
        raise ChatGPTPromptWrapperError(
            "This subcommand (ask mode) does not predefined prompt and need input message."
        )
    return chatgpt_params, config["messages"], chat, show_cost


def update_cost(
    cost_file: Path, new_cost: float, show_cost: bool = False
) -> None:
    if show_cost:
        log.info(f"\nEstimated cost: ${new_cost:.6f}")
    cost_data = {}
    if cost_file.exists():
        with open(cost_file, "r") as f:
            cost_data = {k: v for k, v in sorted(json.load(f).items())}
    month = datetime.now().strftime("%Y%m")
    cost_data[month] = cost_data.get(month, 0) + new_cost
    with open(cost_file, "w") as f:
        json.dump(cost_data, f)


def run_chatgpt(
    messages: Messages, params: dict[str, Any], chat: bool
) -> float:
    cls: Ask | Chat = Chat if chat else Ask
    accepted_args = inspect.signature(cls.__init__).parameters  # type: ignore
    params = {k: v for k, v in params.items() if k in accepted_args}
    cost_data_this = cls(**params).run(messages)  # type: ignore
    return cost_data_this


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
    cost_file = get_config("cg", "cost.json")

    if cmd == "init":
        init(config_file)
        log.info(f"Created config file at {config_file}.")
        return
    if cmd == "cost":
        cost(cost_file, log)
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

    if cmd == "commands":
        commands(config, log)
        return

    if cmd not in config:
        raise ChatGPTPromptWrapperError(f"Subcommand: {cmd} is not defined.")

    cmd_config = config[cmd]
    chatgpt_params, messages, chat, show_cost = check_args(cmd_config, args)

    cost_data_this = run_chatgpt(messages, chatgpt_params, chat)

    update_cost(cost_file, cost_data_this, show_cost)


def main() -> int:
    try:
        chatgpt_prompt_wrapper()
        return 0
    except ChatGPTPromptWrapperError as e:
        log.error(e)
        return 1
