# SonarQube Integration

This project has a SonarQube Community Edition instance on the local LAN, connected via the official `mcp/sonarqube` MCP server (global config in `~/.claude.json`).

## Project Details

- **Project key**: `gepa-adk`
- **Server**: SonarQube Community Edition on the local LAN (URL varies by machine)
- **MCP server**: Official SonarSource `mcp/sonarqube` image, configured globally in `~/.claude.json`

## Network & Environment

- The SonarQube server runs on a LAN machine — not always reachable (user works across multiple machines, sometimes off-LAN)
- If MCP tools return connection errors, the server is likely unreachable — don't retry, just note it and move on
- When running on the machine that hosts the SonarQube server itself, the URL may be `localhost:9000` instead of the LAN IP
- The MCP server token and URL are in `~/.claude.json` — check there for the current configuration
- Shell profile env vars: `$SONAR_TOKEN` (scanner auth) and `$SONARQUBE_URL` (server URL) are set in `~/.bashrc`
- **Never read tokens from `~/.claude.json`** — always use the shell env vars with `-e SONAR_TOKEN` passthrough to avoid exposing secrets in command history

## Scanning (Manual)

Community Edition has no branch analysis and no automatic scan triggers. Scans must be run manually after merging to main.

**Project config**: `sonar-project.properties` at project root defines `sonar.projectKey`, `sonar.sources`, `sonar.python.version`, `sonar.python.coverage.reportPaths`, and `sonar.sourceEncoding`. The scanner reads this automatically — no `-D` flags needed except `sonar.host.url`.

**Scan command** (run from project root on main branch):

```bash
# Optional: generate coverage report first
uv run pytest --cov=gepa_adk --cov-report=xml

# Run scanner ($SONARQUBE_URL and $SONAR_TOKEN set in ~/.bashrc)
podman run --rm \
  -v "$(pwd):/usr/src:z" \
  --userns=keep-id \
  --network host \
  -e SONAR_TOKEN \
  docker.io/sonarsource/sonar-scanner-cli:latest \
  -Dsonar.host.url="$SONARQUBE_URL"
```

## When to Use

- After completing code changes, use `analyze_code_snippet` to check modified files for issues
- Use `search_sonar_issues_in_projects` with `projects: ["gepa-adk"]` to review open issues
- Use `get_project_quality_gate_status` with `projectKey: "gepa-adk"` to check gate status
- After a PR merges to main, offer to run a scan if the user is on-LAN

## Known Issue Patterns

- The dominant finding is **cognitive complexity** (`python:S3776`, threshold 15). When refactoring functions, aim to stay under 15. When using `analyze_code_snippet` for fast feedback, target CC ≤ 12 to buffer against divergence between the MCP tool and the full scanner.

## Important Notes

- SonarQube dashboard results lag behind local changes — don't verify fixes via the dashboard API immediately after editing; use `analyze_code_snippet` for fast feedback during development
- The server may not be reachable in every session (off-LAN, server down)
