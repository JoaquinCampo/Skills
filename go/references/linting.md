# Go Linting and Static Analysis Reference

## Doctrine

- `gofmt` is mandatory. There are no style debates.
- `staticcheck` is the default static analyzer.
- `golangci-lint` is acceptable as a runner, but lint rules stay minimal and high-signal.
- Every lint rule must earn its place. Do not add noise.

---

## 1. gofmt and goimports

These are non-negotiable. Run on every save, enforce in CI.

`gofmt` formats Go code to the canonical style. There is no configuration — that is the point.

`goimports` does everything `gofmt` does, plus manages import grouping and removal of unused imports.

`gofumpt` is a stricter superset of `gofmt` — it enforces additional formatting rules (e.g., no empty lines at the start/end of function bodies, grouped variable declarations). Consider it if your team wants tighter formatting consistency beyond what `gofmt` provides. Note: `gofumpt` is a third-party community tool (`mvdan.cc/gofumpt`), not part of the official Go toolchain. Install with `go install mvdan.cc/gofumpt@latest`.

```bash
# Format all files in the module
gofmt -w .

# Use goimports instead (superset of gofmt)
goimports -w .

# Use gofumpt for stricter formatting (superset of gofmt)
gofumpt -w .
```

**Editor setup:** Configure your editor to run `goimports` on save. Every major Go editor plugin supports this out of the box. If using `gofumpt`, configure it as the formatter instead.

**CI check:**
```bash
# Fail if any file is not formatted
test -z "$(gofmt -l .)"
```

---

## 2. go vet

Built into the Go toolchain. Always run it — zero configuration required.

```bash
go vet ./...
```

**What it catches:**
- Printf format string mismatches
- Unreachable code
- Suspicious mutex usage (copying locks)
- Invalid struct tags
- Incorrect use of `append` (assigning to wrong variable)
- Boolean conditions that are always true/false
- Misuse of `unsafe.Pointer`

`go vet` is conservative. It reports very few false positives. If it flags something, fix it.

**Note:** Since Go 1.10, `go test` automatically runs `go vet` before executing tests. You get `go vet` coverage for free in your test pipeline — but you should still run it explicitly in CI for non-test packages and for clearer error reporting.

---

## 3. staticcheck — The Gold Standard

`staticcheck` is the single most valuable static analyzer for Go. It catches real bugs with extremely low false-positive rates.

```bash
# Install (pin to a specific version for CI reproducibility)
go install honnef.co/go/tools/cmd/staticcheck@v0.5.1

# Run
staticcheck ./...
```

**CI tip:** Pin `staticcheck` to a specific version (e.g., `@v0.5.1`) rather than `@latest` to ensure reproducible builds. Different versions may add or remove checks, causing spurious CI failures. Update the pinned version deliberately as part of a maintenance cycle.

**Key check categories:**

| Prefix | Category | Examples |
|--------|----------|---------|
| SA | Static analysis (bugs) | nil dereference, dead code, infinite loops |
| S | Simplifications | Unnecessary `fmt.Sprintf`, redundant `return` |
| ST | Style | Poorly named error variables, unexported return types |
| QF | Quick fixes | Suggested rewrites |

**Configuration** (`staticcheck.conf` in project root):
```toml
# Only disable checks you have a documented reason to skip
checks = ["all", "-ST1000", "-ST1003"]
# ST1000: package comments — disable only if you have a good reason
# ST1003: naming conventions — sometimes conflicts with domain terms
```

**Rule of thumb:** Start with `checks = ["all"]` and only disable specific checks if they produce false positives for your codebase.

---

## 4. golangci-lint as a Runner

`golangci-lint` is not a linter — it is a runner that orchestrates many linters. Use it to consolidate your lint pipeline, but keep the enabled set minimal.

```bash
# Install (prefer binary, not go install)
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin

# Run
golangci-lint run ./...
```

**Do not** use `--enable-all`. That enables 50+ linters, most of which produce noise.

