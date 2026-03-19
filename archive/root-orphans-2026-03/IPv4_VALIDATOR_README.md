# IPv4 Address Validator

A Python module providing two implementations for validating IPv4 addresses with comprehensive test coverage.

## Overview

This module validates that a string represents a valid IPv4 address. Valid IPv4 addresses consist of exactly four octets (numbers from 0-255) separated by dots.

## Functions

### `is_valid_ipv4(address: Union[str, bytes]) -> bool`

**Recommended implementation** - Explicit octet-by-octet validation.

Validates an IPv4 address by:
1. Handling bytes input by decoding to UTF-8
2. Stripping leading/trailing whitespace
3. Splitting by dots and validating exactly 4 octets exist
4. Checking each octet is numeric, has no leading zeros (except "0" itself), and is in range 0-255

**Parameters:**
- `address`: String or bytes object to validate

**Returns:**
- `True` if valid IPv4 address, `False` otherwise

**Examples:**
```python
>>> is_valid_ipv4("192.168.1.1")
True

>>> is_valid_ipv4("255.255.255.255")
True

>>> is_valid_ipv4("256.1.1.1")
False

>>> is_valid_ipv4("192.168.1")
False

>>> is_valid_ipv4(b"192.168.1.1")
True

>>> is_valid_ipv4("  192.168.1.1  ")
True
```

### `is_valid_ipv4_regex(address: str) -> bool`

**Alternative implementation** - Regex-based validation.

Uses regular expressions to validate IPv4 addresses. More concise but less flexible with input types.

**Parameters:**
- `address`: String to validate

**Returns:**
- `True` if valid IPv4 address, `False` otherwise

**Examples:**
```python
>>> is_valid_ipv4_regex("192.168.1.1")
True

>>> is_valid_ipv4_regex("256.1.1.1")
False
```

## Validation Rules

### Valid Cases
- Four numbers 0-255 separated by dots: `192.168.1.1` ✓
- Single zeros are valid: `0.0.0.0` ✓
- Max address: `255.255.255.255` ✓
- Whitespace is trimmed: `"  192.168.1.1  "` ✓
- Bytes input (for `is_valid_ipv4`): `b"192.168.1.1"` ✓

### Invalid Cases
- **Octet out of range**: `256.1.1.1` ✗
- **Too few octets**: `192.168.1` ✗
- **Too many octets**: `192.168.1.1.1` ✗
- **Non-numeric**: `192.168.a.1` ✗
- **Leading zeros**: `01.168.1.1` ✗ (except single "0")
- **Empty octets**: `192.168..1` ✗
- **Negative numbers**: `-1.0.0.0` ✗
- **Empty string**: `""` ✗
- **None or wrong type**: `None`, `192` (int) ✗

## Implementation Details

### `is_valid_ipv4` - Explicit Approach

**Advantages:**
- Handles multiple input types (str, bytes)
- Explicitly rejects leading zeros (prevents octal interpretation)
- Handles whitespace gracefully
- More readable validation logic
- Better error handling

**Process:**
1. Decode bytes to UTF-8 (or reject)
2. Verify string type
3. Strip whitespace
4. Split by dots
5. Validate exactly 4 parts
6. For each octet:
   - Check not empty
   - Check no leading zeros
   - Check numeric only
   - Check range 0-255

### `is_valid_ipv4_regex` - Pattern Matching

**Advantages:**
- Concise implementation (~10 lines)
- Single validation pass
- Regex pattern clearly shows format

**Pattern:** `^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$`

**Limitations:**
- Only accepts strings (not bytes)
- Less flexible with whitespace
- Regex approach less explicit about validation rules

## Test Coverage

The module includes comprehensive test coverage (`test_ipv4_validator.py`):

- **30+ unit tests** covering both implementations
- **Valid cases**: basic addresses, edge values (0.0.0.0, 255.255.255.255)
- **Invalid cases**: out of range, wrong format, wrong types
- **Edge cases**: leading zeros, empty octets, special characters
- **Type handling**: bytes, whitespace, None, integers
- **Comparison tests**: verifies both implementations agree

### Running Tests

Using pytest (recommended):
```bash
pytest test_ipv4_validator.py -v
```

Or run basic tests:
```bash
python run_tests.py
```

## Usage Examples

### Basic Validation
```python
from ipv4_validator import is_valid_ipv4

# Check if user input is valid
user_ip = "192.168.1.1"
if is_valid_ipv4(user_ip):
    print(f"{user_ip} is valid")
```

### Filtering Addresses
```python
addresses = [
    "192.168.1.1",
    "256.1.1.1",
    "10.0.0.1",
    "not_an_ip"
]

valid_ips = [ip for ip in addresses if is_valid_ipv4(ip)]
# Result: ["192.168.1.1", "10.0.0.1"]
```

### Network Configuration
```python
def validate_network_config(ip, gateway, subnet):
    return all(is_valid_ipv4(addr) for addr in [ip, gateway, subnet])

if validate_network_config("192.168.1.100", "192.168.1.1", "255.255.255.0"):
    print("Network config is valid")
```

## Performance Considerations

- **Time Complexity**: O(n) where n is length of input string
- **Space Complexity**: O(1)
- Both implementations are similarly efficient
- String splitting is slightly faster than regex for this simple pattern

## When to Use Which Implementation

**Use `is_valid_ipv4` (Recommended) when:**
- You need to handle bytes input
- You want leading zero rejection for security/consistency
- You prefer explicit, readable validation logic
- You need flexible whitespace handling

**Use `is_valid_ipv4_regex` when:**
- You only work with strings
- You prefer concise code
- You're familiar with regex and prefer pattern-based validation

## Edge Cases Handled

| Case | is_valid_ipv4 | is_valid_ipv4_regex | Notes |
|------|---|---|---|
| `"0.0.0.0"` | ✓ | ✓ | Valid minimum |
| `"255.255.255.255"` | ✓ | ✓ | Valid maximum |
| `"01.0.0.0"` | ✗ | ✗ | Leading zero rejected |
| `"  192.168.1.1  "` | ✓ | ✗ | Whitespace handling differs |
| `b"192.168.1.1"` | ✓ | N/A | Bytes input support |
| `None` | ✗ | ✗ | Type check |
| `192` | ✗ | ✗ | Integer rejected |
| `"192.168.1"` | ✗ | ✗ | Too few octets |
| `"192.168.1.1.1"` | ✗ | ✗ | Too many octets |

## Files

- `ipv4_validator.py` - Main module with both implementations
- `test_ipv4_validator.py` - Comprehensive test suite (pytest)
- `run_tests.py` - Simple test runner for basic validation
- `IPv4_VALIDATOR_README.md` - This documentation

## License

This code is provided as-is for educational and practical use.
