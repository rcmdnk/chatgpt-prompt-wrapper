# Development

## uv

Use [uv](https://docs.astral.sh/uv/) to setup environment.

To install uv, refer to [the installation page](https://docs.astral.sh/uv/getting-started/installation/).

## pre-commit

To check codes at the commit, use [pre-commit](https://pre-commit.com/).

`pre-commit` command will be installed in the uv environment.

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

## pytest

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

## Renovate

If you want to update dependencies automatically, [install Renovate into your repository](https://docs.renovatebot.com/getting-started/installing-onboarding/).
EOF
