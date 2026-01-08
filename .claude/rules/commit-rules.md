# Commit Rules

## Message Format

```
<type>: <short description>

[optional body]

Co-Authored-By: Claude <model> <noreply@anthropic.com>
```

## Types

- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `docs`: Documentation only
- `chore`: Maintenance tasks
- `test`: Test additions/changes

## Work Item Linking

When working on tracked items, include reference:
- Features: `[F1]`, `[F2]`
- Feedback: `[FB1]`, `[FB2]`
- Build tasks: `[BT1]`, `[BT2]`

## Branch Naming

- `feature/F1-description`
- `fix/FB3-description`
- `task/BT5-description`

## Safety

- Never force push to main/master
- Never skip hooks without explicit request
- Never commit secrets (.env, credentials)
