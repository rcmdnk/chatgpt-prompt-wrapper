import os
import sys
from argparse import ArgumentParser, Namespace

non_chatgpt_params = ["subcommand", "message", "conf", "key"]


def get_arg_parser() -> ArgumentParser:
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        "subcommand", help="Subcommand to run.", type=str, nargs=1
    )
    arg_parser.add_argument(
        "message", help="Message to send to ChatGPT", type=str, nargs="*"
    )
    arg_parser.add_argument(
        "-k",
        "--key",
        help="OpenAI API key.",
        type=str,
        default=os.environ.get("OPENAI_API_KEY", ""),
    )
    arg_parser.add_argument(
        "-c", "--conf", help="Path to the configuration toml file.", type=str
    )
    arg_parser.add_argument(
        "-m", "--model", help="ChatGPT Model to use.", type=str
    )
    arg_parser.add_argument(
        "-t",
        "--tokens",
        help="The maximum number of tokens to generate in the chat completion. Set 0 to use the max values for the model minus prompt tokens.",
        type=int,
    )
    return arg_parser


def parse_arg() -> Namespace:
    positional = []
    option = []
    is_option = False
    is_positional = False
    for arg in sys.argv[1:]:
        if is_positional:
            positional.append(arg)
        elif is_option:
            option.append(arg)
            is_option = False
        elif arg == "--":
            is_positional = True
        elif arg.startswith("-"):
            option.append(arg)
            is_option = True
        else:
            positional.append(arg)
    subcommand = [positional[0]] if positional else []
    message = [" ".join(positional[1:])] if len(positional) > 1 else []
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args(subcommand + message + option)
    return args


def cli_help() -> str:
    arg_parser = get_arg_parser()
    return arg_parser.format_help()
