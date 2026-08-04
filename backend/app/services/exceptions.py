"""Custom service-layer exceptions used by the API layer."""

from __future__ import annotations


class ServiceError(Exception):
    """Base exception for service-layer failures."""


class ResourceNotFoundError(ServiceError):
    """Raised when a requested domain resource cannot be found."""


class ValidationError(ServiceError):
    """Raised when a service operation cannot proceed because the input is invalid."""


class AIServiceUnavailableError(ServiceError):
    """Raised when the upstream AI provider cannot fulfill the request."""


class AIResponseValidationError(ServiceError):
    """Raised when the AI provider returns malformed or incomplete data."""
