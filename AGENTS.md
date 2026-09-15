# Agent instructions for InvoXcel

Read and follow [CLAUDE.md](CLAUDE.md) before making any change. It is the
canonical repository guide shared by coding agents.

Before code work, also read:

1. `docs/design/PRD.md`
2. `skills/karpathy-guidelines/SKILL.md`
3. `skills/karpathy-guidelines/EXAMPLES.md`

For any frontend, UI, UX, visual-design, or styling work, also read
`skills/frontend-design/SKILL.md`. InvoXcel's primary brand color is `#217346`;
define and use it as a shared design token, not repeated raw values. Design for
calm, accessible, data-dense financial review rather than generic SaaS cards.

The project is pre-development. The present agreed direction is a local Django
MVP using `.venv/`, SQLite for the earliest vertical slice, Django Admin, and
`python manage.py runserver`. Do not introduce production infrastructure,
background processing, an AI provider, or extra frameworks without a scoped
decision and a verification plan.

Core rules:

- Template defines output data, not an invoice vendor layout.
- Keep invoice summaries and line items as distinct datasets.
- Treat document content and AI output as untrusted; normalize and validate it.
- Work in small vertical slices with explicit success criteria and focused tests.
- Prefer simple Django conventions and surgical changes over premature layers.
- State assumptions and material tradeoffs; do not silently invent requirements.

If this file conflicts with `CLAUDE.md`, follow `CLAUDE.md` and flag the
conflict to the user.
