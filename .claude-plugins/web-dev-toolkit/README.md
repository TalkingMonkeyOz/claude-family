# web-dev-toolkit Plugin

A Claude Code plugin that provides essential development commands for Next.js + shadcn/ui + TypeScript projects.

## Overview

This plugin streamlines common web development workflows by providing intelligent command wrappers that:
- Auto-detect package managers (pnpm, yarn, npm)
- Handle project-specific configurations
- Parse and categorize command outputs
- Provide clear feedback and recommendations

## Available Commands

### `/build`
Builds the Next.js application and categorizes any errors that occur.
- Detects package manager automatically
- Categorizes TypeScript, ESLint, and runtime errors
- Provides actionable error summaries

### `/dev`
Starts the development server for local development.
- Auto-detects package manager
- Shows server access URL
- Reports any startup issues

### `/lint-fix`
Runs ESLint with automatic fixes applied.
- Fixes all auto-fixable issues
- Reports remaining manual fixes needed
- Shows affected files and rules

### `/type-check`
Runs TypeScript type checking without emitting files.
- Fast type validation (no code generation)
- Organized error reporting
- Clear error descriptions with locations

### `/test`
Executes the project's test suite.
- Detects test runner (Jest, Vitest, Playwright)
- Reports pass/fail counts and details
- Shows code coverage if available

### `/shadcn-add`
Adds a shadcn/ui component to the project.
- Prompts for component selection
- Handles installation via shadcn/ui CLI
- Shows import paths and usage examples

## Installation

The plugin is automatically available when placed in:
```
.claude-plugins/web-dev-toolkit/
```

## Usage

In Claude Code, commands are invoked as slash commands:

```
/build      - Build the project
/dev        - Start dev server
/lint-fix   - Run linter with fixes
/type-check - Check TypeScript types
/test       - Run tests
/shadcn-add - Add shadcn component
```

## Project Requirements

- **Node.js** 16+ (18+ recommended)
- **Next.js** project with TypeScript
- **ESLint** configured (for lint-fix command)
- **TypeScript** configured (for type-check command)
- **Test runner** configured (for test command) - Jest, Vitest, or Playwright
- **shadcn/ui** configured with `components.json` (for shadcn-add command)

## Configuration Files Detected

- `package.json` - Package manager scripts and dependencies
- `pnpm-lock.yaml` - pnpm lock file
- `yarn.lock` - Yarn lock file
- `package-lock.json` - npm lock file
- `tsconfig.json` - TypeScript configuration
- `eslintrc.*` - ESLint configuration
- `.eslintignore` - ESLint ignore patterns
- `jest.config.*` - Jest configuration
- `vitest.config.*` - Vitest configuration
- `playwright.config.*` - Playwright configuration
- `components.json` - shadcn/ui configuration
- `next.config.js` - Next.js configuration

## Error Handling

Commands include intelligent error handling:
- Missing configuration detection
- Fallback commands when scripts aren't defined
- Clear error messages with suggested fixes
- Exit code interpretation

## Author

Claude Family - Infrastructure Project

## Version

1.0.0
