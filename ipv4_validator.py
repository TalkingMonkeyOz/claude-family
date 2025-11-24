"""IPv4 address validation."""

import re
from typing import Union


def is_valid_ipv4(address: Union[str, bytes]) -> bool:
    """
    Validate if a string represents a valid IPv4 address.

    An IPv4 address consists of four octets separated by dots,
    where each octet is an integer between 0 and 255.

    Args:
        address: String or bytes to validate as IPv4 address

    Returns:
        True if address is a valid IPv4 address, False otherwise

    Examples:
        >>> is_valid_ipv4("192.168.1.1")
        True
        >>> is_valid_ipv4("255.255.255.255")
        True
        >>> is_valid_ipv4("256.1.1.1")
        False
        >>> is_valid_ipv4("192.168.1")
        False
        >>> is_valid_ipv4("192.168.1.1.1")
        False
    """
    # Handle bytes input
    if isinstance(address, bytes):
        try:
            address = address.decode('utf-8')
        except (UnicodeDecodeError, AttributeError):
            return False

    # Check if address is a string
    if not isinstance(address, str):
        return False

    # Strip whitespace
    address = address.strip()

    # Empty string is invalid
    if not address:
        return False

    # Split by dots
    parts = address.split('.')

    # Must have exactly 4 parts
    if len(parts) != 4:
        return False

    # Validate each octet
    for part in parts:
        # Part cannot be empty
        if not part:
            return False

        # Part cannot have leading zeros (except for "0" itself)
        if len(part) > 1 and part[0] == '0':
            return False

        # Part must be numeric
        if not part.isdigit():
            return False

        # Convert to integer and check range
        try:
            octet = int(part)
            if octet < 0 or octet > 255:
                return False
        except ValueError:
            return False

    return True


def is_valid_ipv4_regex(address: str) -> bool:
    """
    Validate IPv4 address using regex pattern.

    Alternative implementation using regular expressions.
    Slightly more concise but less explicit than the octet-by-octet approach.

    Args:
        address: String to validate

    Returns:
        True if address is a valid IPv4 address, False otherwise
    """
    if not isinstance(address, str):
        return False

    # Pattern: 1-3 digits, dot, repeated 3 times, then 1-3 digits
    # Then validate each octet is 0-255
    pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    match = re.match(pattern, address)

    if not match:
        return False

    # Validate each octet is in range 0-255
    for octet_str in match.groups():
        octet = int(octet_str)
        if octet < 0 or octet > 255:
            return False

    return True
