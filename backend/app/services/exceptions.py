"""Custom service-layer exceptions used by the API layer."""

from __future__ import annotations


class ServiceError(Exception):
    """Base exception for service-layer failures."""


class ResourceNotFoundError(ServiceError):
    """Raised when a requested domain resource cannot be found."""


class ValidationError(ServiceError):
    """Raised when a service operation cannot proceed because the input is invalid."""


class AIResponseValidationError(ServiceError):
    """Raised when the AI provider returns malformed or incomplete data."""


class StorageUnavailableError(ServiceError):
    """Raised when report storage cannot complete an operation."""


class LLMRequestError(ServiceError):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
