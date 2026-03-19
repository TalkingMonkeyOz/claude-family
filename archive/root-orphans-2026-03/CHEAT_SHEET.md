# IPv4 Validator - Cheat Sheet

Quick reference for the most common use cases.

---

## 🚀 Import & Use (30 seconds)

```python
from ipv4_validator import is_valid_ipv4

# That's it!
result = is_valid_ipv4("192.168.1.1")  # True or False
```

---

## ✅ Valid Examples

```python
is_valid_ipv4("192.168.1.1")        # ✓ True
is_valid_ipv4("0.0.0.0")            # ✓ True
is_valid_ipv4("255.255.255.255")    # ✓ True
is_valid_ipv4("10.0.0.1")           # ✓ True
is_valid_ipv4("127.0.0.1")          # ✓ True
is_valid_ipv4("8.8.8.8")            # ✓ True
is_valid_ipv4(b"192.168.1.1")       # ✓ True (bytes)
is_valid_ipv4("  192.168.1.1  ")    # ✓ True (whitespace)
```

---

## ❌ Invalid Examples

```python
is_valid_ipv4("256.1.1.1")          # ✗ False (octet > 255)
is_valid_ipv4("192.168.1")          # ✗ False (only 3 octets)
is_valid_ipv4("192.168.1.1.1")      # ✗ False (5 octets)
is_valid_ipv4("01.168.1.1")         # ✗ False (leading zero)
is_valid_ipv4("192.168.a.1")        # ✗ False (letter)
is_valid_ipv4("-1.0.0.0")           # ✗ False (negative)
is_valid_ipv4("192.168..1")         # ✗ False (missing octet)
is_valid_ipv4("")                   # ✗ False (empty)
is_valid_ipv4(None)                 # ✗ False (None)
is_valid_ipv4(192)                  # ✗ False (int)
```

---

## 🎯 Common Patterns

### Check Single IP
```python
if is_valid_ipv4(user_input):
    print("Valid!")
else:
    print("Invalid!")
```

### Filter List
```python
valid_ips = [ip for ip in ips if is_valid_ipv4(ip)]
```

### Validate All in List
```python
all_valid = all(is_valid_ipv4(ip) for ip in ips)
```

### Validate Dictionary Values
```python
config_valid = all(
    is_valid_ipv4(v) for v in config.values()
)
```

### With Error Message
```python
if is_valid_ipv4(ip):
    process(ip)
else:
    raise ValueError(f"Invalid IP: {ip}")
```

### Flask/API Integration
```python
@app.route('/config', methods=['POST'])
def config():
    ip = request.json.get('ip')
    if not is_valid_ipv4(ip):
        return {'error': 'Invalid IP'}, 400
    return setup(ip)
```

---

## 📋 Rules at a Glance

| Rule | Examples |
|------|----------|
| **4 Octets** | ✓ `192.168.1.1` ✗ `192.168.1` |
| **Range 0-255** | ✓ `255.255.255.255` ✗ `256.1.1.1` |
| **Numeric Only** | ✓ `192.168.1.1` ✗ `192.168.a.1` |
| **No Leading 0s** | ✓ `0.0.0.0` ✗ `01.1.1.1` |
| **Separated by .** | ✓ `192.168.1.1` ✗ `192-168-1-1` |

---

## 🔄 String vs Bytes

```python
# Both work with is_valid_ipv4()
is_valid_ipv4("192.168.1.1")        # String ✓
is_valid_ipv4(b"192.168.1.1")       # Bytes ✓

# Regex alternative only handles strings
from ipv4_validator import is_valid_ipv4_regex
is_valid_ipv4_regex("192.168.1.1")  # String ✓
is_valid_ipv4_regex(b"192.168.1.1") # Bytes ✗
```

---

## 🧮 Special Addresses

| Address | Purpose | Valid? |
|---------|---------|--------|
| `0.0.0.0` | Default/Unspecified | ✓ |
| `127.0.0.1` | Loopback | ✓ |
| `255.255.255.255` | Broadcast | ✓ |
| `192.168.0.0` | Private (Class A) | ✓ |
| `172.16.0.0` | Private (Class B) | ✓ |
| `10.0.0.0` | Private (Class C) | ✓ |
| `224.0.0.0` | Multicast | ✓ |
| `169.254.0.0` | Link-Local | ✓ |

---

## ⚡ Performance

```
Input Size:     ~20 characters (typical IP)
Time:           < 1 microsecond
Memory:         Negligible
```

---

## 📦 Two Functions

### Main Function (Recommended)
```python
is_valid_ipv4(address: Union[str, bytes]) -> bool

# Features:
# - Handles strings AND bytes
# - Strips whitespace
# - Type-safe
# - Rejects leading zeros
# - More flexible
```

