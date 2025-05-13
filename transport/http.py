# /home/ubuntu/mtap_sdk/transport/http.py
import httpx
import asyncio # For asyncio.sleep in retry logic
import random # For jitter in retry logic
from typing import Any, Dict, Optional, AsyncGenerator

from .base import BaseTransport
from mtap_sdk.core.config import TimeoutConfig, RetryConfig
from mtap_sdk.core.errors import NetworkError, MtapApiError, ConfigurationError

class HttpTransport(BaseTransport):
    """HTTP/S transport implementation using HTTPX."""

    def __init__(self, retry_config: Optional[RetryConfig] = None, default_timeout: Optional[TimeoutConfig] = None):
        self._retry_config = retry_config if retry_config else RetryConfig()
        self._default_timeout = default_timeout if default_timeout else TimeoutConfig()
        
        if not isinstance(self._default_timeout, TimeoutConfig):
            raise ConfigurationError("Invalid default_timeout provided to HttpTransport.")
        if not isinstance(self._retry_config, RetryConfig):
            raise ConfigurationError("Invalid retry_config provided to HttpTransport.")

        # Note: httpx.Timeout can take connect, read, write, pool timeouts.
        # We are using connect and read from our TimeoutConfig.
        # Write timeout can be set per-request if needed, or added to global client timeout.
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                self._default_timeout.connect_timeout, 
                read=self._default_timeout.read_timeout,
                write=self._default_timeout.write_timeout
            )
        )

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None, # Added for multipart/form-data
        stream_data: Optional[AsyncGenerator[bytes, None]] = None,
        timeout: Optional[TimeoutConfig] = None,
        stream_response: bool = False
    ) -> httpx.Response:
        current_timeout_config = timeout if timeout else self._default_timeout
        httpx_timeout = httpx.Timeout(
            current_timeout_config.connect_timeout, 
            read=current_timeout_config.read_timeout,
            write=current_timeout_config.write_timeout
        )

        # Determine content: stream_data > data > json_data. `files` is handled separately by httpx.
        content_payload = None
        if stream_data:
            content_payload = stream_data
        elif data:
            content_payload = data
        # `json_data` is passed directly to httpx.request if `data` and `stream_data` are None.
        # `files` is also passed directly to httpx.request.

        attempts_left = self._retry_config.attempts
        current_attempt = 0
        last_exception: Optional[Exception] = None

        while current_attempt < self._retry_config.attempts:
            current_attempt += 1
            try:
                request_args = {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "timeout": httpx_timeout
                }
                if files:
                    request_args["files"] = files
                elif content_payload:
                    request_args["content"] = content_payload
                elif json_data:
                    request_args["json"] = json_data
                
                if stream_response:
                    # For streaming responses, build request and send with stream=True
                    req = self.client.build_request(**request_args) # type: ignore
                    response = await self.client.send(req, stream=True)
                else:
                    response = await self.client.request(**request_args) # type: ignore

                # If successful (even if it's an HTTP error status that we don't retry on), return response.
                # Retrying for specific status codes is handled here if configured.
                if response.status_code in self._retry_config.status_forcelist and current_attempt < self._retry_config.attempts:
                    # This will be caught by HTTPStatusError below if we raise it, or we can handle retry directly.
                    # To trigger retry, we can simulate an error or just continue the loop after a delay.
                    try:
                        response.raise_for_status() # Raise for 4xx/5xx if not in forcelist
                    except httpx.HTTPStatusError as e_status:
                        if e_status.response.status_code in self._retry_config.status_forcelist:
                            last_exception = e_status
                            # Proceed to delay and retry
                        else:
                            raise # Not a retryable status error, re-raise immediately
                    else: # No HTTPStatusError raised, but status is in forcelist (e.g. 200 in forcelist - unlikely)
                        return response # If it was successful and in forcelist, still return
                else:
                    # If not in forcelist or no attempts left, return the response.
                    # The calling layer (_make_request) will handle non-expected status codes.
                    return response

            except httpx.TimeoutException as e:
                last_exception = NetworkError(f"Request timed out to {url} on attempt {current_attempt}: {e}")
            except httpx.NetworkError as e: # Catches ConnectError, ReadError etc.
                last_exception = NetworkError(f"Network error connecting to {url} on attempt {current_attempt}: {e}")
            except httpx.HTTPStatusError as e: # This is raised by response.raise_for_status()
                last_exception = e # Keep it as HTTPStatusError for now, to check status_forcelist
                if e.response.status_code not in self._retry_config.status_forcelist:
                    # If it's an HTTP error not in the forcelist, we shouldn't retry at transport layer.
                    # Let the client layer handle it as a specific MtapApiError.
                    # However, the current logic means we return the response, and client layer handles it.
                    # This part of the logic needs to be clean: either transport retries or client does.
                    # For now, if raise_for_status() is called and it's not in forcelist, it should be re-raised.
                    # The current structure returns the response, and _make_request checks expected_status.
                    # Let's stick to: transport retries on network errors and specific status_forcelist codes.
                    raise # Re-raise if not in forcelist, _make_request will handle it.
            except Exception as e:
                last_exception = NetworkError(f"Unexpected error during HTTP request to {url} on attempt {current_attempt}: {e}")
            
            # If we are here, an error occurred and we might retry
            if current_attempt < self._retry_config.attempts:
                delay = (self._retry_config.backoff_factor * (2 ** (current_attempt - 1)))
                jitter = delay * 0.1 * random.uniform(-1, 1) # Add +/- 10% jitter
                actual_delay = min(delay + jitter, self._retry_config.max_retry_delay)
                actual_delay = max(0, actual_delay) # Ensure delay is not negative
                print(f"Request to {url} failed (attempt {current_attempt}/{self._retry_config.attempts}), retrying in {actual_delay:.2f}s. Error: {last_exception}")
                await asyncio.sleep(actual_delay)
            else: # Max attempts reached
                break
        
        if last_exception:
            # If HTTPStatusError was the last exception and it was in forcelist, we might re-raise it as MtapApiError or NetworkError
            if isinstance(last_exception, httpx.HTTPStatusError):
                 # Let _make_request handle this by returning the problematic response if it was received
                 # This path is tricky. If all retries for a status_forcelist item fail, we should raise.
                 # The current code returns the response if it's received. If it's an HTTPStatusError from raise_for_status, it's re-raised if not in forcelist.
                 # If it *is* in forcelist and retries are exhausted, we fall through and raise the last_exception.
                 raise MtapApiError(message=f"HTTP error after retries: {last_exception.response.status_code} for {url}", status_code=last_exception.response.status_code)
            raise last_exception # Should be NetworkError or a wrapped unexpected error
        else:
            # Should not be reached if loop completes without returning a response or raising an exception
            raise NetworkError(f"Request failed after {self._retry_config.attempts} attempts to {url} (unexpected state)")

    async def close(self) -> None:
        await self.client.aclose()

