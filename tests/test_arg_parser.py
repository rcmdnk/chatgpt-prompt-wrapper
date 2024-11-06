import sys

from chatgpt_prompt_wrapper.arg_parser import cli_help, parse_args


def test_parse_args(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "cg",
            "sub_cmd",
            "-c",
            "file",
            "message",
            "inputs",
            "--",
            "-k",
            "in message",
        ],
    )
    args = parse_args(sys.argv[1:])
    assert args.subcommand == ["sub_cmd"]
    assert args.conf == "file"
    assert args.message == [
        " ".join(["message", "inputs", "-k", "in message"]),
    ]


def test_cli_help():
    assert cli_help().startswith("usage")
