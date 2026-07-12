# Release Process — Mili-VIO

## Versioning

| Component | Location | Current |
|-----------|----------|---------|
| Python package | `pyproject.toml` → `version` | `0.1.0` |
| Embedded | `embedded/include/mili/mili_config.h` (comment) | aligned with tag |
| Git tags | `vMAJOR.MINOR.PATCH` | not yet published |

**Semantic versioning:**

- **MAJOR** — breaking FC frame, SPI protocol, or SRS API changes
- **MINOR** — new features, backward-compatible
- **PATCH** — bug fixes, docs, CI

## Pre-release Checklist

```bash
# 1. Fast tests (CI equivalent)
pytest tests/ -m "not slow" -v

# 2. Phase 6 validation
mili-vio-validate --quick --skip-embedded

# 3. Embedded (if cmake available)
embedded/scripts/build.ps1 -Quick -Test

# 4. Update CHANGELOG.md — move [Unreleased] to [X.Y.Z] with date
# 5. Bump version in pyproject.toml
```

## Creating a Release

### 1. Commit and tag

```bash
git add CHANGELOG.md pyproject.toml
git commit -m "Release v0.1.0"
git tag -a v0.1.0 -m "Mili-VIO 0.1.0 — initial platform release"
git push origin main --tags
```

### 2. GitHub Release

```bash
gh release create v0.1.0 \
  --title "Mili-VIO v0.1.0" \
  --notes-file CHANGELOG.md
```

Or via GitHub UI: **Releases → Draft new release** → select tag `v0.1.0`.

### 3. Artifacts (optional)

| Artifact | Build command |
|----------|---------------|
| Python wheel | `pip install build && python -m build` |
| Embedded host sim | `embedded/scripts/build.ps1` |
| Validation report | `mili-vio-validate --full` → attach YAML |

## Branch Policy

| Branch | Purpose |
|--------|---------|
| `main` | stable; CI + slow validation on push |
| `develop` | integration (if used) |
| `release/*` | release candidates |

## CI Gates (`.github/workflows/ci.yml`)

| Job | Gate |
|-----|------|
| `test` | `pytest -m "not slow"` Python 3.10 + 3.11 |
| `embedded-smoke` | CMake build + CTest (Windows) |
| `slow-validation` | `mili-vio-validate --quick` on `main` push |

## First Official Release (v0.1.0)

**Status:** tag not yet created in repository.

To publish the first release after validation passes:

1. Run checklist above
2. Create tag `v0.1.0` as shown
3. Open GitHub Release with link to:
   - [OPERATOR_GUIDE.md](OPERATOR_GUIDE.md)
   - [API_INTEGRATION.md](API_INTEGRATION.md)
   - [PHASE6_VALIDATION.md](PHASE6_VALIDATION.md)

## Post-release

- Update `[Unreleased]` section in `CHANGELOG.md`
- Bump to next dev version in `pyproject.toml` (e.g. `0.2.0.dev0` optional)
