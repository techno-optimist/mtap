# /home/ubuntu/mtap_sdk/extensions/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

class BaseExtension(ABC):
    """Abstract base class for all MTAP SDK extensions."""

    extension_id: str # Unique identifier for the extension, e.g., "ext.memora.monetization-v1"

    def __init__(self, client: Any): # client would be an MtapClient instance
        """Initializes the extension with a reference to the MtapClient.

        Args:
            client: The MtapClient instance to interact with core SDK functionalities.
        """
        self.client = client

    @abstractmethod
    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initializes the extension with optional configuration.
        
        This method can be used to set up any necessary state or resources for the extension.
        """
        pass

    # Extensions would add their specific methods here.
    # For example, a monetization extension might have:
    # async def get_balance(self) -> float:
    #     pass
    # async def pre_flight_check(self, operation_cost: float) -> bool:
    #     pass

class ExtensionRegistry:
    """Manages the registration and retrieval of MTAP extensions."""

    def __init__(self):
        self._extensions: Dict[str, Type[BaseExtension]] = {}
        self._initialized_extensions: Dict[str, BaseExtension] = {}

    def register(self, extension_class: Type[BaseExtension]) -> None:
        """Registers an extension class.

        Args:
            extension_class: The class of the extension to register.
        
        Raises:
            ValueError: If the extension_id is not set or already registered.
        """
        if not hasattr(extension_class, 'extension_id') or not extension_class.extension_id:
            raise ValueError("Extension class must have a valid 'extension_id' attribute.")
        
        if extension_class.extension_id in self._extensions:
            raise ValueError(f"Extension with ID 	'{extension_class.extension_id}	' is already registered.")
        
        self._extensions[extension_class.extension_id] = extension_class
        print(f"Extension 	'{extension_class.extension_id}	' registered.")

    async def get_extension(self, extension_id: str, client: Any, config: Optional[Dict[str, Any]] = None) -> Optional[BaseExtension]:
        """Retrieves and initializes an extension by its ID.

        If the extension is retrieved for the first time, it will be instantiated and initialized.
        Subsequent calls will return the already initialized instance.

        Args:
            extension_id: The unique ID of the extension.
            client: The MtapClient instance to pass to the extension.
            config: Optional configuration for the extension initialization.

        Returns:
            An initialized instance of the extension, or None if not registered.
        """
        if extension_id in self._initialized_extensions:
            return self._initialized_extensions[extension_id]
        
        extension_class = self._extensions.get(extension_id)
        if not extension_class:
            print(f"Warning: Extension 	'{extension_id}	' not found in registry.")
            return None
        
        try:
            extension_instance = extension_class(client=client)
            await extension_instance.initialize(config=config)
            self._initialized_extensions[extension_id] = extension_instance
            print(f"Extension 	'{extension_id}	' initialized and retrieved.")
            return extension_instance
        except Exception as e:
            print(f"Error initializing extension 	'{extension_id}	': {e}")
            return None

    def list_registered_extensions(self) -> List[str]:
        """Returns a list of IDs of all registered extensions."""
        return list(self._extensions.keys())

