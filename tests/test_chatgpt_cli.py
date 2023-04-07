import sys

import pytest

from chatgpt_cli import main


@pytest.mark.parametrize(
    "argv, out",
    [
        (["chatgpt_cli"], "Hello World!\n"),
        (["chatgpt_cli", "Alice"], "Hello Alice!\n"),
        (
            ["chatgpt_cli", "Alice", "Bob", "Carol"],
            "Hello Alice, Bob, Carol!\n",
        ),
    ],
)
def test_main(argv, out, capsys):
    sys.argv = argv
    main()
    captured = capsys.readouterr()
    assert captured.out == out
