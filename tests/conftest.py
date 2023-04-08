import pytest

from chatgpt_prompt_wrapper.config import example_config


@pytest.fixture(autouse=False)
def conf_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    file = tmp_path / "cg" / "config.toml"
    file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, "w") as f:
        f.write(example_config())
    return file
