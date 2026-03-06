# Release Process

This document describes how `gepa-adk` releases are created and published to PyPI.

## Overview

Releases are fully automated via [release-please](https://github.com/googleapis/release-please) and GitHub Actions:

1. **Conventional commits** on `main` are tracked automatically
2. **release-please** opens/updates a version-bump PR with changelog
3. **Merging** the PR creates a `v*` tag
4. **publish.yml** triggers on the tag: build → verify → attest → publish to PyPI → deploy docs

No manual version bumps, tags, or GitHub Releases are needed.

## How Releases Work

### Step 1: Merge conventional commits to main

Use [conventional commit](https://www.conventionalcommits.org/) prefixes:

| Prefix | Bump | Example |
|--------|------|---------|
| `feat:` | minor | `feat(engine): add mutation rationale capture` |
| `fix:` | patch | `fix(scorer): handle empty output` |
| `feat!:` or `BREAKING CHANGE:` | major | `feat!: remove evolve_sync` |
| `docs:`, `chore:`, `test:`, `ci:` | none | Hidden from changelog |

### Step 2: release-please creates a PR

After each push to `main`, the `release-please.yml` workflow:

- Analyzes new commits since the last release
- Opens (or updates) a PR titled `chore(main): release X.Y.Z`
- Generates a changelog from conventional commits
- Bumps `pyproject.toml` version via the `extra-files` config
- An `update-lockfile` job updates `uv.lock` on the PR branch

### Step 3: Merge the release PR

When the release PR is merged:

- release-please creates a `vX.Y.Z` tag (using `RELEASE_PLEASE_TOKEN` PAT)
- The tag triggers `publish.yml`

### Step 4: Automatic publishing

The `publish.yml` workflow:

1. **Builds** wheel and sdist with `uv build`
2. **Verifies** tag version matches `pyproject.toml`
3. **Smoke tests** wheel contents (size limit, no test files)
4. **Installs** and verifies the wheel in a clean venv
5. **Publishes** to PyPI via OIDC trusted publishing (no API tokens)
6. **Generates** attestations for package provenance
7. **Deploys** documentation to GitHub Pages

## Configuration Files

| File | Purpose |
|------|---------|
| `release-please-config.json` | Release type, changelog sections, extra-files |
| `.release-please-manifest.json` | Current version (`1.0.1`) |
| `.github/workflows/release-please.yml` | PR creation + lockfile update |
| `.github/workflows/publish.yml` | Build, verify, publish, docs deploy |

## Prerelease Versions

Prerelease versions (e.g., `2.0.0a1`, `2.0.0rc1`) are not currently automated via release-please. If needed, use the manual process below.

## Emergency Manual Release

If release-please is broken or you need an out-of-band release:

```bash
# 1. Bump version in pyproject.toml
uv version 2.0.1

# 2. Commit and merge to main
git add pyproject.toml
git commit -m "chore: bump version to 2.0.1"
# (merge via PR)

# 3. Create and push tag
git checkout main && git pull
git tag v2.0.1
git push origin v2.0.1
```

The `v*` tag triggers `publish.yml` regardless of how it was created.

## Troubleshooting

### Release PR not appearing

- Check that commits use conventional prefixes (`feat:`, `fix:`)
- Verify `RELEASE_PLEASE_TOKEN` secret is set (PAT with `repo` scope)
- Check the release-please workflow run in Actions for errors

### Tag not triggering publish

- Tags created by `GITHUB_TOKEN` do NOT trigger other workflows
- The `RELEASE_PLEASE_TOKEN` PAT is required for cross-workflow triggering
- Verify the tag matches the `v*` pattern

### "Version mismatch" error in publish

```
ERROR: Tag version 2.0.0 does not match pyproject.toml version 1.0.1
```

The tag version must match `pyproject.toml`. release-please handles this automatically; manual tags require a matching version bump first.

### "OIDC token request failed"

Ensure Trusted Publishing is configured at [pypi.org/manage/account/publishing](https://pypi.org/manage/account/publishing/):

- Workflow: `.github/workflows/publish.yml`
- Repository: `Alberto-Codes/gepa-adk`
- Environment: `pypi`

### "Package already exists"

PyPI does not allow overwriting published versions. Bump the version and release again.

## Version Numbering

Follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (2.0.0): Incompatible API changes
- **MINOR** (2.1.0): New features, backwards-compatible
- **PATCH** (2.0.1): Bug fixes, backwards-compatible
