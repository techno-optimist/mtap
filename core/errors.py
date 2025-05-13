# /home/ubuntu/mtap_sdk/core/errors.py

class MtapSdkError(Exception):
    """Base class for all SDK-specific errors."""
    pass

class MtapApiError(MtapSdkError):
    """Base class for errors originating from the MTAP API.

    Attributes:
        status_code (int, optional): The HTTP status code of the error response.
        message (str, optional): The error message from the API.
    """
    def __init__(self, message: str = None, status_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def __str__(self):
        if self.status_code:
            return f"(Status {self.status_code}) {self.message if self.message else ''}"
        return self.message if self.message else "An API error occurred"

class AuthenticationError(MtapApiError):
    """Authentication failed (e.g., invalid credentials, expired token)."""
    pass

class AuthorizationError(MtapApiError):
    """User is not authorized to perform the action."""
    pass

class NotFoundError(MtapApiError):
    """The requested resource (e.g., memory) was not found."""
    pass

class InvalidRequestError(MtapApiError):
    """The request was malformed or invalid (e.g., missing parameters)."""
    pass

class RateLimitError(MtapApiError):
    """Request was rejected due to rate limiting."""
    pass

class ServerError(MtapApiError):
    """An unexpected error occurred on the server side."""
    pass

class IdempotencyConflictError(MtapApiError):
    """An idempotency key conflict occurred."""
    pass

class NetworkError(MtapSdkError):
    """A network issue occurred while trying to communicate with the server."""
    pass

class ConfigurationError(MtapSdkError):
    """The SDK was not configured correctly."""
    pass

class StreamingError(MtapSdkError):
    """An error occurred during data streaming operations."""
    pass

