# Orchestrator development

This checkout is the public distribution of a Claude Code configuration stack.
`CLAUDE.md` is an installation template; preserve its user-facing role.
Change this checkout, never the developer's live `~/.claude` or vault to test it.

- Use Python 3.10+ and `python -m unittest discover -s tests -v` for portable core checks.
- `CLAUDE_HOME` overrides the stack being inspected. Tests must use disposable roots.
- Guards are heuristic defense in depth, not a replacement for host permissions.
- A missing dependency or unexecuted check must not be reported as a pass.
- Sync must use an explicit manifest and must preserve an existing user index.
- Changes to guards, validators or sync require a regression that rejects the broken case.
- Keep PowerShell wrappers ASCII; existing localized scripts require UTF-8 BOM for Windows PowerShell 5.1.
- Treat paths, shell commands and transcripts as untrusted inputs. Do not include their secrets in diagnostics.
- Do not run optional media scripts on real inputs during tests; some are project-specific recipes.
- No auto-export or remote sync on installation. Both require explicit configuration.
- Do not claim Codex runtime compatibility from the presence of this file.
