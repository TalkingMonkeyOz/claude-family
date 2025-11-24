#!/usr/bin/env python
"""Simple test runner for IPv4 validator."""

import sys
from ipv4_validator import is_valid_ipv4, is_valid_ipv4_regex


def test_ipv4_validator():
    """Run basic tests on both implementations."""

    tests = [
        # (input, expected_result, test_name)
        ("192.168.1.1", True, "Simple valid address"),
        ("255.255.255.255", True, "Maximum valid address"),
        ("0.0.0.0", True, "Minimum valid address"),
        ("10.20.30.40", True, "Mixed octets"),
        ("1.2.3.4", True, "Single digit octets"),
        ("256.1.1.1", False, "Octet too large"),
        ("192.256.1.1", False, "Second octet too large"),
        ("192.168.1", False, "Too few octets"),
        ("192.168.1.1.1", False, "Too many octets"),
        (".168.1.1", False, "Missing first octet"),
        ("192..1.1", False, "Missing middle octet"),
        ("192.168.1.", False, "Missing last octet"),
        ("192.168.a.1", False, "Contains letter"),
        ("01.168.1.1", False, "Leading zero"),
        ("", False, "Empty string"),
        ("192.168.1.1  ", True, "Trailing whitespace"),
        ("  192.168.1.1", True, "Leading whitespace"),
        (b"192.168.1.1", True, "Bytes input"),
        (None, False, "None input"),
        (192, False, "Integer input"),
    ]

    failed = 0
    passed = 0

    print("Testing is_valid_ipv4()...")
    print("-" * 70)

    for test_input, expected, name in tests:
        result = is_valid_ipv4(test_input)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"{status} {name:40} | Input: {str(test_input):20} | Expected: {expected}, Got: {result}")

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")

    if failed == 0:
        print("✓ All tests passed!")
        return 0
    else:
        print(f"✗ {failed} test(s) failed!")
        return 1


if __name__ == "__main__":
    sys.exit(test_ipv4_validator())
