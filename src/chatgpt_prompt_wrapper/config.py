import os
from pathlib import Path


def get_config(dir_name: str, file_name: str) -> Path:
    xdg_config_home = Path(
        os.getenv("XDG_CONFIG_HOME", "~/.config")
    ).expanduser()
    if (xdg_config_home / dir_name).is_dir():
        return xdg_config_home / dir_name / file_name
    elif Path(f"~/.{dir_name}").expanduser().is_dir():
        return Path(f"~/.{dir_name}").expanduser() / file_name
    else:
        return xdg_config_home / dir_name / file_name


def example_config() -> str:
    return """[test]
# Example command to test the OpenAI API, taken from below.
# [Chat completion - OpenAI API](https://platform.openai.com/docs/guides/chat/introduction)

description = "Example command to test the OpenAI API."
show = true

[[test.messages]]
role = "system"
content = "You are a helpful assistant."
[[test.messages]]
role = "user"
content = "Who won the world series in 2020?"
[[test.messages]]
role = "assistant"
"content" = "The Los Angeles Dodgers won the World Series in 2020."
[[test.messages]]
role = "user"
content = "Where was it played?"

[sh]
description = "Ask a shell scripting question."
[[sh.messages]]
role = "user"
content = "You are an expert of the shell scripting. Answer the following questions."

[py]
description = "Ask a python programming question."
[[py.messages]]
role = "user"
content = "You are an expert python programmer. Answer the following questions."
"""
