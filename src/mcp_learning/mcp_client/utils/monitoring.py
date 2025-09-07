"""Configure monitoring using Langfuse."""

import types
import typing

from .configurations import Configurations
from .dependencies import MissingOptionalDependencyError, validate_optional_dependency_installation

try:
    validate_optional_dependency_installation("langfuse")
except MissingOptionalDependencyError:
    MONITORING_FEASIBLE = False
else:
    MONITORING_FEASIBLE = True

    import langfuse  # pylint: disable=import-error


class NoOpContextManager:
    """A no-operation context manager that does nothing."""

    def __getattr__(self: "NoOpContextManager", name: str) -> "NoOpMethod":
        """Access any attribute and return a no-op method.

        Parameters
        ----------
        name : str
            name of the attribute being accessed

        Returns
        -------
        NoOpMethod
            a no-op method that does nothing
        """
        del name

        return NoOpMethod()

    def __enter__(self: "NoOpContextManager") -> "NoOpContextManager":
        """Enter the no-op context manager and return itself.

        Returns
        -------
        NoOpContextManager
            the no-op context manager itself
        """
        return self

    def __exit__(
        self: "NoOpContextManager",
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the no-op context manager and do nothing.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            type of the exception being handled, if any
        exc_val : BaseException | None
            value of the exception being handled, if any
        exc_tb : types.TracebackType | None
            traceback of the exception being handled, if any
        """
        del exc_type
        del exc_val
        del exc_tb


class NoOpMethod:
    """A no-operation method that does nothing."""

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> "NoOpContextManager":
        """Call the no-op method and return a no-op context manager.

        Parameters
        ----------
        *args : typing.Any
            positional arguments passed to the method
        **kwargs : typing.Any
            keyword arguments passed to the method

        Returns
        -------
        NoOpContextManager
            a no-op context manager that does nothing
        """
        del args
        del kwargs

        return NoOpContextManager()


class NoOpLangfuseClient:
    """A no-operation Langfuse client that does nothing."""

    def __getattr__(self: "NoOpLangfuseClient", name: str) -> "NoOpMethod":
        """Access any attribute and return a no-op method.

        Parameters
        ----------
        name : str
            name of the attribute being accessed

        Returns
        -------
        NoOpMethod
            a no-op method that does nothing
        """
        del name

        return NoOpMethod()


type MonitoringClient = langfuse.Langfuse | NoOpLangfuseClient


def get_monitoring_client(settings: Configurations) -> MonitoringClient:
    """Get a Langfuse client if monitoring is enabled and the dependency is installed.

    Parameters
    ----------
    settings : Configurations
        language model configurations containing API keys and customisations

    Returns
    -------
    MonitoringClient
        an instance of the Langfuse client or a no-op client
    """
    if MONITORING_FEASIBLE and settings.langfuse_enabled:
        return langfuse.Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

    return NoOpLangfuseClient()


__all__ = [
    "MONITORING_FEASIBLE",
    "MonitoringClient",
    "NoOpLangfuseClient",
    "get_monitoring_client",
]
