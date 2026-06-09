# /specs

Specifications and rules that guide feature work on TMS.

## /specs/features

One Markdown file per feature. Naming format:

```
<NN>-feature-<feature-name>-<NEW|UPDATE>.md
```

- `<NN>` — zero-padded integer index. Use the smallest positive
  integer **not currently in use** by any file in this directory,
  starting from `01`. Indices are stable: once assigned they are never
  reused, even after the file is deleted (gaps stay as gaps).
- `<feature-name>` — short slug summarising the feature, **10–20
  characters total**, lowercase, words joined with `-` (no spaces, no
  punctuation other than `-`).
- `<NEW|UPDATE>` — `NEW` for a net-new feature, `UPDATE` for a
  modification of an existing feature.

Each file holds the specification that drives the feature through
**Investigate → Plan → Do** phases. Scope covers (as relevant) data
model, on-disk storage layout, file control, HTTP API surface, UI
flows, and acceptance criteria.

Lifecycle: created when an `IN-PROGRESS.md` Investigate item enters
the Investigate phase; the file evolves alongside the work and stays
in `/specs/features` as the source of truth after release.

`00-summary.md` is a single aggregator file (not a feature spec, so
it does not follow the `<NN>-feature-<name>-<NEW|UPDATE>.md` format).
It indexes every feature, mirrors each spec's three relationship
sections, and holds the workflow-level function-chain map. It must
be kept in sync whenever a spec is added, renamed, or has its
relationship sections changed.

### Required relationship sections

Every feature spec **must** include the three sections below.
Capture them at decision time, while the author still has the
context fresh; they become the relationship map between features and
the wider product. Section order and headings are fixed.

- `## Affects` — existing modules, features, files, endpoints, or UI
  surfaces this change touches. One bullet per item, with a one-line
  reason ("now also writes to X", "extends Y's schema", etc.).
- `## Depends on` — existing modules / features / invariants this
  spec assumes will remain stable for its design to hold. If a
  listed dependency later changes, this spec must be revisited.
- `## Surface for follow-up` — what this feature makes easier OR
  harder for future work. Often the most valuable section for the
  next author picking up adjacent work.

The rest of the spec body (problem statement, data model, API, UI
flows, acceptance criteria, etc.) is shaped to match the feature; no
fixed template beyond the three relationship sections.

## /specs/rules

Cross-cutting rules that apply to all feature work:

- `tech-rule.md` — engineering / technical rules and conventions.
- `business-rule.md` — product / domain / business rules.
