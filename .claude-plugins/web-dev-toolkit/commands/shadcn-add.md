---
description: Add a shadcn/ui component to the project
---

# Add shadcn/ui Component

Prompts for a component name and adds it to the project using the shadcn/ui CLI.

## Steps

1. Verify shadcn is configured:
   - Check for `components.json` in project root
   - If missing, inform user and stop

2. Ask user for component name:
   - Provide list of popular components:
     - button, card, input, dialog, dropdown-menu
     - form, table, tabs, select, checkbox
     - toast, tooltip, alert, badge, etc.
   - Accept user input or default selection

3. Run shadcn/ui add command:
   ```bash
   npx shadcn-ui@latest add [component-name]
   # or
   npx shadcn@latest add [component-name]
   ```

4. Wait for installation to complete

5. Report results:
   - Component installed successfully
   - Files created (typically in `components/ui/`)
   - Import path to use
   - Example usage if available

## Notes

- shadcn/ui requires `components.json` configuration
- Components are installed locally, not from npm
- Requires Node.js 16+ and a React/Next.js project
- Installation may prompt about dependencies to install
- Multiple components can be added in sequence

## Success Indicators

- Component files appear in `src/components/ui/` or `components/ui/`
- No errors during installation
- User can import: `import { Button } from "@/components/ui/button"`
