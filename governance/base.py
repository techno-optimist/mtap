# /home/ubuntu/mtap_sdk/governance/base.py
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List

from mtap_sdk.core.models import (
    ConsentArtifact, ConsentArtifactStatus, RevocationReceipt, 
    PolicyDetails, PolicySummary
)

class BaseConsentManager(ABC):
    """Abstract base class for managing consent artifacts and proofs."""

    @abstractmethod
    async def generate_consent_proof(
        self,
        consent_artifact_id: str,
        operation_details: Dict[str, Any],
        # Potentially add parameters for ZKP context or specific proof types
    ) -> str:
        """Generates a consent proof for a given artifact and operation."""
        pass

    @abstractmethod
    async def create_consent_artifact(
        self, 
        artifact_data: Dict[str, Any]
    ) -> ConsentArtifactStatus:
        """Creates a new consent artifact."""
        pass

    @abstractmethod
    async def get_consent_artifact(
        self, 
        artifact_id: str
    ) -> Optional[ConsentArtifact]:
        """Retrieves a specific consent artifact by its ID."""
        pass

    @abstractmethod
    async def revoke_consent_artifact(
        self, 
        artifact_id: str, 
        reason_code: Optional[str] = None
    ) -> RevocationReceipt:
        """Revokes a specific consent artifact."""
        pass

    # Potentially add methods for listing consent artifacts, checking revocation status, etc.

class BasePolicyManager(ABC):
    """Abstract base class for managing data usage policies."""

    @abstractmethod
    async def get_policy_details(
        self, 
        policy_id: str
    ) -> Optional[PolicyDetails]:
        """Retrieves detailed information about a specific policy."""
        pass

    @abstractmethod
    async def list_available_policies(
        self
    ) -> List[PolicySummary]:
        """Lists summaries of available data usage policies."""
        pass

    async def get_default_policy_snapshot_id(self) -> Optional[str]:
        """Returns the default policy snapshot ID configured for the client."""
        # This might be implemented by accessing client configuration
        return None

