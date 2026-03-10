# AGENTS.md

## Purpose
`py-madvr-envy` is the protocol and normalization library used by the madVR Envy Home Assistant integration.

## Workflow
- Use `uv` for local commands.
- Run repo-local lint and tests before pushing.
- Keep transport handling, state reduction, and protocol quirks here rather than in the HA layer.

## Design Expectations
- Preserve stable identifiers across reconnects and cold starts.
- Make lifecycle semantics explicit and deterministic.
- Treat missing data as unknown state, not silent entity churn.

## Commits
- Use conventional commits for releasable changes: `fix: ...` or `feat: ...`.

## Releases
1. Merge normal conventional commits to `master`.
2. Let `release-please` open or update the release PR.
3. Do not manually edit version files or changelogs outside the Release Please PR.
4. Do not manually create tags or GitHub releases.
5. Merge the Release Please PR to publish.
