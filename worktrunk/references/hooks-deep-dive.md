# Hooks Deep Dive

Detailed reference for Worktrunk's hook system — configuration patterns, template mechanics, and design guidance.

## Table of Contents
1. [Hook Execution Model](#execution)
2. [All Hook Types Detail](#hook-types)
3. [Configuration Format](#config-format)
4. [Template Variable Semantics](#variable-semantics)
5. [Filter Details](#filter-details)
6. [Designing Effective Hooks](#design-patterns)
7. [Hook Command Reference](#command-ref)

---

<a id="execution"></a>
## Hook Execution Model

- `pre-*` hooks **block** — failure aborts the operation (except `pre-start`, which warns and continues)
- `post-*` hooks run in the **background** — output logged to `.git/wt/logs/{branch}-{source}-{hook}-{name}.log`
- Use `-v` flag to see expanded command details for background hooks
- Hooks execute via `sh -c` — full shell syntax available
- Variables are shell-escaped automatically — no quotes around `{{ ... }}` needed
- User hooks run **before** project hooks
- Named hooks within a type run in definition order

<a id="hook-types"></a>
## All Hook Types Detail

### pre-switch / post-switch
Run when switching between worktrees (even if the worktree already exists).
- `pre-switch` blocks the switch on failure
- `post-switch` runs in background after directory change

### pre-start / post-start
Run when **creating** a new worktree (not on every switch).
- `pre-start` warns on failure but **does not abort** (unique among pre-hooks)
- `post-start` is the most commonly used hook — runs background tasks like dev servers, file copying, builds

### pre-commit / post-commit
Run during `wt step commit` and the commit phase of `wt merge`.
- `pre-commit` blocks the commit on failure
- `post-commit` runs in background

### pre-merge / post-merge
Run during `wt merge`, after rebase but before the actual merge.
- `pre-merge` is the best place for validation gates (tests, linting, building)
- `post-merge` runs in background after cleanup

### pre-remove / post-remove
Run during `wt remove` and the cleanup phase of `wt merge`.
- `pre-remove` blocks removal on failure
- `post-remove` handles cleanup (stopping servers, removing containers)
- Template variables reference the **removed** worktree, so cleanup scripts can identify resources

**Merge hook order:** pre-commit → post-commit (bg) → pre-merge → pre-remove → post-remove + post-merge (bg)

<a id="config-format"></a>
## Configuration Format

### Project hooks (`.config/wt.toml`)
```toml
[pre-start]
deps = "npm ci"
env = "cp .env.example .env"

[post-start]
server = "npm run dev -- --port {{ branch | hash_port }}"

[pre-merge]
lint = "npm run lint"
test = "npm test"

[pre-remove]
server = "lsof -ti :{{ branch | hash_port }} -sTCP:LISTEN | xargs kill 2>/dev/null || true"
```

### User hooks (`~/.config/worktrunk/config.toml`)
```toml
[pre-start]
setup = "echo 'Setting up worktree...'"

[pre-merge]
notify = "notify-send 'Merging {{ branch }}'"
```

### Multi-line commands
```toml
[post-start]
db = """
docker run -d --rm \
  --name {{ repo }}-{{ branch | sanitize }}-postgres \
  -p {{ ('db-' ~ branch) | hash_port }}:5432 \
  -e POSTGRES_DB={{ branch | sanitize_db }} \
  postgres:16
"""
```

### Key differences

| Aspect | Project hooks | User hooks |
|--------|--------------|------------|
| Location | `.config/wt.toml` | `~/.config/worktrunk/config.toml` |
| Scope | Single repository | All repositories |
| Approval | Required on first run | Not required |
| Execution order | After user hooks | Before project hooks |

<a id="variable-semantics"></a>
## Template Variable Semantics

Bare variables (`branch`, `worktree_path`, `commit`) refer to the branch the operation **acts on**:

| Operation | Bare vars refer to | `base` | `target` |
|-----------|-------------------|--------|----------|
| switch/create | Destination branch | Where you came from | = bare vars |
| merge | Feature being merged | = bare vars | Where you're merging to |
| remove | Branch being removed | — | — |

All available variables:

| Variable | Description |
|----------|-------------|
| `{{ branch }}` | Active branch name |
| `{{ worktree_path }}` | Active worktree path |
| `{{ worktree_name }}` | Worktree directory name |
| `{{ commit }}` | HEAD SHA (full) |
| `{{ short_commit }}` | HEAD SHA (7 chars) |
| `{{ upstream }}` | Upstream branch (if tracking) |
| `{{ base }}` | Base branch name |
| `{{ base_worktree_path }}` | Base worktree path |
| `{{ target }}` | Target branch name |
| `{{ target_worktree_path }}` | Target worktree path |
| `{{ cwd }}` | Hook execution directory |
| `{{ repo }}` | Repository directory name |
| `{{ repo_path }}` | Absolute repo root path |
| `{{ primary_worktree_path }}` | Primary worktree path |
| `{{ default_branch }}` | Default branch name |
| `{{ remote }}` | Primary remote name |
| `{{ remote_url }}` | Remote URL |
| `{{ hook_type }}` | Hook type (e.g., `pre-start`) |
| `{{ hook_name }}` | Hook command name |

<a id="filter-details"></a>
## Filter Details

### `sanitize`
Replaces `/` and `\` with `-`. Makes branch names safe for filesystem paths.
```
feature/auth → feature-auth
```

### `sanitize_db`
Produces database-safe identifiers: lowercase alphanumeric and underscores, no leading digits, max 63 chars, with a 3-character hash suffix to avoid collisions and reserved words.
```
feature/AUTH-Login → feature_auth_login_a3f
```

### `hash_port`
Generates a deterministic port in range 10000-19999 from any string. Same input always produces the same port.
```
{{ branch | hash_port }}              → e.g., 16460
{{ ('db-' ~ branch) | hash_port }}   → different port for DB
{{ (repo ~ '-' ~ branch) | hash_port }}  → unique per repo+branch
```

**Operator precedence:** `|` (pipe) binds tighter than `~` (concatenation). Use parentheses for concatenation before filtering:
```
{{ ('db-' ~ branch) | hash_port }}     ← Correct
{{ 'db-' ~ branch | hash_port }}       ← Wrong! Hashes only branch, then concatenates
```

### Functions

`worktree_path_of_branch(branch_name)` — returns the filesystem path of a branch's worktree, or empty string if none exists:
```toml
[pre-start]
setup = "cp {{ worktree_path_of_branch('main') }}/config.local {{ worktree_path }}"
```

<a id="design-patterns"></a>
## Designing Effective Hooks

### post-start vs pre-start
- Use `post-start` for background tasks (dev servers, file watchers, builds) — they run concurrently and don't block
- Use `pre-start` for blocking setup that subsequent hooks or `--execute` depend on (installing deps)

### Copying untracked files
Use `post-start` for background copy, `post-create` if subsequent hooks need the files immediately:
```toml
[post-start]
copy = "wt step copy-ignored"
```

### Progressive validation
Quick checks early, thorough checks later:
```toml
[pre-commit]
lint = "npm run lint"

[pre-merge]
test = "npm test"
build = "npm run build"
```

### Target-specific behavior
Hooks can check the target branch to vary behavior:
```toml
[pre-merge]
gate = """
if [ "{{ target }}" = "production" ]; then
  npm run test:e2e
else
  npm test
fi
"""
```

<a id="command-ref"></a>
## Hook Command Reference

```
wt hook show              # Show configured hooks
wt hook pre-start         # Manually run pre-start hooks
wt hook post-merge        # Manually run post-merge hooks
wt hook approvals add     # Pre-approve a project hook
wt hook approvals clear   # Clear all approvals
```

All hook subcommands: `show`, `pre-switch`, `pre-start`, `post-start`, `post-switch`, `pre-commit`, `post-commit`, `pre-merge`, `post-merge`, `pre-remove`, `post-remove`, `approvals`.

Global flags: `--no-verify` (skip hooks), `--yes` (skip approval prompts), `-v` (verbose).
