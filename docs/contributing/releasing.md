# Release Process

This document describes how to release `gepa-adk` to PyPI.

## Overview

Releases are automated via GitHub Actions using:
- **Trusted Publishing (OIDC)** - no API tokens required
- **uv** for building and publishing
- **Attestations** for package provenance
- **GitHub Pages** deployment for documentation

## Version Management

**Single source of truth:** Version is stored in `pyproject.toml` only.

**Policy:** Version must be bumped in a PR before creating a release. CI will verify the tag matches `pyproject.toml` and fail if it doesn't.

### Bump version locally

```bash
# Using uv (recommended)
uv version 0.2.0

# Or manually edit pyproject.toml
# [project]
# version = "0.2.0"
```

Commit and merge to `main`:

```bash
git add pyproject.toml
git commit -m "chore: bump version to 0.2.0"
git push origin feat/my-feature
# Create PR, get approved, merge
```

## Creating a Release

### Step 1: Create and push tag

After your version bump PR is merged to `main`:

```bash
git checkout main
git pull origin main

# Create tag (note the 'v' prefix)
git tag v0.2.0

# Push tag to GitHub
git push origin v0.2.0
```

### Step 2: Create GitHub Release

1. Go to https://github.com/Alberto-Codes/gepa-adk/releases
2. Click **Draft a new release**
3. Choose tag: `v0.2.0`
4. Click **Generate release notes** (auto-generates from PRs)
5. Edit release notes if needed
6. Click **Publish release**

### Step 3: Automatic Publishing

Once the release is published, the workflow automatically:

1. **Builds** wheel and sdist
2. **Verifies** tag version matches `pyproject.toml`
3. **Tests** artifacts with smoke tests
4. **Generates** attestations for provenance
5. **Publishes** to PyPI or TestPyPI (see below)
6. **Deploys** documentation to GitHub Pages

## Prerelease vs Final Release

The workflow automatically determines the publish target:

### Prerelease (alpha/beta/rc)

Versions containing `a`, `b`, or `rc` are treated as prereleases:
- `0.2.0a1` - alpha
- `0.2.0b2` - beta
- `0.2.0rc1` - release candidate

**Behavior:** Publishes to **TestPyPI only** (not PyPI)

### Final Release

Versions without prerelease markers:
- `0.2.0`
- `1.0.0`

**Behavior:** Publishes to **PyPI**

## Testing with TestPyPI

### For prereleases

Prereleases automatically publish to TestPyPI. Test the installation:

**Using uv (recommended):**
```bash
uv pip install --index-url https://test.pypi.org/simple/ \
               --extra-index-url https://pypi.org/simple/ \
               gepa-adk
```

**Using pip:**
```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            gepa-adk
```

**Note:** The `--extra-index-url` is needed because dependencies (google-adk, litellm, etc.) are not on TestPyPI.

### Manual TestPyPI publish

To manually publish any version to TestPyPI:

1. Go to **Actions** → **Publish to PyPI**
2. Click **Run workflow**
3. Set inputs:
   - **ref:** Tag or commit (e.g., `v0.2.0`)
   - **target:** `testpypi`
4. Click **Run workflow**

### Publishing to both TestPyPI and PyPI

Use manual workflow dispatch with:
- **target:** `both`
- **allow_prerelease_to_pypi:** `true` (if prerelease)

## Manual Workflow Dispatch

For testing or special cases, you can manually trigger the workflow:

**Inputs:**
- **ref** (optional): Tag or commit to build/publish (defaults to current branch)
- **target** (required):
  - `testpypi` - Publish to TestPyPI only (default)
  - `pypi` - Publish to PyPI only
  - `both` - Publish to both
- **allow_prerelease_to_pypi** (boolean): Safety switch for publishing prereleases to PyPI

## Troubleshooting

### "Version mismatch" error

```
ERROR: Version mismatch!
  Tag version:      0.2.0
  pyproject.toml:   0.1.0
```

**Fix:** Bump version in `pyproject.toml` first, merge PR, then create tag.

### "OIDC token request failed"

**Fix:** Ensure Trusted Publishing is configured:
- PyPI: https://pypi.org/manage/account/publishing/
- TestPyPI: https://test.pypi.org/manage/account/publishing/

Required settings:
- Workflow: `.github/workflows/publish.yml`
- Repository: `Alberto-Codes/gepa-adk`
- Environment (optional): Leave blank or use `testpypi` if you've defined a GitHub Environment

### "Package already exists"

You're trying to republish an existing version. PyPI doesn't allow overwriting.

**Fix:** Bump version and create new release.

### Docs not deploying

**Fix:** Ensure GitHub Pages is configured:
- Settings → Pages → Source: **GitHub Actions**

## Version Numbering Guidelines

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0): Incompatible API changes
- **MINOR** (0.2.0): New features, backwards-compatible
- **PATCH** (0.1.1): Bug fixes, backwards-compatible

**Prerelease identifiers:**
- `a` - alpha (early testing, unstable)
- `b` - beta (feature complete, testing)
- `rc` - release candidate (stable, final testing)

Examples:
- `0.1.0` → `0.1.1` (bug fix)
- `0.1.0` → `0.2.0` (new feature)
- `0.2.0` → `0.2.0rc1` → `0.2.0` (prerelease → final)
- `0.9.0` → `1.0.0` (breaking change)
