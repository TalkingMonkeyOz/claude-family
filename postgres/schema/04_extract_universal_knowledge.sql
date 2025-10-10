-- ============================================================================
-- EXTRACT UNIVERSAL KNOWLEDGE - Move Cross-Project Learnings
-- ============================================================================
-- Purpose: Identify learnings from nimbus_context that apply universally
--          and copy them to claude_family.shared_knowledge
-- Date: 2025-10-10
-- ============================================================================

\c ai_company_foundation

SET search_path TO claude_family, public, nimbus_context;

-- ============================================================================
-- 1. EXTRACT UNIVERSAL PATTERNS (Apply to ALL Projects)
-- ============================================================================

DO $$
DECLARE
    v_desktop_identity_id UUID;
    v_knowledge_count INTEGER := 0;
BEGIN
    -- Get Desktop Claude's identity (who learned these)
    SELECT identity_id INTO v_desktop_identity_id
    FROM claude_family.identities
    WHERE identity_name = 'claude-desktop-001';

    -- ────────────────────────────────────────────────────────────────────
    -- Universal Knowledge 1: OneDrive Caching Build Folders
    -- ────────────────────────────────────────────────────────────────────
    INSERT INTO claude_family.shared_knowledge (
        learned_by_identity_id,
        knowledge_type,
        knowledge_category,
        title,
        description,
        applies_to_projects,
        applies_to_platforms,
        confidence_level,
        times_applied,
        code_example
    ) VALUES (
        v_desktop_identity_id,
        'gotcha',
        'onedrive',
        'OneDrive caches build folders causing stale DLL issues',
        'OneDrive Files-on-Demand with "P" (pinned) attribute caches build output folders (bin/, obj/) and serves stale versions even after fresh builds. This causes UI changes to not appear, requiring manual copy to non-OneDrive location. Solution: Unpin folders with "attrib -P" or exclude from OneDrive sync entirely.',
        ARRAY['all'],  -- Applies to all .NET projects
        ARRAY['windows'],
        9,  -- High confidence (verified)
        3,  -- Applied successfully 3 times
        E'# Check OneDrive status\nattrib "path\\to\\bin"\n\n# If shows "P" (pinned), unpin:\nattrib -P "path\\to\\bin" /S /D\nattrib -P "path\\to\\obj" /S /D\n\n# Or exclude from OneDrive:\n# Right-click OneDrive tray icon → Settings → Sync and backup → Manage backup\n# Add bin/ and obj/ to exclusion list'
    )
    ON CONFLICT DO NOTHING;
    v_knowledge_count := v_knowledge_count + 1;

    -- ────────────────────────────────────────────────────────────────────
    -- Universal Knowledge 2: MCP Server Logging Location
    -- ────────────────────────────────────────────────────────────────────
    INSERT INTO claude_family.shared_knowledge (
        learned_by_identity_id,
        knowledge_type,
        knowledge_category,
        title,
        description,
        applies_to_projects,
        applies_to_platforms,
        confidence_level,
        times_applied,
        code_example
    ) VALUES (
        v_desktop_identity_id,
        'technique',
        'mcp',
        'MCP server logs location for diagnostics',
        'MCP servers (Model Context Protocol) log to %APPDATA%\Claude\logs\ directory. Each server has its own log file (mcp-server-{name}.log). Essential for diagnosing MCP server failures. Check these logs when MCP extensions show "failed" status.',
        ARRAY['all'],
        ARRAY['windows'],
        10,  -- Certain
        5,  -- Applied many times
        E'# View MCP logs\ndir "%APPDATA%\\Claude\\logs\\mcp*.log"\n\n# Read specific server log\ntype "%APPDATA%\\Claude\\logs\\mcp-server-Windows-MCP.log"\n\n# Search for errors\nfindstr /i "error fail" "%APPDATA%\\Claude\\logs\\mcp*.log"'
    )
    ON CONFLICT DO NOTHING;
    v_knowledge_count := v_knowledge_count + 1;

    -- ────────────────────────────────────────────────────────────────────
    -- Universal Knowledge 3: Windows-MCP Requires uv Package Manager
    -- ────────────────────────────────────────────────────────────────────
    INSERT INTO claude_family.shared_knowledge (
        learned_by_identity_id,
        knowledge_type,
        knowledge_category,
        title,
        description,
        applies_to_projects,
        applies_to_platforms,
        confidence_level,
        times_applied,
        code_example
    ) VALUES (
        v_desktop_identity_id,
        'gotcha',
        'mcp',
        'Windows-MCP server requires uv package manager',
        'Windows-MCP MCP server fails with "spawn uv ENOENT" if uv (Universal Python package installer by Astral) is not installed. Install via PowerShell script. After installation, restart Claude Desktop app for Windows-MCP to connect successfully.',
        ARRAY['all'],
        ARRAY['windows'],
        10,  -- Certain (diagnosed and fixed)
        1,  -- Applied once (diagnosed today)
        E'# Install uv via PowerShell\npowershell -c "irm https://astral.sh/uv/install.ps1 | iex"\n\n# Verify installation\nuv --version\n\n# Restart Claude Desktop\ntaskkill /F /IM "Claude.exe"\nStart-Process "$env:LOCALAPPDATA\\AnthropicClaude\\Claude.exe"'
    )
    ON CONFLICT DO NOTHING;
    v_knowledge_count := v_knowledge_count + 1;

    -- ────────────────────────────────────────────────────────────────────
    -- Universal Knowledge 4: Windows Forms Handle Creation Timing
    -- ────────────────────────────────────────────────────────────────────
    INSERT INTO claude_family.shared_knowledge (
        learned_by_identity_id,
        knowledge_type,
        knowledge_category,
        title,
        description,
        applies_to_projects,
        applies_to_platforms,
        confidence_level,
        times_applied,
        code_example
    ) VALUES (
        v_desktop_identity_id,
        'pattern',
        'windows-forms',
        'Form.Shown event for control initialization requiring window handles',
        'Windows Forms controls cannot access their window handles until the form is fully shown. Form.Shown event is the correct place to initialize controls that need window handles (e.g., setting visibility, checking Handle property). Constructor is too early - controls are not yet created.',
        ARRAY['all'],  -- Applies to all Windows Forms projects
        ARRAY['windows'],
        9,  -- High confidence
        1,  -- Applied successfully once
        E'// BAD: Constructor is too early\npublic MainForm() {\n    InitializeComponent();\n    someControl.Visible = true;  // May not work\n}\n\n// GOOD: Form.Shown event has handles ready\nprivate void MainForm_Shown(object sender, EventArgs e) {\n    someControl.Visible = true;  // Works reliably\n}'
    )
    ON CONFLICT DO NOTHING;
    v_knowledge_count := v_knowledge_count + 1;

    -- ────────────────────────────────────────────────────────────────────
    -- Universal Knowledge 5: Session Affinity with CookieContainer
    -- ────────────────────────────────────────────────────────────────────
    INSERT INTO claude_family.shared_knowledge (
        learned_by_identity_id,
        knowledge_type,
        knowledge_category,
        title,
        description,
        applies_to_projects,
        applies_to_platforms,
        confidence_level,
        times_applied,
        code_example
    ) VALUES (
        v_desktop_identity_id,
        'pattern',
        'http',
        'HttpClient session affinity with CookieContainer',
        'Use HttpClientHandler with CookieContainer to maintain session affinity (sticky sessions) across HTTP requests. Server-side caching works better when requests from same client hit same server instance. Essential for performance when uploading multiple requests in sequence.',
        ARRAY['all'],  -- Applies to any HTTP client code
        ARRAY['all'],  -- Platform-independent
        10,  -- Very confident
        2,  -- Applied to UserSDK and Core Config
        E'// Create HttpClient with session affinity\nvar handler = new HttpClientHandler {\n    CookieContainer = new CookieContainer(),\n    UseCookies = true\n};\nusing var http = new HttpClient(handler);\n\n// All requests now share cookies = session affinity'
    )
    ON CONFLICT DO NOTHING;
    v_knowledge_count := v_knowledge_count + 1;

    -- ────────────────────────────────────────────────────────────────────
    -- Universal Knowledge 6: CancellationToken Pattern for Stop Buttons
    -- ────────────────────────────────────────────────────────────────────
    INSERT INTO claude_family.shared_knowledge (
        learned_by_identity_id,
        knowledge_type,
        knowledge_category,
        title,
        description,
        applies_to_projects,
        applies_to_platforms,
        confidence_level,
        times_applied,
        code_example
    ) VALUES (
        v_desktop_identity_id,
        'pattern',
        'dotnet',
        'CancellationToken for graceful operation cancellation',
        'Use CancellationTokenSource in GUI, pass token to backend operations. Check IsCancellationRequested in loops. Always dispose CancellationTokenSource in finally block. Enables stop buttons without abrupt termination. Show partial results/statistics when cancelled.',
        ARRAY['all'],  -- Applies to any .NET app with long operations
        ARRAY['all'],
        9,
        1,
        E'// In GUI\nprivate CancellationTokenSource _cts;\n\nprivate async void btnRun_Click(...) {\n    _cts = new CancellationTokenSource();\n    try {\n        await DoWork(_cts.Token);\n    } finally {\n        _cts?.Dispose();\n        _cts = null;\n    }\n}\n\nprivate void btnStop_Click(...) {\n    _cts?.Cancel();\n}\n\n// In backend loop\nforeach (var item in items) {\n    if (token.IsCancellationRequested) break;\n    // ... process item\n}'
    )
    ON CONFLICT DO NOTHING;
    v_knowledge_count := v_knowledge_count + 1;

    RAISE NOTICE '✅ Extracted % universal knowledge items to claude_family.shared_knowledge', v_knowledge_count;
