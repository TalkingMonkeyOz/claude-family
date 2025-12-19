#!/usr/bin/env python3
"""
Simple script to print today's date in YYYY-MM-DD format.
"""

from datetime import date

def main():
    """Print today's date in YYYY-MM-DD format."""
    today = date.today()
    print(today.strftime("%Y-%m-%d"))

if __name__ == "__main__":
    main()
