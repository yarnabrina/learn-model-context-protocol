"""Handle optional dependencies."""

import importlib
import importlib.metadata

import pydantic


class MissingOptionalDependencyError(Exception):
    """Raised when optional dependency for a functionality is unavailable.

    Parameters
    ----------
    install_name : str
        install name of optional dependency
    import_name : str | None, optional
        import name of the package, by default None
    """

    def __init__(
        self: "MissingOptionalDependencyError", install_name: str, import_name: str | None = None
    ) -> None:
        error_message = f"{install_name} is missing in installed packages."
        if import_name is not None:
            error_message += f" {import_name} is also unavailable to be imported."

        super().__init__(error_message)


@pydantic.validate_call(validate_return=True)
def validate_optional_dependency_installation(
    install_name: str, /, import_name: str | None = None
) -> None:
    """Validate if package is installed in current virtual environment.

    Parameters
    ----------
    install_name : str
        install name of package
    import_name : str | None, optional
        import name of the package, by default None

    Raises
    ------
    MissingOptionalDependencyError
        if any package named ``install_name`` is not installed
    MissingOptionalDependencyError
        if ``import_name`` can not be imported
    """
    try:
        _ = importlib.metadata.metadata(install_name)
    except importlib.metadata.PackageNotFoundError as install_error:
        if import_name is None:
            raise MissingOptionalDependencyError(install_name) from install_error

        try:
            _ = importlib.import_module(import_name)
        except ImportError as import_error:
            raise MissingOptionalDependencyError(
                install_name, import_name=import_name
            ) from import_error


__all__ = ["MissingOptionalDependencyError", "validate_optional_dependency_installation"]