END $$;

-- ============================================================================
-- 2. EXTRACT PROJECT-SPECIFIC PATTERNS (Leave in nimbus_context)
-- ============================================================================

-- Note: Project-specific learnings stay in nimbus_context.project_learnings
-- These include:
--   - "NEVER modify UserSDK logic" (Nimbus-specific constraint)
--   - "Column name flexibility with GetFlexibleVal()" (Nimbus-specific)
--   - "Date normalization for Nimbus API" (Nimbus-specific)
--
-- These are NOT universal - they only apply to Nimbus User Loader project

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE 'Project-specific learnings remain in nimbus_context.project_learnings:';
    RAISE NOTICE '  - UserSDK constraints';
    RAISE NOTICE '  - Column naming patterns';
    RAISE NOTICE '  - Date normalization rules';
    RAISE NOTICE '  - Nimbus-specific validation';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- 3. CREATE CODE PATTERNS IN CLAUDE_FAMILY
-- ============================================================================

-- Note: nimbus_context.code_patterns contains Nimbus-specific patterns
-- Let's also add universal patterns to claude_family for cross-project use

DO $$
DECLARE
    v_desktop_identity_id UUID;
    v_pattern_count INTEGER := 0;
BEGIN
    SELECT identity_id INTO v_desktop_identity_id
    FROM claude_family.identities
    WHERE identity_name = 'claude-desktop-001';

    -- Note: We could create a claude_family.code_patterns table
    -- But for now, patterns are in shared_knowledge with type='pattern'
    -- This is simpler and avoids duplication

    v_pattern_count := (
        SELECT COUNT(*)
        FROM claude_family.shared_knowledge
        WHERE knowledge_type = 'pattern'
    );

    RAISE NOTICE 'Universal code patterns stored as shared_knowledge (type=pattern): %', v_pattern_count;
