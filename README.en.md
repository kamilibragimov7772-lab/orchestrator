# Orchestrator — a verifiable orchestration stack for Claude Code

**[English](README.en.md) · [Русский](README.md) · [简体中文](README.zh-CN.md) · [Español](README.es.md) · [Português](README.pt-BR.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Deutsch](README.de.md) · [Français](README.fr.md) · [हिन्दी](README.hi.md) · [العربية](README.ar.md) · [Türkçe](README.tr.md)**

Turn one Claude Code session into an orchestrator: a brief becomes a wave plan, waves run
specialized subagents, every wave lands as a file, and a separate reviewer accepts or rejects
the result. 41 agent cards, 10 shared contracts, 10 slash commands, 4 optional skills.

MIT licensed. Author: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**. Protocol version **2.16.0**.

> **Read this first — language.** The orchestration protocol, the agent cards and the
> acceptance criteria are written **in Russian**. The tooling, tests, install path and code
> comments are in English. If you want the agents themselves, you will be reading Russian
> Markdown. If you want the plumbing that makes an agent stack trustworthy, that part is
> language-neutral and is the reason this repo exists.

---

## Why this exists

There is no shortage of Claude Code subagent collections. There is a shortage of ones you can
verify. Most are a folder of Markdown files: nothing proves the hooks fire, nothing proves the
secret scanner looks at the right bytes, nothing fails when a check silently stops checking.

This repo is the opposite trade-off. The agent library is ordinary; **the plumbing around it is
the point**:

| What most collections ship | What this ships |
|---|---|
| Agent Markdown only | Agents **plus** guards, installer, doctor, acceptance gate, sync |
| No tests | **97 tests**, stdlib only, no API calls, no network |
| "Add this to settings.json" | Installer with collision preflight; **doctor runs the guard for real** and requires it to block |
| Hooks assumed to work | Three-payload smoke test: benign must pass, secret must block, risky must block |
| "It's safe, trust the prompt" | Prompt text is never treated as an access boundary — see [SECURITY.md](SECURITY.md) |

Everything that can be checked by a script is checked by a script, because a rule that lives
only in a prompt is a rule that quietly stops being followed.

---

## Quick start

Requires **Python 3.10+** and **Git**. No API key, no network, no model calls:

```sh
git clone https://github.com/kamilibragimov7772-lab/orchestrator
cd orchestrator
python tools/verify.py
```

That runs the agent-contract linter, the readiness-counter self-test, the full test suite and a
secret scan. It touches nothing outside the checkout.

Install into directories you choose — the installer **plans first and never overwrites**:

```sh
python tools/install.py \
  --destination /absolute/path/stack \
  --vault /absolute/path/knowledge-base \
  --mode minimal
```

Review the plan, then re-run with `--apply`. If any target file exists and differs, the install
stops and preserves your file. Then confirm the result:

```sh
python tools/doctor.py --root /absolute/path/stack --installed
```

`minimal` installs seven roles for research and Markdown deliverables. `full` adds the
software / site-build / media pipelines and their external dependencies. Windows notes and how
to point Claude Code at the new directory: [INSTALL.md](INSTALL.md).

---

## What is in the box

| Layer | Purpose | Verification boundary |
|---|---|---|
| `_orchestr_protocol.md`, `agents/`, `commands/` | Routing, contracts, definition-of-done | The linter checks structure; answer quality needs human acceptance |
| `tools/verify.py`, `tests/` | One reproducible command, negative cases included | No Claude API, no external MCP |
| `tools/guard.py` | PreToolUse detection of credentials and destructive commands | **Heuristic defence in depth** — keep your host permissions and sandbox |
| `tools/install.py`, `tools/doctor.py` | Non-destructive install; readiness report | Doctor does not test auth or model quality |
| `tools/acceptance-gate/` | Deterministic run-log checks plus an optional reviewer worker | Model worker is **off by default**; live end-to-end not certified |
| `tools/sync_stack.py` | Git bridge over an exact allowlist | Optional; refuses to merge diverged branches for you |
| `tools/export_session.py` | Opt-in transcript export | **Off by default**; redaction is pattern-based, not a privacy guarantee |

### The acceptance gate

The idea that took the longest to get right. After a run closes, a **separate context** — it
never saw the orchestrator's reasoning — judges the deliverable against the brief. A
deterministic script runs first and the model only judges what the script cannot:

- `run_status` and `verdict` are separate fields. A run that is not `done` returns
  *"not subject to acceptance"*, not a fake pass.
- `SKIP` yields **"incomplete"**, never "accepted". A PDF is reported as *signature only —
  render it in a viewer*; a `.docx` as *structure parses, visual acceptance is separate*.
- Exit codes are distinct: `0` accepted · `1` rejected · `3` incomplete · `4` not applicable · `2` error.

Rationale, in the author's own measurement across 259 runs: a rule that made it into a
validator holds 76–100% of the time; the same rule as prompt text holds 0–39%.

---

## What it deliberately does not do

Trust is mostly a list of things a tool refuses to do behind your back:

- **No automatic export, mirroring, Git push, cron or model process on install.** Every one of
  those is opt-in and needs explicit configuration.
- **No `robocopy /MIR`-style mirroring.** It could delete files in the destination that are not
  in the source. It was removed.
- **No overwriting.** Conflicting files stop the install; your settings and hooks are merged,
  not replaced.
- **No silent pass.** A missing dependency or an unexecuted check reports `NOT CHECKED` or
  `SKIP`. It never reports a pass it did not earn.
- **No claim of a rating it has not proven.** A "9.5/10" was targeted and **not certified** —
  the open items are listed in [`audit_9_5/`](audit_9_5/) rather than averaged away.

---

## Verification status

CI runs Windows / Linux / macOS × Python 3.10 and 3.12, parses every PowerShell script, and
scans the **entire Git history** with Gitleaks. See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Honest limits, because a green badge is not evidence:

- Tests cover tooling behaviour, not the quality of what the agents write.
- Live model end-to-end acceptance is **not** covered by the suite.
- The guards are heuristics. They complement host permissions; they do not replace them.

---

## Documentation

| File | What it answers |
|---|---|
| [INSTALL.md](INSTALL.md) | Installing, wiring Claude Code, Windows specifics |
| [AGENTS.md](AGENTS.md) | Entry point for working on this codebase |
| [SECURITY.md](SECURITY.md) | What the guards do and do not protect; export privacy |
| [CONTRIBUTING.md](CONTRIBUTING.md) | The checks a change must pass |
| [CHANGELOG.md](CHANGELOG.md) | Behaviour changes |

## Methodology

Engineering baseline: **NIST SSDF 1.1** (NIST, 2022) — reproduce a defect, fix it, add a
regression that rejects the broken case — together with the host's official documentation
([Claude Code hooks](https://code.claude.com/docs/en/hooks)). Checked 2026-09-06. SSDF is used
to select risks, not as a certificate of compliance.

## License

[MIT](LICENSE). Author: **[@kamil_ibrgmv](https://instagram.com/kamil_ibrgmv)**.
