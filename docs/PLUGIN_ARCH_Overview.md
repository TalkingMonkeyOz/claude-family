# Claude Family Plugin Architecture - Overview

## Executive Summary

**Objective:** Build a layered plugin system that provides:
1. Universal coordination tools for all Claude instances
2. Project-type specific tooling (web, desktop, python, etc.)
3. Project-specific customizations
4. Consistent experience across spawned agents
5. Easy installation, updates, and sharing

**Timeline:** 4-8 hours initial build, ongoing maintenance
**Stakeholders:** All Claude Family members (Mission Control, ATO, Nimbus, future projects)
**ROI:** 2-3 hours saved per project setup, consistent tooling across family

---

## Architecture Overview

### Three-Layer Plugin Hierarchy:

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Universal Core (claude-family-core)          │
│  - Installed on EVERY Claude instance                  │
│  - Session management, feedback, orchestration         │
│  - Core database schemas (claude_family, claude_pm)    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Project Type Toolkits                        │
│  - web-dev-toolkit (Next.js, React, shadcn)           │
│  - python-dev-toolkit (FastAPI, pytest, black)        │
│  - desktop-dev-toolkit (Electron, Tauri)              │
│  - Installed on relevant projects only                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Project-Specific Plugins                     │
│  - mission-control-tools                               │
│  - ato-tax-tools                                       │
│  - nimbus-loader-tools                                 │
│  - Installed on single project only                    │
└─────────────────────────────────────────────────────────┘
```

---

## Document Organization

This architecture is documented across 4 focused files:

1. **[[PLUGIN_ARCH_Overview]]** (this file)
   - Executive summary and high-level architecture

2. **[[PLUGIN_ARCH_Layers]]**
   - Detailed specifications for all 3 plugin layers
   - Component details, configuration, commands

3. **[[PLUGIN_ARCH_Implementation]]**
   - Distribution and installation procedures
   - Phase-by-phase implementation plan
   - Benefits analysis and technical considerations

4. **[[PLUGIN_ARCH_Success]]**
   - Success metrics and testing approach
   - Recommended next steps
   - Long-term vision and conclusion

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/PLUGIN_ARCH_Overview.md