END $$;

-- ============================================================================
-- 4. VERIFICATION
-- ============================================================================

DO $$
DECLARE
    v_total_knowledge INTEGER;
    v_universal_knowledge INTEGER;
    v_gotchas INTEGER;
    v_patterns INTEGER;
    v_techniques INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total_knowledge
    FROM claude_family.shared_knowledge;

    SELECT COUNT(*) INTO v_universal_knowledge
    FROM claude_family.shared_knowledge
    WHERE 'all' = ANY(applies_to_projects);

    SELECT COUNT(*) INTO v_gotchas
    FROM claude_family.shared_knowledge
    WHERE knowledge_type = 'gotcha';

    SELECT COUNT(*) INTO v_patterns
    FROM claude_family.shared_knowledge
    WHERE knowledge_type = 'pattern';

    SELECT COUNT(*) INTO v_techniques
    FROM claude_family.shared_knowledge
    WHERE knowledge_type = 'technique';

    RAISE NOTICE '';
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';
    RAISE NOTICE '✅ UNIVERSAL KNOWLEDGE EXTRACTED SUCCESSFULLY!';
    RAISE NOTICE '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';
    RAISE NOTICE '';
    RAISE NOTICE 'Total shared knowledge: %', v_total_knowledge;
    RAISE NOTICE '  Universal (applies to all): %', v_universal_knowledge;
    RAISE NOTICE '  Gotchas: %', v_gotchas;
    RAISE NOTICE '  Patterns: %', v_patterns;
    RAISE NOTICE '  Techniques: %', v_techniques;
    RAISE NOTICE '';
    RAISE NOTICE 'Categories:';
    RAISE NOTICE '  - OneDrive (caching issues)';
    RAISE NOTICE '  - MCP (server diagnostics, dependencies)';
    RAISE NOTICE '  - Windows Forms (handle timing)';
    RAISE NOTICE '  - HTTP (session affinity)';
    RAISE NOTICE '  - .NET (cancellation tokens)';
    RAISE NOTICE '';
    RAISE NOTICE 'Project-specific learnings remain in nimbus_context schema';
    RAISE NOTICE '';
    RAISE NOTICE 'Next: Run load_claude_startup_context.py to test identity loading';
    RAISE NOTICE '';
END $$;

-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- Uncomment to test:

-- -- Show all universal knowledge
-- SELECT
--     knowledge_type,
--     knowledge_category,
--     title,
--     confidence_level,
--     times_applied
-- FROM claude_family.shared_knowledge
-- WHERE 'all' = ANY(applies_to_projects)
-- ORDER BY confidence_level DESC, times_applied DESC;

-- -- Show OneDrive-related gotchas
-- SELECT
--     title,
--     description,
--     code_example
-- FROM claude_family.shared_knowledge
-- WHERE knowledge_category = 'onedrive';

-- -- Show MCP-related knowledge
-- SELECT
--     title,
--     LEFT(description, 100) || '...' as description
-- FROM claude_family.shared_knowledge
-- WHERE knowledge_category = 'mcp';
