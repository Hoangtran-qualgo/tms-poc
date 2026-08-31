# Codex Migration Guideline: Python → TypeScript / Next.js

## Objective

Migrate the existing Python application to a modern TypeScript application as safely as possible while preserving current behavior, business logic, and user-facing functionality.

The migration must be **incremental and reversible**. The existing Python application remains the source of truth until the corresponding TypeScript functionality has been verified.

Do not treat this as a line-by-line language translation. First understand the existing system, then reimplement its behavior using appropriate TypeScript and Next.js patterns.

---

## Target Repository Structure

Keep both implementations in the same repository:

```text
tms/
├── python/
│   └── app/
│       └── existing Python application
│
├── js/
│   └── app/
│       └── new TypeScript / Next.js application
│
├── docker-compose.yml
└── README.md
```

Rules:

* Do not remove or modify the Python application unnecessarily.
* Python and TypeScript applications must be runnable independently.
* During migration, both implementations may coexist.
* Shared external dependencies such as databases or APIs may be reused where appropriate.
* Docker Compose may be used to run the applications and required dependencies locally.

Do not introduce CI/CD work unless explicitly requested.

---

# Phase 1 — Investigate Before Implementing

Before writing TypeScript code, investigate the Python application thoroughly.

Do not immediately start converting files.

Build an understanding of:

### Application Purpose

Determine:

* What problem does the application solve?
* Who are the expected users?
* What are the primary workflows?
* What inputs does the application accept?
* What outputs does it produce?
* What external systems does it communicate with?

Summarize the application purpose before proposing the TypeScript architecture.

### Functional Inventory

Identify the major functional areas.

Examples:

```text
Authentication
User management
Workspace management
Data import/export
Search
Reporting
Configuration
Background jobs
External API integrations
Admin workflows
```

For each area identify:

* entry points
* important functions
* major classes/modules
* inputs
* outputs
* side effects
* dependencies
* error handling
* persistence behavior

Create a functional map rather than simply listing Python files.

---

# Phase 2 — Understand Business Logic

Identify business logic separately from framework-specific implementation.

For important functions, determine:

```text
Input
  ↓
Validation
  ↓
Business rules
  ↓
Data transformation
  ↓
Persistence / external interaction
  ↓
Output
```

Document rules such as:

* required fields
* validation constraints
* permissions
* state transitions
* calculations
* filtering rules
* sorting rules
* deduplication rules
* retry behavior
* error mappings

The TypeScript implementation should preserve these behaviors unless there is an explicit requirement to change them.

Do not assume Python implementation details are business requirements.

---

# Phase 3 — Identify System Contracts

Pay special attention to boundaries between the application and other systems.

Investigate:

* HTTP APIs
* request schemas
* response schemas
* database models
* configuration files
* environment variables
* file formats
* message/event formats
* authentication mechanisms
* external services

Treat these as migration contracts.

Where practical, define equivalent TypeScript types and runtime validation schemas.

Example:

```ts
type User = {
  id: string;
  email: string;
  displayName: string;
};
```

Use runtime validation where external/untrusted input is involved.

Prefer libraries such as Zod when appropriate.

---

# Phase 4 — Establish Behavioral Baseline

Before migrating a feature, determine its current observable behavior.

Use the Python application as the baseline.

Important behaviors include:

```text
same input
   ↓
Python application
   ↓
expected output / side effects
```

The TypeScript implementation should produce equivalent behavior:

```text
same input
   ↓
TypeScript application
   ↓
equivalent output / side effects
```

Existing Python tests should be treated as behavioral documentation when available.

Do not blindly translate Python tests into TypeScript tests. First understand what behavior each test protects.

---

# Phase 5 — Design the TypeScript Application

Use:

```text
TypeScript
Next.js
React
shadcn/ui
```

Prefer current stable and idiomatic patterns.

The new application should emphasize:

* maintainability
* modular architecture
* clear boundaries
* strong typing
* reusable UI components
* accessibility
* responsive design
* predictable state management
* user-friendly error handling
* extensibility

Avoid reproducing Python architecture when it does not fit the JavaScript/TypeScript ecosystem.

---

# Recommended Next.js Structure

Prefer feature/domain-oriented organization over large generic folders.

