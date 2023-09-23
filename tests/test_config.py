try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def test_example_config(conf_file):
    with open(conf_file, "rb") as f:
        conf = tomllib.load(f)
    assert "test" in conf
    assert len(conf["test"]["messages"]) == 4
