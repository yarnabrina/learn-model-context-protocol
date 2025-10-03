# Contributing to Model Context Protocol Exploration Project

Thank you for your interest in contributing!

## Start as a User

Before contributing, please follow the standard user installation and setup instructions:

- See the [Installation Guide](docs/installation.md) for setting up your environment and installing dependencies.
- See [Dependency Management](docs/dependency-management.md) for details on using `pip` instead of `uv`.
- Try running the [Examples](docs/examples.md) to verify your setup.

## Upgrading to Contributor

Once your user setup is working, you can install additional dependencies for development and documentation.

> **Note:** This project uses pip’s latest `--group` feature for development dependency management. See the [pip documentation](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-group) for details.

> **Contributor Tip:** While pip works for installing and upgrading dependencies, we recommend using `uv` for contributions, as it will keep `uv.lock` up to date. If you use only pip, please coordinate with maintainers to ensure the lockfile is refreshed before submitting a PR.

- **Editable installation**

    ```shell
    # Using pip
    pip install -e .

    # Using uv
    uv pip install -e .
    # or just use `uv sync`
    ```

- **Formatting dependencies**

    ```shell
    # Using pip
    pip install --group format .

    # Using uv
    uv sync --group format
    ```

- **Linting dependencies**

    ```shell
    # Using pip
    pip install --group lint .

    # Using uv
    uv sync --group lint
    ```

- **Documentation dependencies**

    ```shell
    # Using pip
    pip install --group docs .

    # Using uv
    uv sync --group docs
    ```

- **All development dependencies**

    ```shell
    # Using pip
    pip install --group dev .

    # Using uv
    uv sync --group dev
    ```

- **Upgrading dependencies**

    ```shell
    # Using pip
    pip install -e -U .
    # add extras or groups as needed

    # Using uv
    uv sync --upgrade
    # add extras or groups as needed
    ```

If you have questions, open an issue or start a discussion on GitHub. Thank you for helping improve this project!
