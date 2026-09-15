# InvoXcel — Agent Guide

## Project purpose

InvoXcel is an AI-assisted invoice extraction and export application. It accepts
one or more invoice documents, lets the user choose the data structure they
want, extracts that data into a normalized internal representation, validates
it, lets the user correct it, and exports it.

This is an MVP/side project. Build it in small, understandable, verified
increments. Do not generate the whole application from a single prompt.

## Authoritative sources

Before proposing or changing product code, read these files in this order:

1. `docs/design/PRD.md` — product requirements and MVP boundaries.
2. `skills/karpathy-guidelines/SKILL.md` — required working behaviour.
3. `skills/karpathy-guidelines/EXAMPLES.md` — concrete examples of that
   behaviour.

For any frontend, UI, UX, visual-design, or styling work, also read
`skills/frontend-design/SKILL.md` before proposing or writing the interface.

The PRD is the product authority. If an implementation decision is absent or
ambiguous, state the assumption and the smallest viable options; do not silently
invent a requirement. Update the PRD only when the user explicitly asks for a
product-decision change.

## Visual identity and frontend work

InvoXcel's primary brand color is `#217346` (Excel green). Treat it as a
design token, for example `--color-primary: #217346`, rather than scattering
the hex value throughout templates and stylesheets. Use white text on this
color for primary actions; preserve accessible contrast and visible keyboard
focus states.

For frontend work, follow `skills/frontend-design/SKILL.md` in addition to the
rules in this guide. Begin with a compact, InvoXcel-specific design plan:

- a 4–6 color token palette anchored by `#217346`;
- deliberate typography and a clear hierarchy suitable for accountants,
  bookkeepers, and finance teams reviewing dense tabular data;
- a layout/wireframe and responsive behaviour for the exact screen being built;
- one distinctive but restrained design decision tied to document review or
  structured financial data.

Review the plan for generic SaaS-card styling before implementation. Keep the
workspace calm and data-forward: the source document, extracted values,
validation state, and editing actions must remain easy to scan. Do not add a
frontend framework, component library, animation system, or design system until
the current slice justifies it and the user agrees.

## Product invariants

- The user chooses the output schema before final extraction.
- Templates describe *what data a user wants*, never a vendor-specific invoice
  layout.
- The system must keep invoice summary data (one record per invoice) separate
  from line-item data (many records per invoice).
- AI output is untrusted input: persist raw output for traceability, normalize
  it, then validate it before presenting it as reliable.
- The review workspace is a core feature: users must be able to compare source
  documents with editable extracted values.
- Export only user-reviewed/current workspace data, using the template's column
  order and types.

## Inputs and outputs

### Accepted MVP inputs

- PDF, including multi-page PDFs
- JPG/JPEG
- PNG
- A user-selected template, selected standard/custom summary columns, selected
  line-item columns, and optional extraction instructions

Treat uploaded filenames, document contents, and AI responses as untrusted.
Validate file type and size server-side; never use a user-supplied filename as a
storage path.

### Required processing outputs

For each invoice, maintain distinct representations:

1. Original uploaded document and metadata.
2. Analysis result: detected fields, document suitability, and line-item/table
   presence.
3. Normalized invoice summary and normalized line items.
4. Validation findings, verification status, and calculated confidence.
5. User edits/audit information where supported by the current scope.
6. Exports: XLSX (primary), CSV, and JSON. XLSX should support separate
   summary and line-item sheets; CSV must not pretend that two datasets are one
   table.

Do not expose a provider-specific AI response as the application data contract.

## How to work with the user

For every non-trivial iteration:

1. Restate the narrow goal, assumptions, and explicit non-goals.
2. Give a small plan with a verification check for each step.
3. Discuss meaningful design choices before committing to a path. Prefer a
   recommendation when the choice is reversible; ask when it changes product
   scope, data ownership, cost, or the user experience materially.
4. Implement only the agreed slice.
5. Report changed files, how to run/verify the slice, and deferred work.

Use the Karpathy guidelines as operating rules:

- Think before coding; surface uncertainty and tradeoffs.
- Prefer the minimum code and data model needed for the present slice.
- Make surgical changes; do not refactor or reformat unrelated code.
- Define observable success criteria and run the relevant checks.

When fixing a defect, first add or identify a reproducible test when practical.
When adding a feature, add focused tests for its behaviour and failure modes.

