# Tips & Patterns — Full Recipes

Complete code examples for common Worktrunk workflows. Read this when helping users set up specific patterns.

## Table of Contents
1. [Alias for new worktree + agent](#alias)
2. [Eliminate cold starts](#cold-starts)
3. [Dev server per worktree](#dev-server)
4. [Database per worktree](#database)
5. [Local CI gate](#local-ci)
6. [Manual commit messages](#manual-commits)
7. [Track agent status](#agent-status)
8. [Monitor CI across branches](#ci-monitoring)
9. [LLM branch summaries](#branch-summaries)
10. [JSON API for scripting](#json-api)
11. [Stacked branches](#stacked)
12. [Agent handoffs](#agent-handoffs)
13. [Tmux session per worktree](#tmux)
14. [Subdomain routing with Caddy](#caddy)
15. [Bare repository layout](#bare-repo)
16. [Monitor hook logs](#hook-logs)
17. [Xcode DerivedData cleanup](#xcode)
18. [Task runners in hooks](#task-runners)
19. [Reuse default-branch](#reuse-default)
20. [Shortcuts](#shortcuts)

---

<a id="alias"></a>
## Alias for New Worktree + Agent

```bash
alias wsc='wt switch --create --execute=claude'
wsc new-feature                       # Creates worktree, runs hooks, launches Claude
wsc feature -- 'Fix GH #322'          # Runs `claude 'Fix GH #322'`
```

<a id="cold-starts"></a>
## Eliminate Cold Starts

Use `wt step copy-ignored` to copy gitignored files (caches, dependencies, `.env`):

```toml
# .config/wt.toml
[post-start]
copy = "wt step copy-ignored"
```

Use `post-create` instead if subsequent hooks or `--execute` command need the copied files immediately.

<a id="dev-server"></a>
## Dev Server Per Worktree

Each worktree runs its own dev server on a deterministic port:

```toml
# .config/wt.toml
[post-start]
server = "npm run dev -- --port {{ branch | hash_port }}"

[list]
url = "http://localhost:{{ branch | hash_port }}"

[pre-remove]
server = "lsof -ti :{{ branch | hash_port }} -sTCP:LISTEN | xargs kill 2>/dev/null || true"
```

The URL column in `wt list` shows each worktree's dev server. Ports are deterministic — `fix-auth` always gets the same port regardless of machine. The URL dims if the server isn't running.

<a id="database"></a>
## Database Per Worktree

Docker containers with unique names and ports:

```toml
# .config/wt.toml
[post-start]
db = """
docker run -d --rm \
  --name {{ repo }}-{{ branch | sanitize }}-postgres \
  -p {{ ('db-' ~ branch) | hash_port }}:5432 \
  -e POSTGRES_DB={{ branch | sanitize_db }} \
  -e POSTGRES_PASSWORD=dev \
  postgres:16
"""

[pre-remove]
db-stop = "docker stop {{ repo }}-{{ branch | sanitize }}-postgres 2>/dev/null || true"
```

The `('db-' ~ branch)` concatenation hashes differently than plain `branch`, so database and dev server ports don't collide. Parentheses required because `|` has higher precedence than `~`.

Generate `.env.local` with correct `DATABASE_URL`:

```toml
[post-create]
env = """
cat > .env.local << EOF
DATABASE_URL=postgres://postgres:dev@localhost:{{ ('db-' ~ branch) | hash_port }}/{{ branch | sanitize_db }}
DEV_PORT={{ branch | hash_port }}
EOF
"""
```

<a id="local-ci"></a>
## Local CI Gate

`pre-merge` hooks run before merging. Failures abort the merge:

```toml
# .config/wt.toml
[pre-merge]
lint = "npm run lint"
typecheck = "npm run typecheck"
test = "npm test"
build = "npm run build"
```

Progressive validation — quick checks before commit, thorough before merge:

```toml
[pre-commit]
lint = "npm run lint"
typecheck = "npm run typecheck"

[pre-merge]
test = "npm test"
build = "npm run build"
```

<a id="manual-commits"></a>
## Manual Commit Messages

Skip LLM generation:

```bash
git add -A && git commit -m "my message"
```

Or use `wt step commit --show-prompt` to see what would be sent to the LLM without running it.

<a id="agent-status"></a>
## Track Agent Status

With the Claude Code plugin, `wt list` shows 🤖 (working) and 💬 (waiting).

Set markers manually:

```bash
wt config state marker set "🚧"                   # Current branch
wt config state marker set "✅" --branch feature   # Specific branch
```

<a id="ci-monitoring"></a>
## Monitor CI Across Branches

```bash
wt list --full    # CI column shows pass/fail from GitHub Actions or GitLab CI
```

Requires `gh` (GitHub) or `glab` (GitLab) CLI installed. Override detection:

```toml
# .config/wt.toml
[ci]
platform = "github"  # or "gitlab"
```

<a id="branch-summaries"></a>
## LLM Branch Summaries

```toml
# ~/.config/worktrunk/config.toml
[list]
summary = true
```

With `commit.generation` configured, `wt list --full` shows LLM-generated one-line summaries. Same summaries appear in the `wt switch` interactive picker.

<a id="json-api"></a>
## JSON API for Scripting

```bash
# Current worktree path
wt list --format=json | jq -r '.[] | select(.is_current) | .path'

# Branches with uncommitted changes
wt list --format=json | jq '.[] | select(.working_tree.modified)'

# Integrated branches (safe to remove)
wt list --format=json | jq '.[] | select(.main_state == "integrated" or .main_state == "empty") | .branch'

# Branches ahead of remote
wt list --format=json | jq '.[] | select(.remote.ahead > 0) | {branch, ahead: .remote.ahead}'
```

<a id="stacked"></a>
## Stacked Branches

Branch from current HEAD instead of the default branch:

```bash
wt switch --create feature-part2 --base=@
```

<a id="agent-handoffs"></a>
## Agent Handoffs

Spawn a worktree with Claude running in the background:

**tmux** (new detached session):
```bash
tmux new-session -d -s fix-auth-bug "wt switch --create fix-auth-bug -x claude -- \
  'The login session expires after 5 minutes. Find the session timeout config and extend it to 24 hours.'"
```

**Zellij** (new pane in current session):
```bash
zellij run -- wt switch --create fix-auth-bug -x claude -- \
  'The login session expires after 5 minutes. Find the session timeout config and extend it to 24 hours.'
```

To enable in CLAUDE.md:
```
When I ask you to spawn parallel worktrees, use the agent handoff pattern
from the worktrunk skill.
```

<a id="tmux"></a>
## Tmux Session Per Worktree

Multi-pane layout per worktree:

```toml
# .config/wt.toml
[post-create]
tmux = """
S={{ branch | sanitize }}
W={{ worktree_path }}
tmux new-session -d -s "$S" -c "$W" -n dev

# Create 4-pane layout: shell | backend / claude | frontend
tmux split-window -h -t "$S:dev" -c "$W"
tmux split-window -v -t "$S:dev.0" -c "$W"
tmux split-window -v -t "$S:dev.2" -c "$W"

# Start services in each pane
tmux send-keys -t "$S:dev.1" 'npm run backend' Enter
tmux send-keys -t "$S:dev.2" 'claude' Enter
tmux send-keys -t "$S:dev.3" 'npm run frontend' Enter

tmux select-pane -t "$S:dev.0"
echo "✓ Session '$S' — attach with: tmux attach -t $S"
"""

[pre-remove]
tmux = "tmux kill-session -t {{ branch | sanitize }} 2>/dev/null || true"
```

Attach immediately: `wt switch --create feature -x 'tmux attach -t {{ branch | sanitize }}'`

<a id="caddy"></a>
## Subdomain Routing with Caddy

Clean URLs like `http://feature-auth.myproject.localhost` without port numbers:

```toml
# .config/wt.toml
[post-start]
server = "npm run dev -- --port {{ branch | hash_port }}"
proxy = """
  curl -sf --max-time 0.5 http://localhost:2019/config/ || caddy start
  curl -sf http://localhost:2019/config/apps/http/servers/wt || \
    curl -sfX PUT http://localhost:2019/config/apps/http/servers/wt -H 'Content-Type: application/json' \
      -d '{"listen":[":8080"],"automatic_https":{"disable":true},"routes":[]}'
  curl -sf -X DELETE http://localhost:2019/id/wt:{{ repo }}:{{ branch | sanitize }} || true
  curl -sfX PUT http://localhost:2019/config/apps/http/servers/wt/routes/0 -H 'Content-Type: application/json' \
    -d '{"@id":"wt:{{ repo }}:{{ branch | sanitize }}","match":[{"host":["{{ branch | sanitize }}.{{ repo }}.localhost"]}],"handle":[{"handler":"reverse_proxy","upstreams":[{"dial":"127.0.0.1:{{ branch | hash_port }}"}]}]}'
"""

[pre-remove]
proxy = "curl -sf -X DELETE http://localhost:2019/id/wt:{{ repo }}:{{ branch | sanitize }} || true"

[list]
url = "http://{{ branch | sanitize }}.{{ repo }}.localhost:8080"
```

Requires Caddy: `brew install caddy`

<a id="bare-repo"></a>
## Bare Repository Layout

All branches as equal worktrees under one directory:

```bash
git clone --bare <url> myproject/.git
cd myproject
```

Configure:
```toml
# ~/.config/worktrunk/config.toml
worktree-path = "{{ repo_path }}/../{{ branch | sanitize }}"
```

Create first worktree: `wt switch --create main`. Now `wt switch --create feature` creates `myproject/feature/`.

```
myproject/
├── .git/       # bare repository
├── main/       # default branch
├── feature/    # feature branch
└── bugfix/     # bugfix branch
```

<a id="hook-logs"></a>
## Monitor Hook Logs

```bash
tail -f "$(wt config state logs get --hook=user:post-start:server)"
```

Format: `source:hook-type:name`. Create an alias:
```bash
alias wtlog='f() { tail -f "$(wt config state logs get --hook="$1")"; }; f'
```

<a id="xcode"></a>
## Xcode DerivedData Cleanup

```toml
# ~/.config/worktrunk/config.toml
[post-remove]
clean-derived = """
  grep -Fl {{ worktree_path }} \
    ~/Library/Developer/Xcode/DerivedData/*/info.plist 2>/dev/null \
  | while read plist; do
      derived_dir=$(dirname "$plist")
      rm -rf "$derived_dir"
      echo "Cleaned DerivedData: $derived_dir"
    done
"""
```

<a id="task-runners"></a>
## Task Runners in Hooks

```toml
[post-create]
setup = "task install"

[pre-merge]
validate = "just test lint"
```

<a id="reuse-default"></a>
## Reuse Default Branch

```bash
git rebase $(wt config state default-branch)
```

<a id="shortcuts"></a>
## Shortcuts

```bash
wt switch --create hotfix --base=@   # Branch from current HEAD
wt switch -                          # Previous worktree
wt remove @                          # Remove current worktree
```

## Python Virtual Environments

```toml
[pre-start]
install = "uv sync"
```

Don't copy venvs — they contain absolute paths. Use `uv sync` to recreate.
