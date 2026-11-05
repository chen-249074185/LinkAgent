---
name: liepin-cli
description: Use when Liepin (猎聘) workflows need the CLI—missing or expired token, unauthorized responses, first-time setup, resume fetch/update, job search or apply, choosing job-kind from search results, machine-readable JSON for parsing, or summarizing user-facing `liepin-cli` help without advanced flags.
---

# liepin-cli

This skill is generated from the current project source. Do not edit distributed copies directly.

## Overview
`liepin-cli` is the local CLI for Liepin resume, job, and auth workflows. Prefer it over ad hoc HTTP requests.

## When to Use
- run `liepin-cli`
- inspect or explain `liepin-cli --help`
- manage Liepin token setup, refresh, or status
- fetch or update resume data
- search jobs or apply to jobs

Do not use this skill for unrelated non-Liepin tasks.

## Core Rules
- Prefer the installed `liepin-cli` command.
- **Explaining help in chat (first pass):** Do not mention `--token`, `--input`, `--base-url`, `--timeout`, `--output`, or `--help` unless the user explicitly asks for raw/full/advanced help.
- **Running commands:** Follow the Command Map; use `--output json` there for machine-readable results. Omit `--output json` when the user only needs human-readable CLI output.
- For expired auth, guide the user to `liepin-cli auth open`, then `liepin-cli auth setup`.
- `job apply --job-kind` must reuse the type code from search results; do not guess labels like `social`.
- Do not assume README sample payload files already exist locally.

## Command Map
| Intent | Preferred command |
|------|------|
| Get current resume | `liepin-cli resume get --output json` |
| Search jobs | `liepin-cli job search ... --output json` |
| Apply to job | `liepin-cli job apply --job-id <id> --job-kind <kind> --output json` |
| First-time token setup | `liepin-cli setup` |
| Auth management | `liepin-cli auth setup/status/open/clear` |

## Help Summary Defaults
- Root help: `setup`, `auth`, `resume`, `job`
- `auth --help`: `status`, `clear`, `open`, `setup`
- `resume --help`: purpose plus subcommand overview only
- `job --help`: `search`, `apply`
- `job apply --help`: `--job-id`, `--job-kind`

## Common Mistakes
- Surfacing hidden/internal flags in the first help answer
- Guessing `jobKind` instead of reusing the search result
- Treating README payload paths as shipped files
- Dumping every resume field at once instead of summarizing the most useful business fields first

## Reference
Read [reference.md](reference.md) for install, command tables, auth recovery, and `--input` / `--output` notes. To install the CLI from source, follow the repository root `README.md`.
