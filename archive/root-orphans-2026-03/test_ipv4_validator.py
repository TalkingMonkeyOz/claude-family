"""Tests for IPv4 address validation functions."""

import pytest
from ipv4_validator import is_valid_ipv4, is_valid_ipv4_regex


class TestIsValidIPv4:
    """Test cases for is_valid_ipv4 function."""

    # Valid addresses
    def test_valid_simple_address(self):
        assert is_valid_ipv4("192.168.1.1") is True

    def test_valid_max_address(self):
        assert is_valid_ipv4("255.255.255.255") is True

    def test_valid_min_address(self):
        assert is_valid_ipv4("0.0.0.0") is True

    def test_valid_mixed_octets(self):
        assert is_valid_ipv4("10.20.30.40") is True

    def test_valid_single_digit_octets(self):
        assert is_valid_ipv4("1.2.3.4") is True

    def test_valid_with_leading_zeros_edge_case(self):
        # "0.0.0.0" is valid, but "01" has leading zero and is invalid
        assert is_valid_ipv4("0.0.0.0") is True

    # Invalid - octet out of range
    def test_invalid_first_octet_too_large(self):
        assert is_valid_ipv4("256.1.1.1") is False

    def test_invalid_second_octet_too_large(self):
        assert is_valid_ipv4("192.256.1.1") is False

    def test_invalid_third_octet_too_large(self):
        assert is_valid_ipv4("192.168.256.1") is False

    def test_invalid_fourth_octet_too_large(self):
        assert is_valid_ipv4("192.168.1.256") is False

    def test_invalid_all_octets_too_large(self):
        assert is_valid_ipv4("300.300.300.300") is False

    # Invalid - wrong number of octets
    def test_invalid_too_few_octets(self):
        assert is_valid_ipv4("192.168.1") is False

    def test_invalid_too_many_octets(self):
        assert is_valid_ipv4("192.168.1.1.1") is False

    def test_invalid_only_one_octet(self):
        assert is_valid_ipv4("192") is False

    def test_invalid_empty_string(self):
        assert is_valid_ipv4("") is False

    # Invalid - empty octets
    def test_invalid_missing_first_octet(self):
        assert is_valid_ipv4(".168.1.1") is False

    def test_invalid_missing_middle_octet(self):
        assert is_valid_ipv4("192..1.1") is False

    def test_invalid_missing_last_octet(self):
        assert is_valid_ipv4("192.168.1.") is False

    def test_invalid_consecutive_dots(self):
        assert is_valid_ipv4("192.168..1") is False

    # Invalid - non-numeric characters
    def test_invalid_with_letters(self):
        assert is_valid_ipv4("192.168.a.1") is False

    def test_invalid_with_special_characters(self):
        assert is_valid_ipv4("192.168.1!1") is False

    def test_invalid_with_spaces(self):
        assert is_valid_ipv4("192.168. 1.1") is False

    # Invalid - leading zeros
    def test_invalid_leading_zero_first_octet(self):
        assert is_valid_ipv4("01.168.1.1") is False

    def test_invalid_leading_zero_middle_octet(self):
        assert is_valid_ipv4("192.001.1.1") is False

    def test_invalid_leading_zero_last_octet(self):
        assert is_valid_ipv4("192.168.1.01") is False

    def test_valid_single_zero(self):
        # Single "0" is valid, not a leading zero
        assert is_valid_ipv4("0.0.0.0") is True

    # Invalid - wrong types
    def test_invalid_none(self):
        assert is_valid_ipv4(None) is False

    def test_invalid_integer(self):
        assert is_valid_ipv4(192) is False

    def test_invalid_float(self):
        assert is_valid_ipv4(192.168) is False

    def test_invalid_list(self):
        assert is_valid_ipv4([192, 168, 1, 1]) is False

    # Valid - bytes input
    def test_valid_bytes_input(self):
        assert is_valid_ipv4(b"192.168.1.1") is True

    def test_invalid_non_utf8_bytes(self):
        assert is_valid_ipv4(b"\xff\xfe") is False

    # Whitespace handling
    def test_valid_with_leading_whitespace(self):
        assert is_valid_ipv4("  192.168.1.1") is True

    def test_valid_with_trailing_whitespace(self):
        assert is_valid_ipv4("192.168.1.1  ") is True

    def test_valid_with_surrounding_whitespace(self):
        assert is_valid_ipv4("  192.168.1.1  ") is True

    # Edge cases
    def test_invalid_negative_octet(self):
        assert is_valid_ipv4("-1.0.0.0") is False

    def test_invalid_very_large_octet(self):
        assert is_valid_ipv4("999.999.999.999") is False

    def test_invalid_float_octet(self):
        assert is_valid_ipv4("192.168.1.1.5") is False


class TestIsValidIPv4Regex:
    """Test cases for is_valid_ipv4_regex function."""

    def test_valid_simple_address(self):
        assert is_valid_ipv4_regex("192.168.1.1") is True

    def test_valid_max_address(self):
        assert is_valid_ipv4_regex("255.255.255.255") is True

    def test_valid_min_address(self):
        assert is_valid_ipv4_regex("0.0.0.0") is True

    def test_invalid_too_many_octets(self):
        assert is_valid_ipv4_regex("192.168.1.1.1") is False

    def test_invalid_too_few_octets(self):
        assert is_valid_ipv4_regex("192.168.1") is False

    def test_invalid_octet_too_large(self):
        assert is_valid_ipv4_regex("256.1.1.1") is False

    def test_invalid_with_letters(self):
        assert is_valid_ipv4_regex("192.168.a.1") is False

    def test_invalid_non_string(self):
        assert is_valid_ipv4_regex(192) is False

    def test_invalid_empty_string(self):
        assert is_valid_ipv4_regex("") is False


class TestComparison:
    """Compare the two implementations."""

    test_cases = [
        ("192.168.1.1", True),
        ("255.255.255.255", True),
        ("0.0.0.0", True),
        ("256.1.1.1", False),
        ("192.168.1", False),
        ("192.168.1.1.1", False),
        ("01.1.1.1", False),
        ("", False),
        ("192.168..1", False),
    ]

    @pytest.mark.parametrize("address,expected", test_cases)
    def test_both_implementations_agree(self, address, expected):
        assert is_valid_ipv4(address) == expected
        assert is_valid_ipv4_regex(address) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
