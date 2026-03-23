---
name: worktrunk
description: >
  Use when: worktrunk, `wt` commands, `.config/wt.toml`, git worktrees for parallel agents,
  worktree hooks, LLM commit messages, agent handoffs, `hash_port`/`sanitize` filters,
  "run agents in parallel", "set up worktrees", managing multiple Claude Code sessions.
---

# Worktrunk — Git Worktree Manager for Parallel AI Agents

Worktrunk is a CLI that makes git worktrees as easy as branches. Each AI agent (Claude Code, Codex, etc.) gets its own worktree so they don't step on each other's changes. GitHub: https://github.com/max-sixty/worktrunk

## Installation

```bash
# macOS/Linux
brew install worktrunk && wt config shell install

# Cargo
cargo install worktrunk && wt config shell install

# Windows (installs as git-wt to avoid Windows Terminal conflict)
winget install max-sixty.worktrunk
git-wt config shell install

# Arch Linux
paru worktrunk-bin && wt config shell install
```

Shell integration (`wt config shell install`) is **required** for directory switching — it wraps the binary so `wt switch` can change the shell's working directory.

If installation fails with C compilation errors: `cargo install worktrunk --no-default-features` (disables syntax highlighting but keeps all core functionality).

## Core Commands

### `wt switch` — Switch to worktree; create if needed

```bash
wt switch feature-auth           # Switch to existing worktree
wt switch -                      # Previous worktree (like cd -)
wt switch --create new-feature   # Create new branch + worktree
wt switch --create hotfix --base production  # Branch from specific base
wt switch pr:123                 # Switch to GitHub PR branch
wt switch mr:42                  # Switch to GitLab MR branch
wt switch                        # Interactive picker (requires skim, not on Windows)
```

**Flags:**
- `-c, --create` — Create a new branch
- `-b, --base <BASE>` — Base branch (defaults to default branch)
- `-x, --execute <CMD>` — Run command after switch (replaces wt process, gets full terminal). Supports template variables.
- `-- <ARGS>` — Additional arguments passed to --execute command

**Shortcuts:** `^` (default branch), `-` (previous), `@` (current)

**Key pattern — alias for new worktree + agent:**
```bash
alias wsc='wt switch --create -x claude'
wsc feature-branch                    # Create worktree, run hooks, launch Claude
wsc feature -- 'Fix GH #322'         # Pass initial prompt to Claude
```

**Lifecycle on create:** pre-switch (blocking) → create worktree → cd → pre-start (blocking, warns on fail) → post-start (background) → post-switch (background)

### `wt list` — List worktrees and status

```bash
wt list                   # Standard view
wt list --full            # Add CI status, line diffs, LLM summaries
wt list --branches        # Include branches without worktrees
wt list --format=json     # Structured output for scripting
```

**Columns:** Branch, Status, HEAD± (uncommitted changes), main↕ (ahead/behind default), main…± (line diffs, --full), Summary (LLM, --full), Remote⇅, CI (--full), Path, URL, Commit, Age, Message

**Status symbols:**

| Symbol | Meaning |
|--------|---------|
| `+` | Staged files |
| `!` | Modified (unstaged) |
| `?` | Untracked files |
| `✘` | Merge conflicts |
| `⤴` | Rebase in progress |
| `↑`/`↓` | Ahead/behind default branch |
| `⇡`/`⇣` | Ahead/behind remote |
| `_` | Same as default branch |
| `⊂` | Integrated (safe to delete) |
| `^` | Is the default branch |
| `|` | No remote tracking |

The table renders progressively — branch names appear instantly, status columns fill in as git operations complete.

### `wt remove` — Remove worktree; delete branch if merged

```bash
wt remove                          # Remove current worktree
wt remove feature-branch           # Remove specific worktree
wt remove --no-delete-branch feat  # Keep the branch
wt remove -D experimental          # Force-delete unmerged branch
wt remove --force feat             # Remove with untracked files
```

**Branch cleanup logic** (checks in order): same commit → ancestor → no added changes → trees match → merge adds nothing. Branches showing `_` or `⊂` in `wt list` are safe to delete.

**Flags:** `-f, --force` (untracked files), `-D, --force-delete` (unmerged branches), `--no-delete-branch`, `--foreground` (block until complete)

### `wt merge` — Merge current into target