### Regex Alternative
```python
is_valid_ipv4_regex(address: str) -> bool

# Features:
# - Concise (10 lines)
# - Pattern-based
# - Strings only
# - Still validates correctly
```

---

## 🔧 Customize Error Messages

```python
def validate_with_error(ip):
    if not ip:
        return "Please enter an IP address"

    if not is_valid_ipv4(ip):
        if '.' not in ip:
            return "Missing dots (format: XXX.XXX.XXX.XXX)"
        if ip.count('.') != 3:
            return f"Wrong number of octets"
        return f"Invalid IP: {ip}"

    return None  # Valid
```

---

## 📊 Quick Decision Tree

```
Is it a string?
├─ YES → Can handle it
├─ NO (bytes)
│   └─ Use is_valid_ipv4() (it decodes bytes)
├─ NO (int/None/list)
│   └─ Will return False
│
Format looks like X.X.X.X?
├─ YES → Check if valid
├─ NO → Will return False
│
Each X is 0-255?
├─ YES → Will return True
├─ NO → Will return False
│
Has leading zeros (01.X.X.X)?
├─ YES → Will return False
├─ NO → Might be valid
│
No other issues?
├─ YES → Returns True ✓
├─ NO → Returns False ✗
```

---

## 🚨 Common Mistakes

```python
# ❌ Wrong: String is None
is_valid_ipv4(None)                 # False, not error

# ❌ Wrong: Type instead of value
is_valid_ipv4(IPAddress("192.168.1.1"))  # Might fail

# ❌ Wrong: Forgetting to strip
user_ip = input() + "\n"            # Has newline
is_valid_ipv4(user_ip)              # False

# ✓ Right: Let is_valid_ipv4 strip it
user_ip = input()                   # Already stripped
is_valid_ipv4(user_ip)              # Works

# ✓ Right: Manual strip for other spaces
is_valid_ipv4(user_ip.strip())      # Explicit

# ✓ Right: Check for None first
if user_ip and is_valid_ipv4(user_ip):
    process(user_ip)
```

---

## 🔀 Alternatives

```python
# Option 1: This module (simple, no deps)
from ipv4_validator import is_valid_ipv4

# Option 2: Standard library (comprehensive)
import ipaddress
try:
    ipaddress.IPv4Address("192.168.1.1")
    valid = True
except:
    valid = False

# Option 3: Regex yourself (if you prefer)
import re
pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
valid = bool(re.match(pattern, ip))
```

---

## 📚 Documentation Files

| File | Purpose | Read Time |
|------|---------|-----------|
| CHEAT_SHEET.md | This file | 2 min |
| IPv4_QUICK_START.md | Copy-paste examples | 5 min |
| IPv4_VALIDATOR_README.md | Complete reference | 15 min |
| IPv4_DEVELOPER_GUIDE.md | Deep technical dive | 20 min |

---

## 🎯 Copy-Paste Solutions

### Validate User Input
```python
from ipv4_validator import is_valid_ipv4

user_ip = input("Enter IP: ").strip()
if is_valid_ipv4(user_ip):
    print("Valid!")
    process(user_ip)
else:
    print("Invalid IP format!")
```

### Validate Configuration
```python
from ipv4_validator import is_valid_ipv4

config = {
    'ip': '192.168.1.100',
    'gateway': '192.168.1.1',
    'dns': '8.8.8.8'
}

if all(is_valid_ipv4(v) for v in config.values()):
    print("Config OK")
else:
    print("Invalid IP in config")
```

### Filter Log File
```python
from ipv4_validator import is_valid_ipv4
import re

def extract_ip(line):
    match = re.search(r'\d+\.\d+\.\d+\.\d+', line)
    return match.group(0) if match else None

with open('access.log') as f:
    valid_lines = [line for line in f
                   if is_valid_ipv4(extract_ip(line) or '')]
```

---

## ✅ Checklist

- ✓ Import `is_valid_ipv4`
- ✓ Call with string or bytes
- ✓ Get True or False back
- ✓ No exceptions thrown
- ✓ No dependencies needed
- ✓ Works with standard library only

---

## 🎓 Learning Path

**5 minutes:**
1. Copy this cheat sheet
2. Try 2-3 examples
3. Integrate into your code

**15 minutes:**
1. Read IPv4_QUICK_START.md
2. Try more examples
3. Run ipv4_examples.py

**30 minutes:**
1. Read IPv4_VALIDATOR_README.md
2. Review test_ipv4_validator.py
3. Understand edge cases

**60 minutes:**
1. Read IPv4_DEVELOPER_GUIDE.md
2. Study the implementation
3. Consider extensions (IPv6, CIDR)

---

**That's all you need!** 🎉

For more, see: `IPv4_QUICK_START.md`
