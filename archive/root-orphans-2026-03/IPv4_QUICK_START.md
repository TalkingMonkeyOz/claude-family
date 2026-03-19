# IPv4 Validator - Quick Start Guide

## Installation

Copy `ipv4_validator.py` to your project directory.

## Basic Usage

```python
from ipv4_validator import is_valid_ipv4

# Check if an address is valid
if is_valid_ipv4("192.168.1.1"):
    print("Valid IP address")
else:
    print("Invalid IP address")
```

## Quick Reference

| Function | Input | Returns | Best For |
|----------|-------|---------|----------|
| `is_valid_ipv4()` | str or bytes | bool | General use, handles multiple input types |
| `is_valid_ipv4_regex()` | str | bool | Pattern-based validation, concise code |

## What's Valid

✓ Standard addresses: `192.168.1.1`
✓ Max value: `255.255.255.255`
✓ Min value: `0.0.0.0`
✓ Bytes input: `b"192.168.1.1"` (for `is_valid_ipv4` only)
✓ Whitespace: `"  192.168.1.1  "` (automatically trimmed)

## What's Invalid

✗ Out of range: `256.1.1.1`
✗ Wrong format: `192.168.1` (need exactly 4 octets)
✗ Leading zeros: `01.168.1.1`
✗ Non-numeric: `192.168.a.1`
✗ Wrong type: `None`, `192` (int), `[192,168,1,1]`

## Common Examples

### Filter a list of IPs
```python
ips = ["192.168.1.1", "256.1.1.1", "10.0.0.1"]
valid_ips = [ip for ip in ips if is_valid_ipv4(ip)]
# Result: ["192.168.1.1", "10.0.0.1"]
```

### Validate network config
```python
def check_network(ip, gateway, subnet):
    return all(is_valid_ipv4(addr) for addr in [ip, gateway, subnet])

if check_network("192.168.1.100", "192.168.1.1", "255.255.255.0"):
    print("Network config OK")
```

### Handle bytes input
```python
# Works with bytes (is_valid_ipv4 only)
is_valid_ipv4(b"192.168.1.1")  # True
```

## Files Included

| File | Purpose |
|------|---------|
| `ipv4_validator.py` | Main module - the validator functions |
| `test_ipv4_validator.py` | 30+ comprehensive tests (pytest) |
| `ipv4_examples.py` | 7 usage examples |
| `run_tests.py` | Simple test runner |
| `IPv4_VALIDATOR_README.md` | Full documentation |
| `IPv4_QUICK_START.md` | This file |

## Run Examples

```bash
# Run usage examples
python ipv4_examples.py

# Run tests
python run_tests.py              # Simple test runner
pytest test_ipv4_validator.py    # Full pytest suite
```

## Key Features

✓ Validates IPv4 addresses correctly (0.0.0.0 - 255.255.255.255)
✓ Rejects leading zeros (prevents octal interpretation)
✓ Handles edge cases (whitespace, bytes, wrong types)
✓ Two implementations: explicit (recommended) and regex
✓ Comprehensive test coverage
✓ Zero dependencies
✓ Clear documentation with examples

## Function Signatures

```python
def is_valid_ipv4(address: Union[str, bytes]) -> bool:
    """Main validator - recommended for general use."""
    ...

def is_valid_ipv4_regex(address: str) -> bool:
    """Regex-based validator - alternative implementation."""
    ...
```

## Performance

- Time: O(n) where n = string length
- Space: O(1) - constant memory
- Both implementations similarly efficient

## Support

For detailed documentation, see `IPv4_VALIDATOR_README.md`
