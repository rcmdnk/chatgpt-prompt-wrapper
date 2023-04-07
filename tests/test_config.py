from chatgpt_cli.config import get_config

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def test_get_config(conf_file):
    assert conf_file == get_config("cg")


def test_example_config(conf_file):
    with open(conf_file, "rb") as f:
        conf = tomllib.load(f)
    assert "test_cmd" in conf
    assert len(conf["test_cmd"]["messages"]) == 4
