---
projects:
  - monash-nimbus-reports
  - nimbus-mui
tags:
  - pattern/build
  - tech/tauri
  - tech/rust
synced: false
---

# Tauri Cross-Platform Build Pattern

Set up a Tauri app for Windows and macOS builds from a single codebase.

---

## Key Principle

Tauri compiles to native binaries - **cannot cross-compile**. Use CI/CD to build each platform on its native runner.

---

## Required Changes

### 1. Cargo.toml - Conditional Dependencies

```toml
[target.'cfg(target_os = "windows")'.dependencies]
keyring = { version = "3", features = ["windows-native"] }

[target.'cfg(target_os = "macos")'.dependencies]
keyring = { version = "3", features = ["apple-native"] }
```

### 2. tauri.conf.json - Bundle Targets

```json
{
  "bundle": {
    "targets": "all",
    "macOS": { "minimumSystemVersion": "10.13" },
    "windows": {}
  }
}
```

### 3. main.rs - Conditional Directive

```rust
#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]
```

### 4. GitHub Actions

Use `dtolnay/rust-toolchain@stable` (not `rust-action`).

Add `permissions: contents: write` for release creation.

Matrix: `windows-latest`, `macos-latest` (x86_64 + aarch64).

---

## Build Output

| Platform | Files |
|----------|-------|
| Windows | `.exe`, `.msi`, `.nsis` |
| macOS | `.app`, `.dmg` |

---

## Triggering Builds

```bash
git tag vX.Y.Z && git push origin vX.Y.Z
```

Tag push triggers workflow → builds appear in GitHub Releases.

---

## Common Issues

| Issue | Solution |
|-------|----------|
| `Unable to resolve dtolnay/rust-action` | Use `dtolnay/rust-toolchain` |
| Release creation fails | Add `permissions: contents: write` |
| Keyring build fails | Check platform-specific features |

---

**Version**: 1.0
**Created**: 2026-01-27
**Updated**: 2026-01-27
**Location**: knowledge-vault/30-Patterns/Tauri Cross-Platform Build Pattern.md
