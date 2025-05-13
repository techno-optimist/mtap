# MTAP SDK (Python)

This is the Python SDK for the Memory Transfer and Access Protocol (MTAP). It provides developers and AI agents with a simple and powerful way to integrate MTAP functionalities into their applications.

MTAP aims to be the "HTTP of human memory," enabling a global ecosystem where memories can be captured, transmitted, accessed, and managed in an interoperable, secure, and user-controlled manner.

This SDK abstracts the complexities of the MTAP protocol, offering intuitive APIs for core memory operations, session management, governance, and extensibility, aligning with the vision of creating a "Stripe for Memories."

## Features

*   Client for interacting with MTAP-compliant servers.
*   Support for core MTAP operations: CAPTURE, APPEND, GET, SEARCH, REVOKE, AUDIT.
*   Asynchronous operations using `async/await`.
*   Streaming support for large data objects.
*   Idempotency for key operations.
*   Modular design based on MTAP layers (Transport, Session, Core, Governance, Extensions).
*   Extensible authentication provider framework.
*   Framework for MTAP extensions.
*   Robust error handling.

## Installation

```bash
pip install mtap-sdk
```

(Note: This package is not yet published on PyPI. This is a placeholder for when it is.)

## Quick Start

```python
import asyncio
from mtap_sdk import MtapClient, MtapClientConfig
from mtap_sdk.session.base import BaseAuthProvider # You would use a concrete auth provider
from mtap_sdk.core.models import MemoryMetadata
from mtap_sdk.core.errors import MtapApiError, NotFoundError

# --- Define a Dummy Auth Provider for this example --- 
class DummyAuthProvider(BaseAuthProvider):
    async def get_auth_headers(self) -> dict:
        return {"Authorization": "Bearer dummy_token"}
    async def authenticate(self) -> dict:
        return {"user_id": "test_user", "token_info": {"access_token": "dummy_token"}}
# --- End Dummy Auth Provider --- 

async def main():
    # Configure the client
    client_config = MtapClientConfig(
        server_url="YOUR_MTAP_SERVER_URL", # Replace with actual server URL
        auth_provider=DummyAuthProvider() # Replace with your actual auth provider
    )
    client = MtapClient(config=client_config)

    try:
        # Authenticate (optional, client methods will call it if needed)
        session = await client.authenticate()
        print(f"Authenticated: {session.user_id}")

        # 1. Capture a memory
        image_data = b"This is a test memory content."
        metadata = MemoryMetadata(
            timestamp="2025-05-13T15:00:00Z",
            location={"lat": 34.0522, "lon": -118.2437},
            tags=["example", "test"],
            description="A test memory captured via SDK."
        )
        
        # Note: The capture_memory implementation in client.py has a placeholder for how metadata is sent.
        # It currently assumes metadata is sent via custom headers, which needs to be aligned with server expectations
        # or use multipart form data for a more robust solution.
        # For this example to work, the server would need to expect X-Memory-Metadata and X-Memory-Context headers.
        print("Attempting to capture memory...")
        # captured_memory = await client.capture_memory(
        #     data=image_data,
        #     metadata=metadata.to_dict(), # Ensure your MemoryMetadata has a to_dict() method or pass a dict
        #     content_type="text/plain",
        #     context={"app_name": "SDK Example"}
        # )
        # print(f"Memory captured: ID {captured_memory.id}")

        # 2. Get the memory (assuming capture was successful and you have an ID)
        # memory_id_to_fetch = captured_memory.id 
        # print(f"\nAttempting to retrieve memory: {memory_id_to_fetch}")
        # retrieved_memory = await client.get_memory(memory_id=memory_id_to_fetch)
        # print(f"Retrieved memory: {retrieved_memory.id}, Description: {retrieved_memory.metadata.get(	"description	")}")
        # content = await retrieved_memory.get_data_bytes()
        # print(f"Content: {content.decode()}")

        # 3. Search memories
        print("\nAttempting to search memories...")
        # search_results = await client.search_memories(query="test")
        # print(f"Found {len(search_results.results)} memories matching 'test':")
        # for mem_summary in search_results.results:
        #     print(f"- ID: {mem_summary.id}, Preview: {mem_summary.metadata_preview.get(	"description	")}")

    except MtapApiError as e:
        print(f"MTAP API Error: {e} (Status: {e.status_code})")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    # Note: The example operations for capture/get/search are commented out 
    # as they require a running MTAP server and proper metadata handling in capture_memory.
    # This script primarily demonstrates client initialization and authentication flow.
    print("MTAP SDK Quick Start Example (Demonstrates Initialization)")
    print("To run full examples, ensure a MTAP server is available and configured,")
    print("and update the capture_memory method in client.py for robust metadata/data handling (e.g., multipart).")
    asyncio.run(main())

```

## Documentation

For detailed documentation on the SDK architecture, API reference, and advanced usage, please refer to:

*   `mtap_sdk_architecture_v1.1.md`
*   `mtap_sdk_documentation_v0.1.1.md`

(These documents would typically be hosted, e.g., on ReadTheDocs or a project website.)

## Development

This SDK is in active development. To set up a development environment:

1.  Clone the repository.
2.  Create a virtual environment: `python -m venv .venv`
3.  Activate it: `source .venv/bin/activate` (Linux/macOS) or `.venv\Scripts\activate` (Windows)
4.  Install dependencies, including development tools: `pip install -e .[dev]`

### Running Tests

(Placeholder - Assumes pytest is set up)

```bash
pytest
```

## Contributing

Contributions are welcome! Please refer to the project's contribution guidelines (CONTRIBUTING.md - to be created) and code of conduct (CODE_OF_CONDUCT.md - to be created).

## License

This SDK is licensed under the MIT License. See the LICENSE file for details. (LICENSE file to be created)

