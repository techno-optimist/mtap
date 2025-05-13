# /home/ubuntu/mtap_sdk/session/base.py
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from dataclasses import dataclass

@dataclass
class SessionContext:
    """Stores session-specific information."""
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None # e.g., scopes
    token_info: Optional[Dict[str, Any]] = None # e.g., access_token, refresh_token, expires_at
    # Add other relevant session context fields

class BaseAuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    async def get_auth_headers(self) -> Dict[str, str]:
        """Returns a dictionary of headers required for authentication.

        This method should handle token acquisition, caching, and refreshing internally.
        """
        pass

    @abstractmethod
    async def authenticate(self) -> SessionContext:
        """Explicitly authenticates and returns a session context.
        
        Useful for initial login or re-authentication.
        """
        pass

    async def refresh_session(self) -> Optional[SessionContext]:
        """Attempts to refresh the current session or token.
        
        Returns a new SessionContext if successful, None otherwise.
        This might be a no-op for some auth providers.
        """
        return None # Default implementation for providers that don't support refresh

    async def logout(self) -> None:
        """Performs logout actions, like invalidating tokens if applicable."""
        pass # Default implementation

