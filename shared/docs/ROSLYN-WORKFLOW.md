# Roslyn MCP - Mandatory Validation Workflow

**Purpose**: Enforce Roslyn MCP validation for ALL C# code to prevent errors, hallucinations, and wasted time.

---

## 🚨 THE RULE

**"All C# code suggestions must be validated with Roslyn MCP before presenting."**

This is **NON-NEGOTIABLE** for C# projects (Claude PM, Nimbus User Loader).

---

## 📋 The 6-Step Workflow

```
1. RESEARCH    → Use Context7 for unfamiliar APIs
2. ANALYZE     → Run Roslyn BEFORE editing (understand structure)
3. IMPLEMENT   → Make code changes based on analysis
4. VALIDATE    → Run Roslyn again (catch new errors)
5. LOG         → Output validation results in response
6. PRESENT     → Show code to user only after validation
```

---

## 🔧 Roslyn MCP Tools

### `mcp__roslyn__ValidateFile`
**Purpose**: Validate C# file for syntax errors, semantic issues, and compiler warnings

**Usage**:
```
mcp__roslyn__ValidateFile /path/to/file.cs
```

**When to Use**:
- BEFORE editing any .cs file (understand structure first)
- AFTER making changes (verify no new errors)
- When asked "where is X used?" (FindUsages shows references)

### `mcp__roslyn__FindUsages`
**Purpose**: Locate all usages of a symbol across the project

**Usage**:
```
mcp__roslyn__FindUsages /path/to/file.cs line column
```

**When to Use**:
- Before renaming or deleting code (check what depends on it)
- Understanding code dependencies
- Refactoring safely

---

## 📝 Audit Trail Format

Claude **MUST** log validation results in responses:

```
✅ ROSLYN VALIDATION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 MainForm.cs
   Errors: 0
   Warnings: 2 (CA1031, IDE0051)

📁 ViewModel.cs
   Errors: 0
   Warnings: 0
   ✓ Clean

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Timestamp: 2025-10-29 14:23:45
STATUS: ✅ All files validated - ready to present
```

This creates **verifiable compliance** - user can see Claude followed the process.

---

## 🎯 Context7 Usage

### When to Use Context7
- Researching unfamiliar WPF/WinForms/MVVM patterns
- Before implementing features with new APIs
- Debugging version-specific issues

### Library IDs (Specific, Not Vague)

**Claude PM (WPF):**
```
use library /dotnet/wpf topic "data-binding"
use library /dotnet/mvvm topic "commands"
use library /modernwpf/modernwpf
use library /communitytoolkit/mvvm
```

**Nimbus (WinForms):**
```
use library /dotnet/winforms topic "threading"
use library /dotnet/csharp topic "async-await"
use library /npgsql/npgsql
```

### Security Rule
**NEVER** use Context7 for:
- Claude PM internal APIs
- Nimbus internal APIs
- ATO tax logic
- Proprietary business logic

Context7 queries go to external Upstash API - safe for PUBLIC frameworks only.

---

## ⚙️ 5-Layer Enforcement Strategy

### Layer 1: Documentation (CLAUDE.md)
- Mandatory workflow at lines 7-20 (impossible to miss)
- Loaded automatically when opening project

### Layer 2: Convenience (/validate-csharp)
- Slash command: Type `/validate-csharp` to validate all modified files
- Makes compliance easy, reduces friction

### Layer 3: Visibility (Audit Trail)
- Claude outputs validation results in responses
- User can verify process was followed
- Creates traceable audit log

### Layer 4: Configuration (.editorconfig)
- Roslyn analyzers enforced at IDE level
- FxCop, StyleCop for style and safety
- Catches issues during development

### Layer 5: Safety Net (git pre-commit hook)
- Runs Roslyn validation on staged .cs files
- Fails commit if errors found
- Ensures nothing gets committed without validation

---

## 🚫 When to Skip Roslyn

**Skip ONLY for:**
- Design discussions (pseudocode, no actual code)
- Architecture planning
- Non-C# files

**DO NOT skip for:**
- "Small" edits (they cause bugs too!)
- "Quick" fixes (that's when mistakes happen)
- "I'll validate later" (won't happen)

---

## 📚 Real Failure Example

**Session 2025-10-28** (Nimbus User Loader):
- Problem: Duplicate `InitializeComponent()` method
- Time wasted: 6 hours debugging build errors
- Root cause: Roslyn `FindUsages` not used BEFORE editing
- Impact: User frustration, lost productivity
- Lesson: Roslyn would have caught it in **seconds**

**This is why validation is MANDATORY.**

---

## 🎓 Best Practices from Research

### From Anthropic Docs:
- Use project-scope MCP configs for team-shared tools
- Leverage slash commands for repeated workflows
- Use `--mcp-debug` flag for troubleshooting

### From Roslyn MCP Docs:
- Use `--runAnalyzers` flag for FxCop/StyleCop enforcement
- Integrate into CI/CD pipeline for automated validation
- Real-time feedback prevents issues before commit

### From Context7 Docs:
- Specify exact library IDs (not vague "use context7")
- Use topic parameter for focused documentation
- Token configuration: default 10000, adjust as needed

---

## 🔗 Related Documentation

- **Full C# Guide**: `C:\claude\shared\docs\csharp-desktop-mcp-guide.md` (606 lines)
- **MCP Configuration**: `C:\Projects\claude-family\docs\MCP_CONFIGURATION_GUIDE.md`
- **Family Rules**: (coming soon) `C:\claude\shared\docs\family-rules.md`

---

**Created**: 2025-10-29
**Applies To**: claude-pm, nimbus-user-loader (all C# projects)
**Confidence**: 10/10 (research-backed, failure-tested)
