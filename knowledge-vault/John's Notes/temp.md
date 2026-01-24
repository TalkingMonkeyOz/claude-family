
### Claude Manager Mui Feature Vision

- Currently have an “agent constructor” but it doesn’t match the original product vision
- Desired outcome is a **single, comprehensive configuration experience** for Claude Manager startup, driven through a UI
- Configuration should be:
    - **End-to-end**: covers everything involved in starting up Claude Manager
    - **Composable**: users can see and adjust all pieces, not just a few presets
    - **Understandable**: structure and dependencies between components are clear
- Strong emphasis on **natural language controls**:
    - Users describe desired behavior and constraints in plain language
    - System translates this into concrete config (documents, hooks, programs, etc.)
    - Iterative refinement: user can adjust in natural language and see updated artifacts
- UI should expose the ability to **view and modify generated artifacts**:
    - `Claude.md` (core behavior / personality / operating guide)
    - `globalclaw.md` / global configuration documents
    - Skills definitions
    - Rules and constraints
    - Any other startup components that affect behavior
- Control should extend down to **low-level execution plumbing**:
    - Hooks configuration
    - Programs referenced by hooks
    - Overall execution graph (what runs when, under what conditions)

### Orchestration System Requirements

- Initial intent was **not** to build “a full orchestration system”
    - That assumption is now considered wrong; a full orchestration layer is actually what’s needed
- New target is a **fully orchestrated system** that:
    - Treats all startup components (docs, skills, rules, hooks, programs) as part of a single orchestrated configuration
    - Can be **configured, inspected, and modified** through the UI and natural language
    - Supports **reproducible setups** (save/restore/share configurations)
    - Makes it easy to reason about what will happen when Claude Manager starts
- Current state:
    - System is **much improved** compared to a year ago
    - There is still a **significant gap** between current capabilities and the fully-orchestrated vision
- Directional shift:
    - Full orchestration is now a **primary product objective**, not a stretch goal or “later” feature

### Implementation Approach

- Implement this orchestration and configuration experience **inside Claude Manager Mui**
- Reuse and integrate **all recently developed components and capabilities**:
    - Existing agent constructor work where it fits
    - Existing hooks and program systems
    - Existing document and skills infrastructure
- Treat this feature as a **stress test of the current stack**:
    - Push the boundaries of what the current system can express and manage
    - Identify gaps in orchestration, configuration, and developer ergonomics
- Outcome goal:
    - A concrete, UI-driven orchestration feature that demonstrates the **end-state vision** and guides future refactors and platform work