Example:

```text
tms/js/app/
├── src/
│   ├── app/
│   │
│   ├── features/
│   │   ├── users/
│   │   ├── workspaces/
│   │   ├── reports/
│   │   └── imports/
│   │
│   ├── components/
│   │   ├── ui/
│   │   └── shared/
│   │
│   ├── lib/
│   │
│   ├── services/
│   │
│   ├── schemas/
│   │
│   ├── types/
│   │
│   └── utils/
│
├── tests/
└── package.json
```

Do not create abstractions unless they solve an actual recurring problem.

Prefer simple, explicit architecture.

---

# UI/UX Guidelines

Use **shadcn/ui** as the primary component foundation.

The new UI should not merely duplicate the existing Python UI pixel-for-pixel.

Preserve user workflows while improving usability where safe.

Prioritize:

* clear information hierarchy
* consistent spacing
* consistent component behavior
* meaningful loading states
* empty states
* error states
* confirmation dialogs
* actionable validation messages
* responsive layouts
* keyboard accessibility
* accessible labels
* predictable navigation

Prefer reusable shadcn components such as:

```text
Button
Dialog
AlertDialog
Form
Input
Select
Table
Tabs
Card
Badge
DropdownMenu
Toast / Sonner
Skeleton
Sheet
Tooltip
```

Avoid custom components when shadcn already provides an appropriate foundation.

---

# Migration Strategy

Use **incremental vertical slices**.

Do not perform a big-bang rewrite.

A migration slice should represent meaningful user functionality, for example:

```text
Login
↓
Workspace list
↓
Workspace details
↓
Member management
↓
Import members
```

rather than:

```text
convert all models
↓
convert all utils
↓
convert all services
↓
convert all controllers
```

The first approach makes behavioral verification much easier.

For each migrated feature:

```text
Understand Python behavior
        ↓
Identify contracts
        ↓
Implement TypeScript version
        ↓
Test independently
        ↓
Compare with Python behavior
        ↓
Resolve differences
        ↓
Mark feature as migrated
```

---

# Safety Rules

Follow these rules throughout the migration.

### Rule 1 — Python Remains Intact

Do not delete, rename, or substantially refactor Python code merely to simplify migration.

Only modify Python code when necessary and explain why.

### Rule 2 — No Unverified Behavior Changes

If Python behavior appears strange or inefficient, do not silently "fix" it.

Document the behavior first.

Differentiate between:

```text
Existing behavior

Potential defect

Recommended improvement
```

Migration and product behavior changes should remain separate whenever possible.

### Rule 3 — Preserve Contracts

Avoid changing:

* API payloads
* persisted data
* identifiers
* error semantics
* file formats
* external integration behavior

unless explicitly approved.

### Rule 4 — Prefer TypeScript-Native Design

Preserve behavior, not Python syntax or structure.

For example, do not automatically convert:

```python
class UserService:
    ...
```

into:

```ts
class UserService {
   ...
}
```

Evaluate whether functions, modules, interfaces, services, or another TypeScript pattern is more appropriate.

### Rule 5 — Avoid Premature Refactoring

Do not simultaneously:

* migrate language
* redesign business logic
* redesign database schemas
* replace major dependencies
* change APIs
* change infrastructure

unless required.

First achieve behavioral parity.

Then propose improvements separately.

---

# Testing Philosophy

Migration confidence should come from behavioral comparison.

Prioritize:

### Unit Tests

For isolated business rules and transformations.

### Integration Tests

For:

* APIs
* database behavior
* external services
* authentication
* file processing

### Contract Tests

For important request/response boundaries.

### UI Tests

For critical user workflows.

### Regression Tests

For bugs previously discovered in the Python implementation.

When possible, use the same logical fixtures against both implementations.

Example:

```text
Fixture A
   ├── Python implementation → Result A
   └── TypeScript implementation → Result B

Compare Result A and Result B
```

The goal is behavioral equivalence, not identical internal implementation.

---

# Error Handling

Investigate how Python currently handles:

```text
validation errors
network errors
timeouts
HTTP 4xx
HTTP 5xx
database failures
missing configuration
unexpected data
partial failures
```

The TypeScript implementation should provide predictable behavior.

For UI-facing failures, prefer:

