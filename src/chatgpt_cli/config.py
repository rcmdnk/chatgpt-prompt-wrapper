import os
from pathlib import Path


def get_config(name: str, suffix: str = "toml") -> Path:
    xdg_config_home = Path(
        os.getenv("XDG_CONFIG_HOME", "~/.config")
    ).expanduser()
    if (xdg_config_home / name).is_dir():
        return xdg_config_home / name / f"config.{suffix}"
    elif Path(f"~/.{name}").expanduser().is_dir():
        return Path(f"~/.{name}").expanduser() / f"config.{suffix}"
    elif Path(f"~/.{name}.{suffix}").expanduser().is_file():
        return Path(f"~/.{name}.{suffix}").expanduser()
    else:
        return xdg_config_home / name / f"config.{suffix}"


def example_config() -> str:
    return """[test_cmd]
# Example command to test the OpenAI API, taken from below.
# [Chat completion - OpenAI API](https://platform.openai.com/docs/guides/chat/introduction)

description = "Example command to test the OpenAI API."

model = "gpt-3.5-turbo"
max_tokens = 1024
return_tokens = 250

[[test_cmd.messages]]
role = "system"
content = "You are a helpful assistant."
[[test_cmd.messages]]
role = "user"
content = "Who won the world series in 2020?"
[[test_cmd.messages]]
role = "assistant"
"content" = "The Los Angeles Dodgers won the World Series in 2020."
[[test_cmd.messages]]
role = "user"
content = "Where was it played?"
"""
