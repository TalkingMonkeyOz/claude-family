---
description: Start the Next.js development server
---

# Start Development Server

Launches the Next.js development server on the default port (typically 3000).

## Steps

1. Check which package manager is installed:
   - Look for `pnpm-lock.yaml` → use `pnpm`
   - Look for `yarn.lock` → use `yarn`
   - Look for `package-lock.json` → use `npm`
   - Default to `npm` if none found

2. Start the development server:
   ```bash
   # pnpm
   pnpm dev
   
   # yarn
   yarn dev
   
   # npm
   npm run dev
   ```

3. Report to user:
   - Server startup status
   - Access URL (typically `http://localhost:3000`)
   - Any warnings or issues that appeared

## Notes

- Dev server will run continuously and watch for file changes
- Hot Module Replacement (HMR) is typically enabled by default
- User can stop with Ctrl+C
- Check `next.config.js` for custom port configuration
- If port 3000 is in use, Next.js will try the next available port
