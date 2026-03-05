import importlib
import sys

if sys.version_info >= (3, 11):
    tomllib = importlib.import_module("tomllib")
else:
    tomllib = importlib.import_module("tomli")


def test_example_config(conf_file):
    with open(conf_file, "rb") as f:
        conf = tomllib.load(f)
    assert "test" in conf
    assert len(conf["test"]["messages"]) == 4
