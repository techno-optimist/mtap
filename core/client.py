# /home/ubuntu/mtap_sdk/core/client.py
import httpx
import json
import asyncio
import time # For potential token expiry checks
from typing import Any, Optional, AsyncGenerator, Dict, Union, List
import urllib.parse
import mimetypes # For guessing content type of files in multipart

from .config import MtapClientConfig
from .models import (
    Memory, SearchResult, RevocationReceipt, AuditLogSlice,
    ConsentArtifact, ConsentArtifactStatus, PolicyDetails, PolicySummary, MemorySummary
)
from .errors import (
    MtapSdkError, ConfigurationError, NotImplementedError, MtapApiError,
    AuthenticationError, AuthorizationError, NotFoundError, InvalidRequestError,
    RateLimitError, ServerError, IdempotencyConflictError, NetworkError, StreamingError
)
from mtap_sdk.transport.base import BaseTransport
from mtap_sdk.transport.http import HttpTransport
from mtap_sdk.session.base import BaseAuthProvider, SessionContext
from mtap_sdk.governance.base import BaseConsentManager, BasePolicyManager
from mtap_sdk.extensions.base import ExtensionRegistry, BaseExtension

class MtapClient:
    """Main client for interacting with the MTAP API."""

    def __init__(self, config: MtapClientConfig):
        if not isinstance(config, MtapClientConfig):
            raise ConfigurationError("Invalid MtapClientConfig provided.")
        self.config = config
        
        self.transport: BaseTransport = self._get_transport_provider()

        if not isinstance(self.config.auth_provider, BaseAuthProvider):
            raise ConfigurationError("Invalid auth_provider in MtapClientConfig. Must be instance of BaseAuthProvider.")
        self.auth_provider: BaseAuthProvider = self.config.auth_provider
        
        self.consent_manager: Optional[BaseConsentManager] = None 
        self.policy_manager: Optional[BasePolicyManager] = None   
        
        self.extension_registry = ExtensionRegistry()
        self._session_context: Optional[SessionContext] = None
        self._is_closed = False

    def _get_transport_provider(self) -> BaseTransport:
        if not isinstance(self.config.transport_preference, str):
            raise ConfigurationError("Transport preference must be a string.")
            
        transport_pref = self.config.transport_preference.lower()
        if transport_pref in ["http", "https", "http3", "http/3"]:
            return HttpTransport(self.config.default_retry_config, self.config.default_timeout_config)
        else:
            raise NotImplementedError(f"Transport 	"{self.config.transport_preference}	" not implemented.")

    async def is_authenticated(self) -> bool:
        """Checks if the client has an active and valid session context."""
        if self._is_closed:
            return False
        if not self._session_context or not self._session_context.token_info:
            return False
        
        # Placeholder for more robust token expiry check if token_info contains expiry information
        # For example, if token_info has an "expires_at" timestamp:
        # expires_at = self._session_context.token_info.get("expires_at")
        # if expires_at and isinstance(expires_at, (int, float)) and expires_at < time.time():
        #     return False # Token expired
        return True

    async def authenticate(self) -> SessionContext:
        if self._is_closed:
            raise MtapSdkError("Client is closed.")
        self._session_context = await self.auth_provider.authenticate()
        if not isinstance(self._session_context, SessionContext):
            # Invalidate potentially partially set context
            self._session_context = None
            raise AuthenticationError("Authentication provider did not return a valid SessionContext.")
        return self._session_context

    async def get_session_context(self, auto_authenticate: bool = True) -> Optional[SessionContext]:
        """Retrieves the current session context.

        Args:
            auto_authenticate: If True (default), will attempt to authenticate if no valid session exists.
                               If False, returns the current session context or None if not authenticated,
                               without triggering authentication.
        """
        if self._is_closed:
            raise MtapSdkError("Client is closed.")

        if await self.is_authenticated():
            return self._session_context
        
        if auto_authenticate:
            await self.authenticate() # This will set self._session_context or raise
            return self._session_context
        else:
            return None # Not authenticated and auto_authenticate is False

    async def close(self) -> None:
        if self._is_closed:
            return
        if self.transport:
            await self.transport.close()
        if self.auth_provider:
            try:
                await self.auth_provider.logout()
            except Exception as e:
                print(f"Error during auth_provider logout: {e}") 
        self._session_context = None # Clear session context on close
        self._is_closed = True

    def _handle_api_error(self, status_code: int, error_payload: Any, url: str):
        message = f"API Error at {url} (Status {status_code})"
        details = None
        if isinstance(error_payload, dict):
            details = error_payload.get("detail", error_payload.get("error"))
            if isinstance(details, str):
                message = details
            elif isinstance(details, dict):
                 message = details.get("message", str(details))
            elif error_payload.get("message"): 
                message = error_payload["message"]
        elif isinstance(error_payload, str) and error_payload:
            message = error_payload

        error_map = {
            400: InvalidRequestError,
            401: AuthenticationError,
            403: AuthorizationError,
            404: NotFoundError,
            409: IdempotencyConflictError,
            429: RateLimitError,
        }
        error_class = error_map.get(status_code)
        if error_class:
            raise error_class(message, status_code)
        if 500 <= status_code < 600:
            raise ServerError(message, status_code)
        raise MtapApiError(message, status_code)

    async def _make_request(
        self,
        method: str,
        path: str,
        expected_status: List[int],
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None, 
        stream_data: Optional[AsyncGenerator[bytes, None]] = None,
        stream_response: bool = False
    ) -> Union[Dict[str, Any], httpx.Response]:
        if self._is_closed:
            raise MtapSdkError("Client is closed.")
        if not self.transport:
            raise ConfigurationError("Transport not initialized.")

        # Ensure authenticated session before making a request that requires auth
        # get_session_context will handle auto-authentication if needed and configured
        session_context = await self.get_session_context(auto_authenticate=True)
        if not session_context: # Should not happen if auto_authenticate is True and auth succeeds
            raise AuthenticationError("Failed to establish authenticated session for request.")
            
        auth_headers = await self.auth_provider.get_auth_headers()
        
        full_url = f"{self.config.server_url.rstrip("/")}/{path.lstrip("/")}"
        if params:
            encoded_params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in params.items()}
            full_url += "?" + urllib.parse.urlencode(encoded_params)
            
        all_headers = {**(self.config.default_headers or {}), **(headers or {}), **auth_headers}
        
        if json_data and not files and "Content-Type" not in all_headers:
             all_headers["Content-Type"] = "application/json; charset=utf-8"

        raw_response: Optional[httpx.Response] = None
        try:
            raw_response = await self.transport.request(
                method=method, url=full_url, headers=all_headers,
                data=data, json=json_data, files=files, stream_data=stream_data,
                timeout=self.config.default_timeout_config, 
                stream_response=stream_response
            )
        except NetworkError as e:
            raise e 
        except Exception as e:
            raise MtapSdkError(f"Unexpected error during request transport: {e}") from e

        if raw_response.status_code not in expected_status:
            error_payload = None
            try:
                error_content_bytes = await raw_response.aread()
                if "application/json" in raw_response.headers.get("content-type", "").lower():
                    error_payload = json.loads(error_content_bytes.decode("utf-8"))
                else:
                    error_payload = error_content_bytes.decode("utf-8", errors="replace")
            except Exception:
                pass 
            finally:
                if not stream_response or raw_response.status_code not in expected_status:
                    await raw_response.aclose()
            self._handle_api_error(raw_response.status_code, error_payload, full_url)

        if stream_response:
            return raw_response 
        else:
            try:
                response_content_bytes = await raw_response.aread()
                if not response_content_bytes:
                    return {} 
                if "application/json" in raw_response.headers.get("content-type", "").lower():
                    return json.loads(response_content_bytes.decode("utf-8"))
                else:
                    return {"raw_content": response_content_bytes, "content_type": raw_response.headers.get("content-type")}
            except json.JSONDecodeError as e:
                raise MtapApiError(f"Failed to decode JSON response from {full_url}: {e}", raw_response.status_code) from e
            except Exception as e:
                raise MtapSdkError(f"Error processing successful response from {full_url}: {e}") from e
            finally:
                await raw_response.aclose()

    async def capture_memory(
        self, 
        data: Union[bytes, AsyncGenerator[bytes, None]], 
        metadata: Dict[str, Any], 
        content_type: str, 
        filename: Optional[str] = "memory_data", 
        context: Optional[Dict[str, Any]] = None, 
        consent_proof: Optional[str] = None, 
        policy_snapshot_id: Optional[str] = None, 
        request_id: Optional[str] = None 
    ) -> Memory:
        path = "memories"
        headers = {}
        if request_id:
            headers["Idempotency-Key"] = request_id 
        if consent_proof:
            headers["X-Consent-Proof"] = consent_proof
        current_policy_id = policy_snapshot_id or self.config.default_policy_snapshot_id
        if current_policy_id:
            headers["X-Policy-Snapshot"] = current_policy_id

        files: Dict[str, Any] = {
            "metadata": (None, json.dumps(metadata), "application/json")
        }
        if context:
            files["context"] = (None, json.dumps(context), "application/json")

        actual_filename = filename if filename else "untitled"
        data_content_type = content_type if content_type else mimetypes.guess_type(actual_filename)[0] or "application/octet-stream"

        if isinstance(data, bytes):
            files["data"] = (actual_filename, data, data_content_type)
        elif hasattr(data, "__aiter__"): 
            files["data"] = (actual_filename, data, data_content_type)
        else:
            raise InvalidRequestError("Data must be bytes or an async generator.")

        response_json = await self._make_request(
            "POST", path, expected_status=[201],
            headers=headers, 
            files=files
        )
        if not isinstance(response_json, dict):
            raise MtapApiError(f"Capture memory response was not a JSON object: {type(response_json)}")
        return Memory(**response_json)

    async def append_to_memory(
        self, 
        parent_memory_id: str, 
        data: Union[bytes, AsyncGenerator[bytes, None]], 
        metadata: Dict[str, Any], 
        content_type: str, 
        filename: Optional[str] = "memory_data_append",
        consent_proof: Optional[str] = None, 
        request_id: Optional[str] = None
    ) -> Memory:
        path = f"memories/{parent_memory_id}/append"
        headers = {}
        if request_id:
            headers["Idempotency-Key"] = request_id
        if consent_proof:
            headers["X-Consent-Proof"] = consent_proof

        files: Dict[str, Any] = {
            "metadata": (None, json.dumps(metadata), "application/json")
        }
        actual_filename = filename if filename else "untitled_append"
        data_content_type = content_type if content_type else mimetypes.guess_type(actual_filename)[0] or "application/octet-stream"

        if isinstance(data, bytes):
            files["data"] = (actual_filename, data, data_content_type)
        elif hasattr(data, "__aiter__"): 
            files["data"] = (actual_filename, data, data_content_type)
        else:
            raise InvalidRequestError("Data must be bytes or an async generator for append.")

        response_json = await self._make_request(
            "POST", path, expected_status=[200, 201],
            headers=headers, files=files
        )
        if not isinstance(response_json, dict):
            raise MtapApiError(f"Append memory response was not a JSON object: {type(response_json)}")
        return Memory(**response_json)

    async def get_memory(
        self, 
        memory_id: str, 
        revision_id: Optional[str] = None, 
        accept_format: Optional[str] = None, 
        byte_range: Optional[str] = None, 
        consent_proof: Optional[str] = None, 
        stream: bool = False
    ) -> Union[Memory, httpx.Response]: 
        path = f"memories/{memory_id}"
        if revision_id:
            path += f"/revisions/{revision_id}"
        
        headers = {}
        if accept_format:
            headers["Accept"] = accept_format
        if byte_range:
            headers["Range"] = f"bytes={byte_range}" 
        if consent_proof:
            headers["X-Consent-Proof"] = consent_proof

        expected_statuses = [200]
        if byte_range: expected_statuses.append(206) 

        response_data = await self._make_request(
            "GET", path, expected_status=expected_statuses,
            headers=headers, stream_response=stream
        )

        if stream:
            return response_data 
        else:
            if "raw_content" in response_data and isinstance(response_data, dict):
                mem_id = memory_id
                mem_content_type = response_data.get("content_type", "application/octet-stream")
                mem_metadata = {} 
                return Memory(id=mem_id, content_type=mem_content_type, metadata=mem_metadata, _data_blob=response_data["raw_content"])
            
            if not isinstance(response_data, dict):
                 raise MtapApiError(f"Unexpected response type for non-streamed get_memory: {type(response_data)}")
            return Memory(**response_data) 

    async def search_memories(
        self, 
        query: Optional[Union[str, Dict[str, Any]]] = None, 
        query_dsl_type: Optional[str] = "simple_text", 
        page_token: Optional[str] = None, 
        page_size: int = 20, 
        sort: Optional[str] = None, 
        filters: Optional[Dict[str, Any]] = None, 
        consent_proof: Optional[str] = None, 
        privacy_budget_request: Optional[Dict[str, Any]] = None
    ) -> SearchResult:
        path = "memories/search"
        params: Dict[str, Any] = {"page_size": page_size}
        json_body: Dict[str, Any] = {}

        if query:
            if isinstance(query, str):
                json_body["q"] = query # Prefer query in body for POST
            else: 
                json_body["query_object"] = query 
        if query_dsl_type:
            json_body["dsl_type"] = query_dsl_type
        if page_token:
            params["page_token"] = page_token # page_token can remain a query param
        if sort:
            json_body["sort"] = sort
        if filters:
            json_body["filters"] = filters 
        if privacy_budget_request:
            json_body["privacy_budget"] = privacy_budget_request

        headers = {}
        if consent_proof:
            headers["X-Consent-Proof"] = consent_proof

        response_json = await self._make_request("POST", path, params=params, headers=headers, json_data=json_body if json_body else None, expected_status=[200]) 
        if not isinstance(response_json, dict):
            raise MtapApiError(f"Search response was not a JSON object: {type(response_json)}")
        return SearchResult(**response_json)

    async def revoke_memory(
        self, 
        memory_id: str, 
        reason_code: Optional[str] = None, 
        cascade: bool = False, 
        consent_proof: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> RevocationReceipt:
        path = f"memories/{memory_id}/revoke"
        headers = {}
        if consent_proof:
            headers["X-Consent-Proof"] = consent_proof
        if request_id:
            headers["Idempotency-Key"] = request_id
        
        json_body: Dict[str, Any] = {"cascade": cascade}
        if reason_code:
            json_body["reason_code"] = reason_code
            
        response_json = await self._make_request("POST", path, headers=headers, json_data=json_body, expected_status=[200, 202])
        if not isinstance(response_json, dict):
            raise MtapApiError(f"Revoke response was not a JSON object: {type(response_json)}")
        return RevocationReceipt(**response_json)

    async def audit_log(
        self, 
        scope: Optional[Dict[str, Any]] = None, 
        action_types: Optional[List[str]] = None, 
        since: Optional[str] = None, 
        until: Optional[str] = None, 
        page_token: Optional[str] = None,
        limit: int = 100, 
        consent_proof: Optional[str] = None
    ) -> AuditLogSlice:
        path = "audit/logs"
        params: Dict[str, Any] = {"limit": limit}
        if scope:
            params["scope"] = json.dumps(scope) 
        if action_types:
            params["action_types"] = ",".join(action_types) 
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if page_token:
            params["page_token"] = page_token

        headers = {}
        if consent_proof:
            headers["X-Consent-Proof"] = consent_proof

        response_json = await self._make_request("GET", path, params=params, headers=headers, expected_status=[200])
        if not isinstance(response_json, dict):
            raise MtapApiError(f"Audit log response was not a JSON object: {type(response_json)}")
        return AuditLogSlice(**response_json)

    async def get_consent_artifact(self, artifact_id: str) -> Optional[ConsentArtifact]:
        if self.consent_manager:
            return await self.consent_manager.get_consent_artifact(artifact_id)
        # Example direct implementation if no manager is configured:
        # path = f"governance/consent/artifacts/{artifact_id}"
        # response_json = await self._make_request("GET", path, expected_status=[200, 404])
        # if response_json and response_json.get("id"): # Check if it is a valid artifact
        #     return ConsentArtifact(**response_json)
        # return None
        raise NotImplementedError("ConsentManager not configured or method not implemented directly on client.")

    async def get_extension(self, extension_id: str, config: Optional[Dict[str, Any]] = None) -> Optional[BaseExtension]:
        if self._is_closed:
            raise MtapSdkError("Client is closed.")
        return await self.extension_registry.get_extension(extension_id, client=self, config=config)

    def register_extension(self, extension_class: type[BaseExtension]) -> None:
        if self._is_closed:
            raise MtapSdkError("Client is closed.")
        self.extension_registry.register(extension_class)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

