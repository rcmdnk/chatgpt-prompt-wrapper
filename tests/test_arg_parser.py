from chatgpt_cli.arg_parser import cli_help, parse_arg


def test_parse_arg(monkeypatch):
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
    args = parse_arg()
    assert args.subcommand == ["sub_cmd"]
    assert args.conf == "file"
    assert args.message == [
        " ".join(["message", "inputs", "-k", "in message"])
    ]


def test_cli_help():
    assert cli_help().startswith("usage")
