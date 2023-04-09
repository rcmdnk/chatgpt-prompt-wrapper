# chatgpt-prompt-wrapper

[![test](https://github.com/rcmdnk/chatgpt-prompt-wrapper/actions/workflows/test.yml/badge.svg)](https://github.com/rcmdnk/chatgpt-prompt-wrapper/actions/workflows/test.yml)
[![test coverage](https://img.shields.io/badge/coverage-check%20here-blue.svg)](https://github.com/rcmdnk/chatgpt-prompt-wrapper/tree/coverage)

Python CLI implementation for [ChatGPT](https://openai.com/blog/chatgpt).

## Requirement

- Python 3.9, 3.10, 3.11
- Poetry (For development)

## Installation

```
$ pip install chatgpt-prompt-wrapper
```

## Usage

### Command line interface

```
$ cg help
usage: cg [-h] [-k KEY] [-c CONF] [-m MODEL] [-t TOKENS] [-l LIMIT] [--show] [--hide] [--multiline]
          [--no_multiline] [--show_cost]
          subcommand [message ...]

positional arguments:
  subcommand            Subcommand to run. Use 'commands' subcommand to list up available subcommands.
  message               Message to send to ChatGPT

optional arguments:
  -h, --help            show this help message and exit
  -k KEY, --key KEY     OpenAI API key.
  -c CONF, --conf CONF  Path to the configuration toml file.
  -m MODEL, --model MODEL
                        ChatGPT Model to use.
  -t TOKENS, --tokens TOKENS
                        The maximum number of tokens to generate in the chat completion. Set 0 to use
                        the max values for the model minus prompt tokens.
  -l LIMIT, --limit LIMIT
                        The limit of the total tokens of the prompt and the completion. Set 0 to use
                        the max values for the model.
  --show                Show prompt for ask command.
  --hide                Hide prompt for ask command.
  --multiline           Use multiline input for chat command.
  --no_multiline        Use single line input for chat command.
  --show_cost           Show cost used.
```

```
$ cg commands
Available subcommands:
  Reserved commands:
    init      : Initialize config file with an example command.
    cost      : Show estimated cost used until now.
    commands  : List up subcommands (show this).
    version   : Show version.
    help      : Show help.
  User commands:
    ask       : Ask a question w/o predefined prompt.
    test      : Example command to test the OpenAI API.
    ...
```

### Configuration file

#### File path

The default path to the configuration file is **$XDG_CONFIG_HOME/cg/config.toml**.

If **$XDG_CONFIG_HOME** is not defined, use **~/.config/cg/config.toml**.

If it does not exist and **~/.cg/config.toml** exists,
the existing file is used.

You can change the path by `-c <file>` (`--conf <file>`) option.

#### How to write the configuration file

The configuration file is written in the TOML format.

Subcommand is defined as the top table name.

The options for each table can be:

- `description`: Description of the command.
- `chat`: Set `true` to make the command chat mode (default is ask mode, only one exchange).
- `show_cost`: Set `true` to show cost at the end of the command.
- `model`: The model to use. (default: "gpt-3.5-turbo")
- `max_tokens`: The maximum number of tokens to generate in the chat completion. Set 0 to use the max values for the model. (default: 0)
- `tokens_limit`: The limit of the total tokens of the prompt and the completion. Set 0 to use the max values for the model. (default: 0)
- `temperature`: Sampling temperature (0 ~ 2). (default: 1)
- `top_p`: Probability (0 ~ 1) that the model will consider the top_p tokens. Do not set both temperature and top_p in the same time. (default: 1)
- `presence_penalty`: The penalty for the model to return the same token (-2 ~ 2). (default: 0)
- `frequency_penalty`: The penalty for the model to return the same token multiple times (-2 ~ 2). (default: 0)
- List of `messages`: Dictionary of message, which must have `role` ('system', 'user' or 'assistant') and `content` (message text).

The options for ask mode:

- `show`: Set `true` to show prompt for non chat command.
- `hide`: Set `true` to hide prompt for non chat command (default).

The options for chat mode:

- `multiline`: Set `true` to hide prompt for non chat command (default).
- `no_multiline`: Set `true` to hide prompt for non chat command.

Here is a example configuration (if you execute `cg init` at the first time, this configuration file is created).

```toml
[ask]
description = "Ask a question w/o predefined prompt."

[test]
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

[chat]
description = "Chat with the assistant."
chat = true
[[chat.messages]]
role = "user"
content = "Let's enjoy a chat."
```

These messages will be sent as an prompt before your input message.

You can give full questions and use `cg` w/o input messages like a first example `test` command.

Command examples:

- test

![test command](https://raw.githubusercontent.com/rcmdnk/chatgpt-prompt-wrapper/main/fig/cg_test.png)

- sh

![sh command](https://raw.githubusercontent.com/rcmdnk/chatgpt-prompt-wrapper/main/fig/cg_sh.png)

- py

![py command](https://raw.githubusercontent.com/rcmdnk/chatgpt-prompt-wrapper/main/fig/cg_py.png)

- caht

![chat command](https://raw.githubusercontent.com/rcmdnk/chatgpt-prompt-wrapper/main/fig/cg_chat.gif)

## Development

### Poetry

Use [Poetry](https://python-poetry.org/) to setup environment.

To install poetry, run:

```
$ pip install poetry
```

or use `pipx` (`x` is `3` or anything of your python version).

Setup poetry environment:

```
$ poetry install
```

Then enter the environment:

```
$ poetry shell
```

## pre-commit

To check codes at the commit, use [pre-commit](https://pre-commit.com/).

`pre-commit` command will be installed in the poetry environment.

First, run:

```
$ pre-commit install
```

Then `pre-commit` will be run at the commit.

Sometimes, you may want to skip the check. In that case, run:

```
$ git commit --no-verify
```

You can run `pre-commit` on entire repository manually:

```
$ pre-commit run -a
```

### pytest

Tests are written with [pytest](https://docs.pytest.org/).

Write tests in **/tests** directory.

To run tests, run:

```
$ pytest
```

The default setting runs tests in parallel with `-n auto`.
If you run tests in serial, run:

```
$ pytest -n 0
```

## GitHub Actions

If you push a repository to GitHub, GitHub Actions will run a test job
by [GitHub Actions](https://github.co.jp/features/actions).

The job runs at the Pull Request, too.

It checks codes with `pre-commit` and runs tests with `pytest`.
It also makes a test coverage report and uploads it to [the coverage branch](https://github.com/rcmdnk/chatgpt-prompt-wrapper/tree/coverage).

You can see the test status as a badge in the README.

### Renovate

If you want to update dependencies automatically, [install Renovate into your repository](https://docs.renovatebot.com/getting-started/installing-onboarding/).
