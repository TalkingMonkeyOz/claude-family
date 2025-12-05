# {{PROJECT_NAME}} - Web Application

**Type**: Web App
**Created**: {{CREATED_DATE}}

---

## Project Overview

Web application project.

---

## Project Structure

```
{{PROJECT_NAME}}/
├── src/
│   ├── components/     # React/Vue components
│   ├── pages/          # Page components
│   ├── styles/         # CSS/SCSS files
│   └── utils/          # Utility functions
├── public/             # Static assets
├── tests/              # Test files
├── CLAUDE.md           # This file
└── README.md           # Project overview
```

---

## Build Commands

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

---

## Key Technologies

- Framework: (Next.js / React / Vue)
- Styling: (Tailwind / CSS Modules)
- State: (Context / Redux / Zustand)

---

## When Working Here

- Follow component naming conventions
- Write tests for new features
- Check accessibility (a11y)
- Test responsive design

---

## Recent Work

```sql
SELECT summary, outcome, session_start
FROM claude.sessions
WHERE project_name = '{{PROJECT_NAME}}'
ORDER BY session_start DESC LIMIT 5;
```

---

**Version**: 1.0
**Location**: {{PROJECT_PATH}}/CLAUDE.md
