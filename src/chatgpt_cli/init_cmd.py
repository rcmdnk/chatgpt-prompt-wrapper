from pathlib import Path

from .chatgpt_cli_exception import ChatGPTCliError
from .config import example_config


def init(config_file: Path) -> None:
    if config_file.is_file():
        raise ChatGPTCliError(f"Config file {config_file} already exists.")
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w") as f:
        f.write(example_config())
