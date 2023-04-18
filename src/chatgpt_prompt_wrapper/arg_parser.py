import os
from argparse import ArgumentParser, Namespace

true_false_params = [
    ("show", "hide"),
    ("multiline", "no_multiline"),
    ("vi", "emacs"),
]

true_params = ["show_cost"]


def get_arg_parser() -> ArgumentParser:
    arg_parser = ArgumentParser()
    arg_parser.add_argument(
        "subcommand",
        help="Subcommand to run. Use 'commands' subcommand to list up available subcommands.",
        type=str,
        nargs=1,
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
        "-c", "--conf", help="Path to the configuration TOML file.", type=str
    )
    arg_parser.add_argument(
        "-m", "--model", help="ChatGPT Model to use.", type=str
    )
    arg_parser.add_argument(
        "-t",
        "--max_tokens",
        help="The maximum number of tokens to generate in the chat completion. Set 0 to use the max values for the model minus prompt tokens.",
        type=int,
    )
    arg_parser.add_argument(
        "-T",
        "--min_max_tokens",
        help="The minimum of max_tokens for the completion when max_tokens = 0.",
        type=int,
    )
    arg_parser.add_argument(
        "-l",
        "--tokens_limit",
        help="The limit of the total tokens of the prompt and the completion. Set 0 to use the max values for the model.",
        type=int,
    )
    arg_parser.add_argument(
        "--show",
        help="Show prompt for `ask` mode.",
        action="store_true",
    )
    arg_parser.add_argument(
        "--hide",
        help="Hide prompt for `ask` mode.",
        action="store_true",
    )
    arg_parser.add_argument(
        "--multiline",
        help="Use multiline input for `chat` mode.",
        action="store_true",
    )
    arg_parser.add_argument(
        "--no_multiline",
        help="Use single line input for `chat` mode.",
        action="store_true",
    )
    arg_parser.add_argument(
        "--vi",
        help="Use vi mode at `chat`.",
        action="store_true",
    )
    arg_parser.add_argument(
        "--emacs",
        help="Use emacs mode at `chat`.",
        action="store_true",
    )
    arg_parser.add_argument(
        "--show_cost",
        help="Show cost used.",
        action="store_true",
    )
    return arg_parser


def parse_args(argv: list[str]) -> Namespace:
    arg_parser = get_arg_parser()
    optional_strings: dict[str, int] = {}
    for action in arg_parser._actions:
        for s in action.option_strings:
            if isinstance(action.nargs, int):
                optional_strings[s] = action.nargs
            elif action.nargs is None:
                optional_strings[s] = 1

    positional = []
    option = []
    is_option = 0
    is_positional = False
    for arg in argv:
        if is_positional:
            positional.append(arg)
        elif is_option:
            option.append(arg)
            is_option -= 1
        elif arg == "--":
            is_positional = True
        elif arg in optional_strings:
            option.append(arg)
            is_option = optional_strings[arg]
        else:
            positional.append(arg)
    subcommand = [positional[0]] if positional else []
    message = [" ".join(positional[1:])] if len(positional) > 1 else []
    args = arg_parser.parse_args(subcommand + message + option)
    return args


def cli_help() -> str:
    arg_parser = get_arg_parser()
    return arg_parser.format_help()
