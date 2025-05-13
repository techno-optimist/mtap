# /home/ubuntu/mtap_sdk/core/models.py
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict, Union, AsyncGenerator

@dataclass
class Memory:
    """Represents a memory object in MTAP."""
    id: str
    content_type: str
    metadata: Dict[str, Any]
    revision_id: Optional[str] = None
    commit_hash: Optional[str] = None
    policy_snapshot_id: Optional[str] = None
    # Internal fields for data access, not directly part of MTAP model but for SDK use
    _data_blob: Optional[bytes] = field(default=None, repr=False)
    _data_link: Optional[str] = field(default=None, repr=False)
    _data_stream_provider: Optional[Any] = field(default=None, repr=False) # Callable that returns a stream

    async def get_data_stream(self) -> Optional[AsyncGenerator[bytes, None]]:
        """Provides an asynchronous stream of the memory data."""
        if self._data_stream_provider:
            return self._data_stream_provider()
        if self._data_blob:
            async def _generator():
                yield self._data_blob
            return _generator()
        # Potentially fetch from _data_link if necessary and not streamed directly
        return None

    async def get_data_bytes(self) -> Optional[bytes]:
        """Provides the complete memory data as bytes."""
        if self._data_blob:
            return self._data_blob
        if self._data_stream_provider:
            chunks = []
            async for chunk in self._data_stream_provider():
                chunks.append(chunk)
            self._data_blob = b"".join(chunks)
            return self._data_blob
        # Potentially fetch from _data_link
        return None

@dataclass
class MemorySummary:
    """Represents a summary of a memory object, often used in search results."""
    id: str
    content_type: str
    metadata_preview: Dict[str, Any] # Or a subset of metadata
    revision_id: Optional[str] = None

@dataclass
class SearchResult:
    """Represents the result of a memory search operation."""
    results: List[Union[Memory, MemorySummary]]
    next_page_token: Optional[str] = None
    privacy_budget_consumed: Optional[Dict[str, Any]] = None # e.g., {"epsilon": 0.1}

@dataclass
class RevocationReceipt:
    """Confirms the revocation of a memory or consent artifact."""
    revocation_id: str
    timestamp: str # ISO 8601 format
    status: str # e.g., "processed", "pending"
    target_id: str # ID of the memory or consent artifact revoked
    reason_code: Optional[str] = None

@dataclass
class AuditLogEntry:
    """Represents a single entry in an audit log."""
    log_id: str
    timestamp: str # ISO 8601 format
    actor_id: str
    action: str # e.g., "CAPTURE", "GET", "REVOKE_CONSENT"
    target_resource: Dict[str, str] # e.g., {"memory_id": "..."} or {"consent_id": "..."}
    details: Optional[Dict[str, Any]] = None
    status: str # e.g., "success", "failure"
    consent_proof_used: Optional[str] = None # Reference to consent proof

@dataclass
class AuditLogSlice:
    """Represents a slice of an audit log."""
    log_entries: List[AuditLogEntry]
    next_log_token: Optional[str] = None

@dataclass
class ConsentArtifact:
    """Represents a consent artifact."""
    id: str
    granter_id: str # User granting consent
    grantee_id: str # Entity receiving consent
    scope: Dict[str, Any] # e.g., {"memories": ["id1", "id2"], "actions": ["GET"]}
    conditions: Optional[Dict[str, Any]] = None # e.g., {"expiry_date": "..."}
    status: str # e.g., "active", "revoked", "expired"
    policy_snapshot_id: Optional[str] = None
    raw_artifact: Optional[str] = None # The signed artifact itself, if available

@dataclass
class ConsentArtifactStatus:
    """Status of a consent artifact management operation."""
    artifact_id: str
    status: str # e.g., "created", "updated", "revoked", "not_found"
    details: Optional[str] = None
    artifact: Optional[ConsentArtifact] = None

@dataclass
class PolicySummary:
    """Summary of a data usage policy."""
    id: str
    name: str
    version: str
    description_short: Optional[str] = None

@dataclass
class PolicyDetails(PolicySummary):
    """Detailed information about a data usage policy."""
    description_full: Optional[str] = None
    terms_url: Optional[str] = None
    # Other relevant policy fields