---

## 5. Recommended Linter Set

### Core (always enable)

| Linter | What it catches | Why it earns its place |
|--------|----------------|----------------------|
| `staticcheck` | Bugs, simplifications, style | Gold standard, near-zero false positives |
| `govet` | Suspicious constructs | Built-in, conservative, catches real issues |
| `errcheck` | Unchecked errors | Ignoring errors is Go's #1 bug source |
| `ineffassign` | Ineffectual assignments | Dead stores hide bugs |
| `unused` | Unused code | Dead code is maintenance debt |
| `gosimple` | Simplifications | Part of staticcheck suite, suggests cleaner code |

> **Note:** Since golangci-lint v1.49+, `gosimple` and `unused` are aliases for sub-analyzers within `staticcheck`. When you enable `staticcheck` in golangci-lint, you already get `gosimple` and `unused` checks. They are listed separately here for clarity — if running standalone staticcheck, these are built in. In golangci-lint, enabling them explicitly is harmless but redundant.

### Optional (earn their place in most projects)

| Linter | What it catches | When to add |
|--------|----------------|-------------|
| `gocritic` | Opinionated but useful checks | When the team wants stricter code review automation |
| `revive` | Configurable replacement for golint | Only with specific rules enabled, never the full default set |
| `exhaustive` | Non-exhaustive enum switches | When you use enums extensively and want compile-time-like safety |

**Rationale for exclusions:** Linters like `gocyclo`, `funlen`, `wsl`, `godot`, `nlreturn`, and `varnamelen` enforce stylistic preferences that generate noise without catching bugs. Do not enable them.

---

## 6. Configuration Examples

### Recommended `.golangci.yml`

```yaml
run:
  timeout: 5m
  modules-download-mode: readonly

linters:
  disable-all: true
  enable:
    - errcheck
    - govet
    - staticcheck
    - gosimple
    - ineffassign
    - unused
    # Optional — uncomment if the team agrees:
    # - gocritic
    # - exhaustive

linters-settings:
  errcheck:
    # Check type assertions
    check-type-assertions: true
    # Do not ignore closing of HTTP response bodies
    check-blank: false

  govet:
    enable-all: true

  staticcheck:
    checks: ["all"]

  # Only configure if you enable gocritic:
  # gocritic:
  #   enabled-tags:
  #     - diagnostic
  #     - performance
  #   disabled-checks:
  #     - commentedOutCode
  #     - hugeParam

  # Only configure if you enable exhaustive:
  # exhaustive:
  #   default-signifies-exhaustive: true

issues:
  # Show all issues from a linter, not just the first N
  max-issues-per-linter: 0
  max-same-issues: 0

  exclude-rules:
    # Test files can have longer functions, unused params, etc.
    - path: _test\.go
      linters:
        - errcheck
        - gocritic

    # Allow dot-imports in test files for testing frameworks
    - path: _test\.go
      text: "dot-imports"

    # Exclude generated code from all linters (protobuf, wire, ent, etc.)
    - path: ".*\\.pb\\.go$"
      linters: []  # skip all linters
    - path: ".*_gen\\.go$"
      linters: []
    - path: "wire_gen\\.go$"
      linters: []
    - source: "^// Code generated .* DO NOT EDIT\\.$"
      linters: []
```

> **Excluding generated code:** Generated files (protobuf `.pb.go`, Wire `wire_gen.go`, Ent, sqlc, etc.) should never be linted — they are machine-authored and not meant for human editing. The `exclude-rules` above cover common patterns. Additionally, most Go code generators include a `// Code generated ... DO NOT EDIT.` comment that golangci-lint can match via the `source` directive.

### Recommended `staticcheck.conf` (if running standalone)

```toml
checks = ["all"]
```

---

## 7. CI Integration

### Basic CI step

```yaml
# GitHub Actions example
- name: Lint
  uses: golangci/golangci-lint-action@v6
  with:
    version: v2.1
    args: --timeout=5m
```

