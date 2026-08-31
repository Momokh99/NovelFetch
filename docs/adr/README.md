# Architecture Decision Records

This directory holds the project's Architecture Decision Records (ADRs) for the
NovelFetch codebase (single-context layout).

Each ADR is a numbered file `NNNN-title.md` capturing one meaningful decision:
the context, the decision, and the consequence.

## Conventions

- **Naming**: `NNNN-kebab-case-title.md` (e.g. `0001-pluggable-source-system.md`)
- **Numbering**: sequential, starting at `0001`; the next free number is the highest existing `NNNN` plus one.
- **Where they live**: `docs/adr/` at the repo root (system-wide decisions). There are no context-scoped ADR directories (single-context repo).

## How to read them

Before working in an area, read the ADRs that touch it. If your output would
contradict an existing ADR, surface that explicitly — see the consumer rules in
[`docs/agents/domain.md`](../agents/domain.md).

## How to add one

Use the `/domain-modeling` skill (via `/grill-with-docs` or `/improve-codebase-architecture`),
which records decisions here as they are resolved. Don't create ADRs speculatively.
