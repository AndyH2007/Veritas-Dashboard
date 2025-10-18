"""
Hash generation utility for On-Chain Action Provenance
Implements SHA-256(input + output + timestamp) as specified
"""

import hashlib
import json
from typing import Any, Dict, Union
from datetime import datetime


def generate_action_hash(input_data: Any, output_data: Any, timestamp: Union[int, float, None] = None) -> str:
    """
    Generate deterministic SHA-256 hash for agent action.
    
    Args:
        input_data: Agent input (any serializable data)
        output_data: Agent output (any serializable data) 
        timestamp: Unix timestamp (defaults to current time)
    
    Returns:
        Hexadecimal hash string
    """
    if timestamp is None:
        timestamp = int(datetime.now().timestamp())
    
    # Convert inputs to strings for consistent hashing
    input_str = _serialize_data(input_data)
    output_str = _serialize_data(output_data)
    timestamp_str = str(int(timestamp))
    
    # Create deterministic hash: SHA-256(input + output + timestamp)
    combined = f"{input_str}{output_str}{timestamp_str}"
    hash_bytes = hashlib.sha256(combined.encode('utf-8')).digest()
    
    return hash_bytes.hex()


def _serialize_data(data: Any) -> str:
    """Serialize data to string for consistent hashing."""
    if isinstance(data, (dict, list)):
        return json.dumps(data, sort_keys=True, separators=(',', ':'))
    elif isinstance(data, str):
        return data
    else:
        return str(data)


def verify_hash(input_data: Any, output_data: Any, timestamp: Union[int, float], expected_hash: str) -> bool:
    """
    Verify that the generated hash matches expected hash.
    
    Args:
        input_data: Original input data
        output_data: Original output data
        timestamp: Original timestamp
        expected_hash: Hash to verify against
    
    Returns:
        True if hash matches, False otherwise
    """
    computed_hash = generate_action_hash(input_data, output_data, timestamp)
    return computed_hash == expected_hash


# Example usage and testing
if __name__ == "__main__":
    # Test deterministic behavior
    test_input = {"prompt": "Hello world", "model": "gpt-4"}
    test_output = {"response": "Hello! How can I help you?"}
    test_timestamp = 1697654321
    
    # Generate hash
    hash1 = generate_action_hash(test_input, test_output, test_timestamp)
    print(f"Generated hash: {hash1}")
    
    # Verify deterministic behavior
    hash2 = generate_action_hash(test_input, test_output, test_timestamp)
    print(f"Same inputs = same hash: {hash1 == hash2}")
    
    # Test verification
    is_valid = verify_hash(test_input, test_output, test_timestamp, hash1)
    print(f"Hash verification: {is_valid}")
    
    # Test with different timestamp
    hash3 = generate_action_hash(test_input, test_output, test_timestamp + 1)
    print(f"Different timestamp = different hash: {hash1 != hash3}")