### Fail-on-new-only strategy

When adding linters to an existing codebase, avoid fixing thousands of existing issues at once. Use `--new-from-rev` to only fail on new issues:

```bash
# Only report issues in code changed since main
golangci-lint run --new-from-rev=origin/main ./...
```

In CI config:
```yaml
- name: Lint (new issues only)
  uses: golangci/golangci-lint-action@v6
  with:
    version: v2.1
    args: --new-from-rev=origin/main --timeout=5m
```

**Migration path:**
1. Enable linters with `--new-from-rev` so new code is clean.
2. Fix existing issues incrementally, file by file, as you touch code.
3. Once the baseline is clean, remove `--new-from-rev`.

### Pre-commit hook (optional)

```bash
#!/bin/sh
# .git/hooks/pre-commit
golangci-lint run --new-from-rev=HEAD~1 ./...
```

> The `--new` flag is deprecated since golangci-lint v1.x. Use `--new-from-rev=HEAD~1` instead.

---

## 8. go vet vs staticcheck vs golangci-lint

| Tool | Scope | When to use |
|------|-------|-------------|
| `go vet` | Built-in conservative checks | Always. Part of `go test` pipeline. |
| `staticcheck` | Deep static analysis, simplifications | Always. The single best standalone analyzer. |
| `golangci-lint` | Meta-runner for many linters | When you need multiple linters in one pass. |

**Overlap:** `golangci-lint` can run both `govet` and `staticcheck` internally. If you use `golangci-lint`, you get all three in one command. If you prefer standalone tools, run `go vet` and `staticcheck` separately.

**Recommendation:** Use `golangci-lint` in CI (one tool, one config file). Use `staticcheck` and `go vet` directly during development if you prefer faster feedback.

---

## 9. nolint Directives

Suppress a lint finding only when you understand why the linter flagged it and have a documented reason to disagree.

```go
// CORRECT — always include the linter name and a reason
//nolint:errcheck // fire-and-forget: best-effort logging, error is intentionally ignored
logger.Sync()

// CORRECT — scoped to a specific linter
//nolint:gosimple // intentional: verbose form is clearer for readers unfamiliar with this API
result := fmt.Sprintf("%s", value)

// WRONG — blanket suppression, no reason
//nolint
doSomething()

// WRONG — no explanation
//nolint:errcheck
file.Close()
```

**Rules:**
- Always specify the linter: `//nolint:errcheck`, not `//nolint`.
- Always include a reason after `//`.
- If you find yourself adding many `nolint` directives, reconsider whether the code should be restructured.
- Review `nolint` directives in code review the same way you review `TODO` comments.

---

## 10. Anti-Patterns

### Enabling every linter

```yaml
# DO NOT DO THIS
linters:
  enable-all: true
```

This enables 50+ linters with conflicting opinions. You will spend more time fighting lint noise than writing code. Start with the core six and add linters only when they catch a real issue.

### Disabling linters without explanation

```go
// This is tech debt disguised as pragmatism
//nolint
func doEverything() { ... }
```

Every `nolint` without a reason is a future debugging session waiting to happen.

### Fighting linters instead of understanding them

If a linter flags your code, the default assumption should be that the linter is right. Investigate before suppressing. Staticcheck and govet have near-zero false positive rates — if they flag something, there is almost certainly an issue.

### Inconsistent linter config across the team

The `.golangci.yml` file belongs in the repository root, committed and versioned. Every developer and CI pipeline must use the same configuration. Never rely on individual editor settings for lint rules.

```
# Verify everyone uses the same config
golangci-lint config
# Shows which config file is being used and its resolved path
```

---

## Quick Start Checklist

1. Add `.golangci.yml` to repo root with the core six linters.
2. Configure editor to run `goimports` on save.
3. Add `golangci-lint` step to CI.
4. Use `--new-from-rev` if the codebase has existing issues.
5. Review and adjust linter set quarterly — add only what catches real bugs.