Unlike `git merge`, this merges **current into target** (like GitHub's merge button). Target defaults to the default branch.

```bash
wt merge                    # Merge to default branch
wt merge develop            # Merge to specific branch
wt merge --no-remove        # Keep worktree after merge
wt merge --no-squash        # Preserve commit history
wt merge --no-ff            # Create merge commit (semi-linear)
wt merge --no-commit        # Skip commit/squash, still rebase
```

**Pipeline:** Commit → Squash → Rebase → Pre-merge hooks → FF Merge → Pre-remove hooks → Cleanup → Post-remove + Post-merge hooks (background)

- Default behavior: squash + rebase + fast-forward merge + remove worktree
- `--stage all|tracked|none` controls what gets staged
- Backup ref saved to `refs/wt-backup/<branch>`
- Conflicts during rebase abort immediately

## `wt step` — Individual Operations

Building blocks of `wt merge`, plus standalone utilities.

```bash
wt step commit              # Stage + commit with LLM message
wt step squash              # Squash all branch commits into one
wt step rebase              # Rebase onto target
wt step push                # Fast-forward target to current
wt step diff                # All changes since branching
wt step copy-ignored        # Copy gitignored files between worktrees
wt step eval '{{ branch | hash_port }}'  # Evaluate template expression
wt step for-each -- echo '{{ branch }}'  # Run in every worktree
wt step promote             # [experimental] Swap branch into main worktree
wt step prune               # [experimental] Remove merged worktrees
wt step relocate            # [experimental] Move worktrees to expected paths
```

**`commit` / `squash`** flags: `--stage all|tracked|none`, `--show-prompt` (debug LLM prompt)

**`copy-ignored`** uses reflink (copy-on-write) when available. Language notes:
- **Rust:** `target/` is huge but reflink cuts build from ~68s to ~3s
- **Python:** venvs contain absolute paths and can't be copied — use `uv sync` instead
- **Node:** `node_modules/` copies well with reflink

**`prune`** flags: `--min-age 1h` (default), `--dry-run`, `--foreground`

**Aliases** — custom commands in config, run via `wt step <alias-name>`:
```toml
# .config/wt.toml or ~/.config/worktrunk/config.toml
[aliases]
deploy = "make deploy BRANCH={{ branch }}"
port = "echo http://localhost:{{ branch | hash_port }}"
```

## Hook System

Hooks are shell commands at key lifecycle points. 10 types across 5 events:

| Event | `pre-` (blocking) | `post-` (background) |
|-------|-------------------|---------------------|
| **start** | pre-start (warns on fail) | post-start |
| **switch** | pre-switch | post-switch |
| **commit** | pre-commit | post-commit |
| **merge** | pre-merge | post-merge |
| **remove** | pre-remove | post-remove |

`pre-*` hooks block and abort on failure. `post-*` hooks run in background with logs at `.git/wt/logs/{branch}-{source}-{hook}-{name}.log`.

**Project hooks** go in `.config/wt.toml` (committed to repo, require approval on first run):
```toml
[pre-start]
deps = "npm ci"

[pre-merge]
test = "npm test"
build = "npm run build"

[post-start]
server = "npm run dev -- --port {{ branch | hash_port }}"
copy = "wt step copy-ignored"
```

**User hooks** go in `~/.config/worktrunk/config.toml` (personal, no approval needed, run before project hooks).

**Security:** Project hooks need approval on first run. Changed commands need re-approval. `--yes` bypasses prompts. `--no-verify` skips hooks entirely. Manage with `wt hook approvals add/clear`.

### Template Variables

| Variable | Description |
|----------|-------------|
| `{{ branch }}` | Active branch name |
| `{{ worktree_path }}` | Active worktree path |
| `{{ worktree_name }}` | Worktree directory name |
| `{{ commit }}` / `{{ short_commit }}` | HEAD SHA (full / 7 chars) |
| `{{ base }}` / `{{ base_worktree_path }}` | Base branch name / path |
| `{{ target }}` / `{{ target_worktree_path }}` | Target branch name / path |
| `{{ default_branch }}` | Default branch name |
| `{{ repo }}` / `{{ repo_path }}` | Repo directory name / absolute path |
| `{{ primary_worktree_path }}` | Primary worktree path |
| `{{ remote }}` / `{{ remote_url }}` | Remote name / URL |
| `{{ hook_type }}` / `{{ hook_name }}` | Current hook type / name |

Bare variables (`branch`, `worktree_path`) refer to the branch the operation acts on. `base` and `target` give the other side. Variables are shell-escaped automatically.

### Filters

| Filter | Example | Description |
|--------|---------|-------------|
| `sanitize` | `{{ branch \| sanitize }}` | Replace `/` `\` with `-` (path-safe) |
| `sanitize_db` | `{{ branch \| sanitize_db }}` | DB-safe identifier, hash suffix, max 63 chars |
| `hash_port` | `{{ branch \| hash_port }}` | Deterministic port 10000-19999 |

Hash concatenations for unique ports: `{{ (repo ~ '-' ~ branch) | hash_port }}`. Parentheses needed because `|` has higher precedence than `~`.

### Functions

`worktree_path_of_branch("main")` — returns the filesystem path of a branch's worktree, or empty string if none exists.

For detailed hook design patterns (dev servers, databases, tmux sessions, progressive validation, Caddy subdomain routing, etc.), read `references/tips-patterns.md`.

## Configuration

| File | Location | Shared |
|------|----------|--------|
| **User config** | `~/.config/worktrunk/config.toml` | No |
| **Project config** | `.config/wt.toml` | Yes (commit it) |
| **System config** | Platform-specific (`wt config show`) | Org-wide |

### User config example

```toml
# ~/.config/worktrunk/config.toml
worktree-path = ".worktrees/{{ branch | sanitize }}"

[commit.generation]
command = "CLAUDECODE= MAX_THINKING_TOKENS=0 claude -p --no-session-persistence --model=haiku --tools='' --disable-slash-commands --setting-sources='' --system-prompt=''"

[merge]
squash = true      # --no-squash to preserve history
commit = true      # --no-commit to skip
rebase = true      # --no-rebase to skip
remove = true      # --no-remove to keep worktree
verify = true      # --no-verify to skip hooks
no-ff = false      # --no-ff for merge commits

[list]
summary = true     # LLM branch summaries in wt list --full
```

### Project config example

```toml
# .config/wt.toml
[pre-start]
deps = "npm ci"

[post-start]
server = "npm run dev -- --port {{ branch | hash_port }}"
copy = "wt step copy-ignored"

[pre-merge]
lint = "npm run lint"
test = "npm test"

[pre-remove]
server = "lsof -ti :{{ branch | hash_port }} -sTCP:LISTEN | xargs kill 2>/dev/null || true"

[list]
url = "http://localhost:{{ branch | hash_port }}"

[ci]
platform = "github"  # or "gitlab"

[aliases]
deploy = "make deploy BRANCH={{ branch }}"
```

### Config subcommands

```bash
wt config shell install          # Install shell integration (required)
wt config shell uninstall        # Remove shell integration
wt config create                 # Create user config with documented examples
wt config create --project       # Create .config/wt.toml
wt config show                   # Show config files & locations
wt config show --full            # Include diagnostic checks
wt config state default-branch   # Show/manage default branch cache
wt config state marker set "🚧"  # Set status marker for current branch
wt config state logs get         # Show background hook logs
```

### Environment variables

All user config options can be overridden with `WORKTRUNK_` prefix. Special variables:

| Variable | Purpose |
|----------|---------|
| `WORKTRUNK_BIN` | Override binary path |
| `WORKTRUNK_CONFIG_PATH` | Override user config location |
| `WORKTRUNK_SYSTEM_CONFIG_PATH` | Override system config location |
| `WORKTRUNK_MAX_CONCURRENT_COMMANDS` | Max parallel git commands (default: 32) |
| `NO_COLOR` | Disable colored output |

## LLM Commit Messages

Worktrunk generates commit messages by piping a templated prompt to an external command. Integrates with `wt merge`, `wt step commit`, `wt step squash`.

### Setup

Add to `~/.config/worktrunk/config.toml`:

```toml
# Claude Code
[commit.generation]
command = "CLAUDECODE= MAX_THINKING_TOKENS=0 claude -p --no-session-persistence --model=haiku --tools='' --disable-slash-commands --setting-sources='' --system-prompt=''"

# Codex
# command = "codex exec -m gpt-5.1-codex-mini -c model_reasoning_effort='low' -c system_prompt='' --sandbox=read-only --json - | jq -sr '[.[] | select(.item.type? == \"agent_message\")] | last.item.text'"

# Other tools
# command = "llm -m claude-haiku-4.5"
# command = "aichat -m claude:claude-haiku-4.5"
```

`CLAUDECODE=` unsets the nesting guard so `claude -p` works from within Claude Code. `--no-session-persistence` prevents pollution.

### Custom templates

```toml
[commit.generation]
command = "llm -m claude-haiku-4.5"

template = """
Write a commit message for this diff. One line, under 50 chars.
Branch: {{ branch }}
Diff:
{{ git_diff }}
"""

squash-template = """
Combine these {{ commits | length }} commits into one message:
{% for c in commits %}
- {{ c }}
{% endfor %}
Diff:
{{ git_diff }}
"""
```

**Branch summaries:** With `[list] summary = true` and commit generation configured, `wt list --full` shows LLM-generated one-line summaries per branch.

**Fallback:** When no LLM is configured, worktrunk generates deterministic messages based on changed filenames.

## Claude Code Integration

```bash
claude plugin marketplace add max-sixty/worktrunk
claude plugin install worktrunk@worktrunk
```

Provides:
1. **Configuration skill** — Claude can help set up hooks, LLM commits, troubleshoot shell integration
2. **Activity tracking** — 🤖 (working) and 💬 (waiting) markers in `wt list`

Manual status markers: `wt config state marker set "✅" --branch feature`

## Common Patterns (Quick Reference)

For full recipes with complete code examples, read `references/tips-patterns.md`.

| Pattern | Key command / config |
|---------|---------------------|
| New worktree + agent | `alias wsc='wt switch --create -x claude'` |
| Eliminate cold starts | `post-start` hook: `wt step copy-ignored` |
| Dev server per worktree | `hash_port` filter + `[list] url` |
| Database per worktree | Docker + `sanitize_db` + `hash_port` |
| Local CI gate | `pre-merge` hooks: lint, test, build |
| Stacked branches | `wt switch --create part2 --base=@` |
| Agent handoffs | tmux/Zellij + `-x claude -- 'prompt'` |
| Reuse default branch | `git rebase $(wt config state default-branch)` |
| Bare repo layout | `worktree-path = "{{ repo_path }}/../{{ branch \| sanitize }}"` |

## Gotchas

1. **Filter precedence: `|` binds tighter than `~`.** When hashing a concatenated string, you must use parentheses: `{{ ('db-' ~ branch) | hash_port }}`. Without them, `{{ 'db-' ~ branch | hash_port }}` hashes only `branch` and then concatenates — giving the wrong port.

2. **Python venvs can't be copied between worktrees.** They contain absolute paths. Don't use `wt step copy-ignored` for Python — use `uv sync` (or `pip install -r requirements.txt`) in a `pre-start` hook instead.

3. **`CLAUDECODE=` is required for nested Claude calls.** When generating LLM commit messages from within a Claude Code session, the `CLAUDECODE` env var blocks nested `claude -p` calls. The workaround is `CLAUDECODE=` (unset) at the start of the command string.

4. **Shell integration is mandatory for `wt switch`.** Without `wt config shell install`, the binary can't change the shell's working directory. Commands will run but you'll stay in the old directory. If `wt switch` seems broken, this is almost always the cause.

5. **`wt merge` squashes by default.** Unlike `git merge`, worktrunk squashes all branch commits into one. If you want to preserve individual commits, use `--no-squash`. Backup refs are saved to `refs/wt-backup/<branch>` either way.

6. **Project hooks require approval on first run.** If hooks seem to be silently skipped, the user hasn't approved them yet. Run `wt hook show` to check, or `--yes` to auto-approve. If a hook command changes (even whitespace), it needs re-approval.

7. **`wt remove` deletes branches by default.** It checks 5 merge-detection heuristics and deletes branches that appear merged. Use `--no-delete-branch` if you want to keep the branch, or `-D` to force-delete unmerged branches.

## Troubleshooting

- **Shell integration not working:** Run `wt config show` to diagnose. Ensure the shell rc file sources worktrunk.
- **`wt` conflicts with Windows Terminal:** Use `git-wt` or disable the WT alias in Windows settings.
- **Default branch wrong:** `wt config state default-branch clear` to reset cache.
- **Hook not running:** Check `wt hook show`, verify approval with `wt hook approvals`, use `-v` for debug output.
- **Background hook logs:** `tail -f "$(wt config state logs get --hook=user:post-start:server)"`

## FAQ

- **vs. branch switching:** Worktrees give each agent isolated files and index — no conflicts.
- **vs. plain `git worktree`:** Worktrunk automates the full lifecycle, adds hooks, status aggregation, and consistent naming.
- **vs. git-machete / git-town:** Different scope — those manage branch stacks in one directory. Worktrunk manages multi-worktree workflows. Can be used together.
- **Windows:** Works in Git Bash and PowerShell. Interactive picker unavailable. Git for Windows required for hooks.
- **What can Worktrunk delete:** Worktrees and branches, both with safeguards. `wt config state clear` removes cached metadata.