## Current local-development scope

The repository has no application scaffold yet. Until a later product decision
expands scope, work locally with Django and its development server only:

- Use a project-local virtual environment, `.venv/`; do not commit it.
- Keep configuration out of source control. Commit `.env.example`, never `.env`
  or API credentials.
- Use SQLite for the first local vertical slice unless the user asks to introduce
  PostgreSQL. Keep model/query code portable so changing databases is ordinary.
- Run Django locally with `python manage.py runserver` after applying migrations.
- Use Django Admin for MVP administration; do not build a separate admin UI.
- Do not add Docker, Celery/Redis, cloud storage, queues, authentication
  providers, background workers, or production deployment infrastructure until
  a concrete MVP need is agreed.
- Do not call an AI provider from a request path until a provider, cost controls,
  error behaviour, and test-double strategy are explicitly chosen. Early
  extraction work should use a service boundary and deterministic fixtures.

Suggested bootstrap commands (adapt only after checking the files actually
present):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install Django
django-admin startproject config .
python manage.py migrate
python manage.py runserver
```

Do not run `startproject` into a non-empty codebase without first showing the
files that would be created and confirming the chosen project layout.

## Target module boundaries

Start with Django's conventional `config/` project package and small domain apps.
Create an app only when the current iteration needs it; this is a target shape,
not permission to scaffold every app now.

```text
config/                 Django settings, URLs, ASGI/WSGI
apps/
  uploads/              Uploaded-document validation and storage metadata
  templates/            Output templates and column definitions
  processing/           Analysis/extraction orchestration and batch state
  invoices/             Normalized invoice summaries, line items, validation
  exports/              XLSX, CSV, and JSON rendering
  workspace/            Review/edit views and UI composition
services/               Provider-neutral AI client contracts and adapters
tests/                  Cross-app integration/flow tests when needed
docs/design/            PRD and agreed architecture decisions
skills/                 Repository-local agent skills
```

Within an app, use Django defaults first (`models.py`, `views.py`, `forms.py`,
`admin.py`, `urls.py`, `tests/`). Introduce `services.py`, selectors, or extra
packages only when a concrete workflow makes the boundary useful. Avoid a
generic `utils/` dumping ground.

The intended data flow is:

```text
upload → initial analysis → schema selection → extraction
       → normalization → validation → editable workspace → export
```

Keep the AI-provider adapter behind the processing service. Keep validation
rules deterministic and independent of the provider. Keep export formatting
independent of the web views.

## Engineering standards

- Match the repository's existing style and tooling once introduced.
- Use Django migrations for every model change; never edit the database by hand
  as a substitute for a migration.
- Use `Decimal` for currency, not `float`; make timezone/date assumptions
  explicit.
- Give externally visible fields stable machine keys separate from display names.
- Preserve source linkage/provenance for values when extraction begins, so a
  reviewer can understand where a value came from.
- Add validation for required fields, field types, dates, currency, totals, and
  India GST rules only when the selected template requires them.
- Make a clear distinction between extraction failure, validation warnings, and
  user-editable missing data.
- Keep secrets out of logs, commits, fixtures, screenshots, and error messages.
- Test uploads and parsing with safe, non-sensitive fixture documents.
- Run the smallest relevant check first, then the full relevant suite before
  calling a slice complete. At minimum, run Django system checks and tests for
  touched behaviour once the project exists.

## MVP guardrails

Do not add these unless the user explicitly reprioritizes them:

- vendor-layout-specific templates
- a chat interface as the primary review experience
- QBO export
- public API/integrations
- mobile app
- team collaboration, complex roles/permissions, or custom admin
- bulk editing, Excel-like keyboard navigation, or analytics dashboards

Prefer a functioning end-to-end vertical slice over broad unfinished scaffolding.
For example: upload one safe sample PDF → select two summary fields → return
fixture extraction → validate → edit → export CSV. Verify it, then expand.

## Definition of done for an iteration

A coding iteration is complete only when:

- Its goal and non-goals are documented in the conversation or an agreed design
  note.
- Its behaviour is covered by focused automated tests where feasible.
- Relevant migrations, `python manage.py check`, and tests pass.
- The local run path is documented when it changes.
- No secrets, generated artefacts, or unrelated refactors were introduced.
- Remaining limitations and the next smallest useful slice are stated.
