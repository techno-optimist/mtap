# /home/ubuntu/mtap_sdk/transport/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncGenerator

from mtap_sdk.core.config import TimeoutConfig

class BaseTransport(ABC):
    """Abstract base class for MTAP transport implementations."""

    @abstractmethod
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
        json_data: Optional[Dict[str, Any]] = None,
        stream_data: Optional[AsyncGenerator[bytes, None]] = None,
        timeout: Optional[TimeoutConfig] = None,
        stream_response: bool = False
    ) -> Any: # Returns a response object specific to the transport (e.g., HTTPX Response)
        """Makes an asynchronous request to the MTAP server.

        Args:
            method: HTTP method (e.g., "GET", "POST").
            url: The full URL for the request.
            headers: Request headers.
            data: Raw byte payload.
            json_data: JSON payload (will be serialized).
            stream_data: An async generator yielding bytes for streaming request body.
            timeout: Timeout configuration for this specific request.
            stream_response: Whether to stream the response body.

        Returns:
            A transport-specific response object.
        ""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Closes the transport client and releases resources."""
        pass

    # Potentially add helper methods for common response handling if applicable across transports

