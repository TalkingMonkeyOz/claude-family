#!/usr/bin/env python
"""Examples and use cases for IPv4 validator."""

from ipv4_validator import is_valid_ipv4, is_valid_ipv4_regex


def example_basic_validation():
    """Example 1: Basic validation of a single address."""
    print("=" * 70)
    print("Example 1: Basic Validation")
    print("=" * 70)

    addresses = [
        "192.168.1.1",
        "256.1.1.1",
        "10.0.0.1",
        "not_an_ip"
    ]

    for addr in addresses:
        valid = is_valid_ipv4(addr)
        status = "✓ Valid" if valid else "✗ Invalid"
        print(f"  {addr:20} {status}")

    print()


def example_filter_addresses():
    """Example 2: Filter valid addresses from a list."""
    print("=" * 70)
    print("Example 2: Filter Valid Addresses")
    print("=" * 70)

    all_addresses = [
        "192.168.1.1",
        "172.16.0.1",
        "256.256.256.256",
        "10.0.0.0",
        "01.0.0.0",
        "8.8.8.8",
        "invalid_ip",
        "127.0.0.1"
    ]

    valid_ips = [ip for ip in all_addresses if is_valid_ipv4(ip)]

    print(f"  Input addresses: {len(all_addresses)}")
    print(f"  Valid addresses: {len(valid_ips)}")
    print(f"  Valid IPs: {valid_ips}")

    print()


def example_network_validation():
    """Example 3: Validate network configuration."""
    print("=" * 70)
    print("Example 3: Network Configuration Validation")
    print("=" * 70)

    configs = [
        {"ip": "192.168.1.100", "gateway": "192.168.1.1", "subnet": "255.255.255.0"},
        {"ip": "256.1.1.1", "gateway": "192.168.1.1", "subnet": "255.255.255.0"},
        {"ip": "192.168.1.100", "gateway": "invalid", "subnet": "255.255.255.0"},
    ]

    for i, config in enumerate(configs, 1):
        all_valid = all(is_valid_ipv4(v) for v in config.values())
        status = "✓ Valid" if all_valid else "✗ Invalid"
        print(f"  Config {i}: {status}")
        for key, value in config.items():
            valid = is_valid_ipv4(value)
            indicator = "✓" if valid else "✗"
            print(f"    {key:10} {value:20} {indicator}")

    print()


def example_user_input_validation():
    """Example 4: Validate user input with user-friendly messages."""
    print("=" * 70)
    print("Example 4: User Input Validation with Messages")
    print("=" * 70)

    def validate_ip_with_message(user_input):
        """Validate IP and provide helpful feedback."""
        if not user_input:
            return False, "Please enter an IP address"

        if is_valid_ipv4(user_input):
            return True, f"✓ {user_input} is a valid IPv4 address"
        else:
            # Provide some hints about why it's invalid
            if '.' not in user_input:
                return False, f"✗ Missing dots (expected format: 255.255.255.255)"
            elif user_input.count('.') != 3:
                return False, f"✗ Wrong number of octets (found {user_input.count('.') + 1}, expected 4)"
            else:
                return False, f"✗ {user_input} is not a valid IPv4 address"

    test_inputs = [
        "192.168.1.1",
        "256.1.1.1",
        "192.168.1",
        "not.an.ip.address",
        ""
    ]

    for user_input in test_inputs:
        valid, message = validate_ip_with_message(user_input)
        print(f"  Input: {user_input:20} → {message}")

    print()


def example_comparison():
    """Example 5: Compare both implementations."""
    print("=" * 70)
    print("Example 5: Comparing Both Implementations")
    print("=" * 70)

    test_cases = [
        "192.168.1.1",
        "255.255.255.255",
        "256.1.1.1",
        "192.168.1",
        "",
    ]

    print(f"  {'Input':<20} {'is_valid_ipv4':<20} {'is_valid_ipv4_regex':<20}")
    print("  " + "-" * 60)

    for test in test_cases:
        result1 = is_valid_ipv4(test)
        result2 = is_valid_ipv4_regex(test)
        print(f"  {str(test):<20} {str(result1):<20} {str(result2):<20}")

    print()


def example_special_addresses():
    """Example 6: Special IP addresses."""
    print("=" * 70)
    print("Example 6: Special IP Addresses")
    print("=" * 70)

    special_ips = {
        "0.0.0.0": "Default/Unspecified",
        "127.0.0.1": "Localhost/Loopback",
        "255.255.255.255": "Broadcast",
        "192.168.0.0": "Private Class A",
        "172.16.0.0": "Private Class B",
        "10.0.0.0": "Private Class C",
        "224.0.0.0": "Multicast",
        "169.254.0.0": "Link-Local",
    }

    for ip, description in special_ips.items():
        valid = is_valid_ipv4(ip)
        status = "✓" if valid else "✗"
        print(f"  {status} {ip:20} {description}")

    print()


def example_error_cases():
    """Example 7: Common error cases."""
    print("=" * 70)
    print("Example 7: Common Error Cases and Why They Fail")
    print("=" * 70)

    error_cases = {
        "256.1.1.1": "Octet > 255",
        "192.168.1": "Too few octets (3 instead of 4)",
        "192.168.1.1.1": "Too many octets (5 instead of 4)",
        "192.168.a.1": "Non-numeric character 'a'",
        "01.168.1.1": "Leading zero in octet",
        "192.168. 1.1": "Space in octet",
        "-1.0.0.0": "Negative number",
        "192.168.1.": "Trailing dot/missing octet",
        ".192.168.1": "Leading dot/missing octet",
        "": "Empty string",
    }

    for ip, reason in error_cases.items():
        valid = is_valid_ipv4(ip)
        print(f"  '{ip}' → Invalid because: {reason}")

    print()


if __name__ == "__main__":
    print("\n")
    print("IPv4 Validator - Usage Examples")
    print("=" * 70)
    print()

    example_basic_validation()
    example_filter_addresses()
    example_network_validation()
    example_user_input_validation()
    example_comparison()
    example_special_addresses()
    example_error_cases()

    print("=" * 70)
    print("Examples completed!")
    print("=" * 70)
