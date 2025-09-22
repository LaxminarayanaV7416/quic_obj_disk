"""
    Author: Laxminarayana Vadnala
    Date: 2024-06-20
    Description: This is base building block defination for Object Storage Kernel.
    Email: lvadnala@nd.edu
"""

from typing import Optional, List, Dict, Any


class Object:
    """
        Object class is the base building block for Object Storage Kernel.
        It represents a generic object with basic attributes and methods.
    """

    def __init__(self, 
                    object_id: str,
                    metadata: Dict[str, str],
                    data_block: Any):
        """
            Initializes an Object instance.

            Args:
                object_id (str): The Hash of the object id.
                metadata (dict, optional): Additional metadata for the object. Defaults to None.
        """
        self.object_id = object_id
        self.metadata = metadata
        self.data_block = data_block

    def get_info(self) -> dict:
        """
            Retrieves information about the object.

            Returns:
                dict: A dictionary containing the object's name, size, and metadata.
        """
        return {
            "object_id": self.object_id,
            "metadata": self.metadata
        }

    def update_metadata(self, key: str, value):
        """
            Updates the metadata of the object.

            Args:
                key (str): The metadata key to update.
                value: The new value for the metadata key.
        """
        self.metadata[key] = value