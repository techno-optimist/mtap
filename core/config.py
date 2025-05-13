# /home/ubuntu/mtap_sdk/core/config.py

from dataclasses import dataclass, field
from typing import Optional

# Forward declaration or import for BaseAuthProvider
# To avoid circular import if BaseAuthProvider imports something from config indirectly,
# though in this structure it seems unlikely. Using string literal for now if it were an issue.
# from mtap_sdk.session.base import BaseAuthProvider # Or use 'BaseAuthProvider' as string literal if needed
from mtap_sdk.session.base import BaseAuthProvider # Assuming direct import is fine

@dataclass
class RetryConfig:
    """Configuration for retry attempts on failed requests."""
    attempts: int = 3
    backoff_factor: float = 0.5  # Multiplier for delay between retries (e.g., delay = backoff_factor * (2 ** (attempt_number - 1)))
    max_retry_delay: float = 60.0 # Maximum delay in seconds between retries
    status_forcelist: list[int] = field(default_factory=lambda: [500, 502, 503, 504]) # HTTP status codes to retry on

@dataclass
class TimeoutConfig:
    """Configuration for request timeouts."""
    connect_timeout: float = 5.0  # Seconds to wait for connection to establish
    read_timeout: float = 30.0    # Seconds to wait for server to send data
    write_timeout: float = 30.0   # Seconds to wait for chunks to be written (for streaming uploads)

@dataclass
class MtapClientConfig:
    """Configuration for the MtapClient."""
    server_url: str
    auth_provider: BaseAuthProvider # Changed from Any to BaseAuthProvider
    transport_preference: str = "http3" # Or "http", "https"
    default_policy_snapshot_id: Optional[str] = None
    default_retry_config: RetryConfig = field(default_factory=RetryConfig)
    default_timeout_config: TimeoutConfig = field(default_factory=TimeoutConfig)
    default_headers: Optional[dict[str, str]] = None # e.g., {"User-Agent": "MTAPSDK/0.1.0"}
    # Add other global configurations

