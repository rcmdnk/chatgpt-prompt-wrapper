from __future__ import annotations

import inspect
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from conf_finder import ConfFinder

from .__version__ import __version__
from .arg_parser import cli_help, parse_args, true_false_params, true_params
from .chatgpt import Ask, Chat, Discuss
from .chatgpt_prompt_wrapper_exception import ChatGPTPromptWrapperError
from .cmd import commands, cost, init
from .log_formatter import get_logger

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass
class ChatGPTPromptWrapper:
    """ChatGPTPromptWrapper main class.

    Parameters
    ----------
    argv : list[str] | None
        Arguments to parse. If None, use sys.argv[1:]. It must have at least one positional argument as subcommand.
    cmd_name : str
        Command name.
    config_file_name : str
        Configuration TOML file name.
    cost_file_name : str
        Cost JSON file name.
    """

    argv: list[str] | None = None
    cmd_name: str = "cg"
    config_file_name: str = "config.toml"
    cost_file_name: str = "cost.json"

    def __post_init__(self) -> None:
        self.log = get_logger(__name__.split(".")[0])

        if self.argv is None:
            self.argv = sys.argv[1:]
        self.args = parse_args(self.argv)
        self.cmd = self.args.subcommand[0]

        if "." in self.config_file_name:
            self.config_file_ext = self.config_file_name.split(".")[-1]
            self.config_file_name = ".".join(
                self.config_file_name.split(".")[:-1]
            )
        else:
            self.config_file_ext = "toml"

        if "." in self.cost_file_name:
            self.cost_file_ext = self.cost_file_name.split(".")[-1]
            self.cost_file_name = ".".join(self.cost_file_name.split(".")[:-1])
        else:
            self.cost_file_ext = "json"

    def cmd_wo_config(self) -> bool:
        if self.cmd == "help":
            self.log.info(cli_help())
            return True

        if self.cmd == "version":
            self.log.info(f"{__package__} {__version__}")
            return True

        return False

    def cmd_wo_key(self) -> bool:
        if self.cmd == "init":
            init(self.config_file)
            self.log.info(f"Created config file at {self.config_file}.")
            return True

        if self.cmd == "cost":
            cost(self.cost_file, self.log)
            return True
        return False

    def set_files(self) -> None:
        cf = ConfFinder(self.cmd_name)
        self.config_file = (
            Path(self.args.conf)
            if self.args.conf
            else cf.conf(
                ext=self.config_file_ext, file_name=self.config_file_name
            )
        )
        self.cost_file = cf.conf(
            ext=self.cost_file_ext, file_name=self.cost_file_name
        )

    def set_config_messages(self, config: dict[str, Any]) -> None:
        if "messages" not in config:
            config["messages"] = []
        if self.args.message:
            config["messages"].append(
                {"role": "user", "content": " ".join(self.args.message)}
            )

    def set_ture_false_config(
        self,
        config: dict[str, Any],
        true_value: str,
        false_value: str | None = None,
        default_value: bool | None = None,
    ) -> None:
        if default_value is not None:
            config[true_value] = default_value

        if true_value in config:
            pass
        elif false_value is not None and false_value in config:
            config[true_value] = not config[false_value]

        if getattr(self.args, true_value):
            config[true_value] = True
        elif false_value is not None and getattr(self.args, false_value):
            config[true_value] = False

    def update_cmd_config(self, config: dict[str, Any]) -> None:
        self.set_config_messages(config)
        for true_value, false_value in true_false_params:
            self.set_ture_false_config(config, true_value, false_value)
        for true_value in true_params:
            self.set_ture_false_config(config, true_value, default_value=False)

        config.update(
            {
                k: v
                for k, v in vars(self.args).items()
                if k
                not in [x for y in true_false_params for x in y] + true_params
                and v is not None
            }
        )

    def get_cmd_config(self, config: dict[str, Any]) -> dict[str, Any]:
        cmd_config = config.get("global", {})
        cmd_config.update(config.get(self.cmd, {}))

        cmd_config["mode"] = cmd_config.get("mode", "ask")
        if self.cmd in ["ask", "chat", "discuss"]:
            cmd_config["mode"] = self.cmd

        self.update_cmd_config(cmd_config)

        if not cmd_config["messages"]:
            if cmd_config["mode"] == "ask":
                raise ChatGPTPromptWrapperError(
                    "This subcommand (ask mode) does not predefined prompt and need input message."
                )
            elif self.cmd == "discuss":
                raise ChatGPTPromptWrapperError(
                    "This subcommand (discussion mode) needs input message as a theme."
                )

        return cmd_config

    def run_chatgpt(self, config: dict[str, Any]) -> float:
        cls: type[Ask | Chat | Discuss]
        if config["mode"] == "ask":
            cls = Ask
        elif config["mode"] == "chat":
            cls = Chat
        elif config["mode"] == "discuss":
            cls = Discuss
        else:
            raise ChatGPTPromptWrapperError(
                f"Invalid mode: {config['mode']}. Please choose from ask, chat, discuss."
            )
        accepted_args = inspect.signature(cls.__init__).parameters
        params = {k: v for k, v in config.items() if k in accepted_args}
        cost_data_this = cls(**params).run(config["messages"])
        return cost_data_this

    def update_cost(
        self, cost_file: Path, new_cost: float, show_cost: bool = False
    ) -> None:
        if show_cost:
            self.log.info(f"\nEstimated cost: ${new_cost:.6f}")
        cost_data = {}
        if cost_file.exists():
            with open(cost_file, "r") as f:
                cost_data = dict(sorted(json.load(f).items()))
        month = datetime.now().strftime("%Y%m")
        cost_data[month] = cost_data.get(month, 0) + new_cost
        cost_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cost_file, "w") as f:
            json.dump(cost_data, f)

    def main(self) -> None:
        if self.cmd_wo_config():
            return

        self.set_files()

        if self.cmd_wo_key():
            return

        if not self.args.key:
            raise ChatGPTPromptWrapperError(
                "Set OPEN_AI_API_KEY environment variable or give it by -k (--key) argument."
            )

        if (
            self.cmd not in ["ask", "chat", "discuss"]
            and not self.config_file.is_file()
        ):
            raise ChatGPTPromptWrapperError(
                f"Configuration file {self.config_file} does not exist"
                f"`ask` or `cht` subcommand can be used w/o configuration file."
                f"You prepare the configuration file by `cg init` command."
            )

        if self.config_file.is_file():
            with open(self.config_file, "rb") as f:
                config = tomllib.load(f)
        else:
            config = {}

        if self.cmd == "commands":
            commands(config, self.log)
            return

        cmds = ["ask", "chat", "discuss"] + [
            x for x in config if x != "global"
        ]
        if self.cmd == "global":
            raise ChatGPTPromptWrapperError("`global` is not a subcommand.")
        if self.cmd not in cmds:
            raise ChatGPTPromptWrapperError(
                f"Subcommand: `{self.cmd}` is not defined."
            )

        cmd_config = self.get_cmd_config(config)
        cost_data_this = self.run_chatgpt(cmd_config)
        self.update_cost(
            self.cost_file, cost_data_this, cmd_config["show_cost"]
        )


def main() -> int:
    cg = ChatGPTPromptWrapper()
    try:
        cg.main()
        return 0
    except ChatGPTPromptWrapperError as e:
        cg.log.error(e)
        return 1
