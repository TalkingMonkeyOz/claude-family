# Claude Family Plugin Architecture - Implementation Plan

See [[PLUGIN_ARCH_Overview]] for introduction and architecture overview.

---

## Plugin Distribution & Installation

### Marketplace Structure:

```
C:\claude\plugins\marketplace\
├── universal/
│   └── claude-family-core\
├── web-dev/
│   └── web-dev-toolkit\
├── python-dev/
│   └── python-dev-toolkit\
├── desktop-dev/
│   └── desktop-dev-toolkit\
├── mission-control/
│   └── mission-control-tools\
├── ato/
│   └── ato-tax-tools\
└── nimbus/
    └── nimbus-loader-tools\
```

### Installation Commands:

```bash
# On Mission Control Claude
/plugin install claude-family-core
/plugin install web-dev-toolkit
/plugin install mission-control-tools

# On ATO Claude
/plugin install claude-family-core
/plugin install web-dev-toolkit
/plugin install ato-tax-tools

# On Nimbus Claude
/plugin install claude-family-core
/plugin install desktop-dev-toolkit  # or python-dev if Python-based
/plugin install nimbus-loader-tools
```

### Update Workflow:

```bash
# Update single plugin
/plugin update claude-family-core

# Update all plugins
/plugin update --all

# Check for updates
/plugin list --check-updates
```

---

## Implementation Plan

### Phase 1: Core Foundation (Priority 1)
**Timeline: 4-6 hours**

**Tasks:**
1. Create plugin directory structure
2. Build `claude-family-core` plugin:
   - plugin.json manifest
   - All session management commands
   - Feedback system commands
   - Orchestrator commands
   - MCP configuration
   - Basic hooks
3. Test on one Claude instance (Mission Control or yourself)
4. Document installation process
5. Create README with usage examples

**Deliverables:**
- ✅ Fully functional claude-family-core plugin
- ✅ Installation guide
- ✅ Test results from one instance

**Success Criteria:**
- /session-start works and logs to database
- /session-end captures summary
- /feedback-check displays open items
- /inbox-check shows orchestrator messages
- /team-status displays active Claudes

---

### Phase 2: Web Dev Toolkit (Priority 2)
**Timeline: 2-3 hours**

**Tasks:**
1. Create `web-dev-toolkit` plugin
2. Implement shadcn/ui helper commands
3. Implement build/deploy commands
4. Test with Mission Control or ATO project
5. Document common workflows

**Deliverables:**
- ✅ web-dev-toolkit plugin
- ✅ Integration with Next.js projects

---

### Phase 3: Project-Specific Plugins (Priority 3)
**Timeline: 2-3 hours each**

**Tasks:**
1. Create mission-control-tools
2. Create ato-tax-tools
3. Create nimbus-loader-tools
4. Test each on respective project
5. Document project-specific workflows

**Deliverables:**
- ✅ Three project-specific plugins
- ✅ Complete plugin ecosystem

---

### Phase 4: Rollout & Training (Priority 4)
**Timeline: 1-2 hours**

**Tasks:**
1. Install core plugin on all Claude instances
2. Install type-specific plugins on relevant instances
3. Install project-specific plugins
4. Create master plugin inventory
5. Document update procedures

**Deliverables:**
- ✅ All Claudes running with appropriate plugins
- ✅ Plugin inventory/map
- ✅ Update procedures documented

---

## Benefits Analysis

### For Orchestrated Agents:

**Before plugins:**
```
spawn_agent(type="coder", task="Build feature X")
→ Agent spawns with basic tools only
→ No session logging
→ No access to feedback system
→ Can't coordinate with other Claudes
→ Manual context passing needed
```

**After plugins:**
```
spawn_agent(type="coder", task="Build feature X")
→ Agent spawns in workspace with plugins
→ Auto-loads claude-family-core
→ Can use /feedback-create if finds issues
→ Can send messages via orchestrator
→ Session auto-logged
→ Has all slash commands available
```

**Impact:** Agents become 10x more capable and coordinated

---

### For New Project Setup:

**Before plugins:**
- Manual MCP configuration: 30 min
- Create slash commands: 1-2 hours
- Set up hooks: 30 min
- Configure database access: 30 min
- Document for team: 1 hour
- **Total: 3-4 hours per project**

**After plugins:**
- Install claude-family-core: 1 min
- Install project-type toolkit: 1 min
- Create project-specific plugin: 30 min (one-time)
- **Total: 5 minutes for existing types, 30 min for new types**

**ROI after 3 projects: 9-10 hours saved**

---

### For Team Coordination:

**Before plugins:**
- Inconsistent tooling across Claudes
- Manual message checking
- No standardized workflows
- Repeated setup on each instance
- Hard to share best practices

**After plugins:**
- Every Claude has same core tools
- Auto inbox checking via hooks
- Standardized workflows (/session-start, /session-end)
- One-command installation
- Plugins ARE the shared best practices

---

### For Future Scaling:

**Commercialization scenario:**
```
Customer: "How do I set up Claude to work with your ATO Tax product?"

Before: Send 10-page PDF with manual configuration steps

After: "Run: /plugin install ato-tax-toolkit"
```

**White-label potential:**
- Package plugins with your products
- Customers get professional tooling
- You can update/improve plugins remotely
- Creates ecosystem around your products

---

## Technical Considerations

### 1. MCP Server Availability

**Known MCPs (verified):**
- ✅ postgres
- ✅ filesystem
- ✅ memory
- ✅ orchestrator

**Uncertain (need to verify):**
- ❓ TypeScript/ESLint MCP
- ❓ Tailwind CSS MCP
- ❓ React/Next.js specific MCP

**Action:** Research MCP registry/marketplace for availability before finalizing .mcp.json configurations in type-specific toolkits.

**Fallback:** If MCPs don't exist, use Bash tool to run commands directly (less elegant but functional).

---

### 2. Hook Limitations

**Need to verify:**
- Can hooks run periodic tasks? (e.g., check inbox every 5 min)
- Can hooks modify Claude's context/input?
- Can hooks block tool execution?

**Research needed:** Review Claude Code hooks documentation thoroughly

**Fallback:** If periodic hooks not supported, use tool-result triggers on frequently used tools

---

### 3. Plugin Installation Flow

**Assumption:** Plugins installed via `/plugin install` command

**Need to verify:**
- Exact installation syntax
- How to specify marketplace location
- Whether multiple marketplaces supported
- Update/version management commands

**Research needed:** Review Claude Code plugin documentation

---

### 4. Spawned Agent Plugin Inheritance

**Critical question:** Do spawned agents automatically load plugins from workspace?

**Test required:** Spawn agent in workspace with plugins installed, verify if agent has access to:
- Slash commands from plugins
- MCP servers from plugins
- Hooks from plugins

**If YES:** Huge benefit, agents are immediately super-powered
**If NO:** Need to document manual plugin loading for agents

---

### 5. Database Connection Management

**Current assumption:** Single database connection string in .mcp.json

**Considerations:**
- What if different projects use different databases?
- How to handle credentials securely?
- Can plugins override parent MCP configurations?

**Solution options:**
1. Use environment variables for connection strings
2. Template connection strings with project-specific values
3. Layer MCP configs (plugin MCP extends base MCP)

**Recommended:** Environment variable approach
```json
{
  "mcpServers": {
    "postgres": {
      "command": "uvx",
      "args": ["mcp-server-postgres", "${DATABASE_URL}"]
    }
  }
}
```

---

**Version**: 2.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/PLUGIN_ARCH_Implementation.md
