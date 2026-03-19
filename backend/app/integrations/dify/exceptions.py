from __future__ import annotations


class DifyClientError(RuntimeError):
    """Base exception for Dify integration failures."""


class DifyRequestError(DifyClientError):
    """Raised when Dify request fails or response payload is invalid."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)