```text
technical failure
      ↓
normalized application error
      ↓
clear user-facing message
```

Do not expose raw stack traces or implementation details in the UI.

---

# Logging and Observability

Preserve meaningful logging from the Python application.

Identify logs that help answer:

```text
What happened?
Which operation failed?
Which user action triggered it?
Which external dependency failed?
How long did it take?
Can the issue be reproduced?
```

The TypeScript implementation should have structured and useful logging.

Avoid excessive debug logging in normal operation.

Do not work on external monitoring infrastructure unless explicitly requested.

---

# Dependency Migration

Do not search for a one-to-one npm replacement for every Python dependency.

Instead determine:

```text
Python package
      ↓
What capability does it provide?
      ↓
What is the idiomatic TypeScript/Node solution?
```

For every important dependency, identify:

* purpose
* whether it is still required
* TypeScript alternative
* migration risk
* behavioral differences

Avoid adding dependencies for functionality that can be implemented simply using the platform/framework.

---

# Docker Scope

Docker support is allowed.

A root-level Docker Compose configuration may be used to simplify local development.

Example conceptual setup:

```text
docker-compose
│
├── python-app
├── js-app
├── database
└── supporting local services
```

Docker Compose should primarily support:

* local development
* migration comparison
* integration testing
* consistent dependency setup

Do not implement:

```text
GitHub Actions
GitLab pipelines
Jenkins
production deployment pipelines
cloud infrastructure
release automation
```

unless explicitly requested.

---

# Documentation During Migration

Maintain lightweight migration documentation.

Track functionality using a table similar to:

| Feature   | Python   | TypeScript  | Parity   | Notes          |
| --------- | -------- | ----------- | -------- | -------------- |
| Login     | Existing | Implemented | Verified | Equivalent     |
| User list | Existing | Implemented | Verified | Equivalent     |
| Import    | Existing | In progress | Pending  | CSV edge cases |
| Reports   | Existing | Not started | -        | -              |

Do not mark a feature migrated merely because code exists.

Migration is complete only when behavior has been verified.

---

# Codex Working Behavior

While performing this migration:

1. Inspect before editing.
2. Explain your understanding of the relevant Python behavior.
3. Identify dependencies and contracts.
4. State assumptions explicitly.
5. Ask for clarification when behavior cannot be determined from the repository.
6. Prefer small, reviewable changes.
7. Avoid modifying unrelated code.
8. Run relevant tests after changes.
9. Compare new behavior with the Python implementation.
10. Report discrepancies rather than hiding them.
11. Do not delete the Python implementation.
12. Do not perform CI/CD work.
13. Prefer Docker Compose only when infrastructure support is necessary.
14. Favor maintainable TypeScript over mechanical Python translation.
15. Favor user-friendly and accessible UI using Next.js and shadcn/ui.

---

# Before Implementing Any Feature

For every migration unit, first provide a short investigation summary using:

```text
Feature:
Purpose:

Python entry points:
Relevant modules:

Inputs:
Outputs:

Business rules:

External dependencies:

Persistence:

Error behavior:

Important edge cases:

Current tests:

Migration risks:

Proposed TypeScript responsibility:
```

Do not begin implementation until this information is sufficiently understood.

---

# Definition of Done for a Migrated Feature

A feature can be considered migrated when:

* its purpose is understood;
* Python behavior has been documented;
* important business rules have been identified;
* TypeScript implementation exists;
* relevant input/output contracts are preserved;
* error behavior is covered;
* critical tests pass;
* behavior has been compared with Python;
* UI states are handled appropriately;
* no unrelated Python functionality was broken;
* migration documentation is updated.

---

# Final Principle

The primary goal is not:

> "Convert Python code into TypeScript."

The primary goal is:

> **Safely reproduce the application's intended behavior in a maintainable TypeScript/Next.js architecture while keeping the existing Python application available as the reference implementation until migration confidence is established.**

Optimize decisions in this order:

```text
1. Behavioral correctness
2. Migration safety
3. Verifiability
4. Maintainability
5. User experience
6. TypeScript/Next.js idiomatic design
7. Code similarity with Python
```

When uncertain, prefer preserving existing behavior and documenting the uncertainty rather than guessing.
