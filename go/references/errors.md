# Go Error Handling Reference

> Errors are values. They are part of normal control flow — not exceptions,
> not surprises. Handle them explicitly, wrap them with context, and never
> discard them silently.

---

## 1. Error Wrapping with fmt.Errorf and %w

Wrap errors at meaningful boundaries to build a context chain. Use `%w` to
preserve the original error for inspection with `errors.Is`/`errors.As`.
Use `%v` (or just a new error) when you intentionally want to hide the
underlying cause from callers.

**Bad — naked return, no context:**

```go
func loadConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err // caller sees "open /etc/app.yaml: permission denied"
                        // but has no idea loadConfig was involved
    }
    // ...
}
```

**Good — wrap once with concise context:**

```go
func loadConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("load config: %w", err)
        // caller sees "load config: open /etc/app.yaml: permission denied"
    }
    // ...
}
```

**Avoid stuttering** — don't repeat what the wrapped error already says:

```go
// Bad: "read file: open /etc/app.yaml: permission denied"
//       ^^^^^^^^^ redundant — the inner error already says "open"
return nil, fmt.Errorf("read file: %w", err)

// Good: name the operation at YOUR level of abstraction
return nil, fmt.Errorf("load config: %w", err)
```

---

## 2. errors.Is and errors.As

`errors.Is` walks the entire error chain (unwrapping via `%w`) to check
for a specific sentinel value. `errors.As` does the same but matches by
type. Never compare wrapped errors with `==` — it breaks as soon as
anyone wraps the error.

**Bad — equality check on a potentially wrapped error:**

```go
if err == os.ErrNotExist {
    // This FAILS if err was wrapped: fmt.Errorf("load config: %w", os.ErrNotExist)
}
```

**Good — use errors.Is:**

```go
if errors.Is(err, os.ErrNotExist) {
    // Works regardless of how many layers of wrapping exist
    return defaultConfig, nil
}
```

**Good — use errors.As for custom types:**

```go
var pathErr *fs.PathError
if errors.As(err, &pathErr) {
    log.Printf("operation %s failed on path %s", pathErr.Op, pathErr.Path)
}
```

Note: The target for `errors.As` must be a pointer to the type you want
(pointer-to-pointer for pointer-receiver error types).

---

## 3. Sentinel Errors vs Custom Error Types

Use **sentinel errors** (`var ErrNotFound = errors.New(...)`) when the
caller only needs to know *what* happened. Use **custom error types**
(`type ValidationError struct{...}`) when the caller needs structured
data about the failure. Don't reach for custom types unless you have
fields to expose.

**Sentinel errors — simple, sufficient for most cases:**

```go
// Define at package level. Convention: Err prefix.
var (
    ErrNotFound   = errors.New("not found")
    ErrConflict   = errors.New("conflict")
    ErrForbidden  = errors.New("forbidden")
)

func GetUser(id string) (*User, error) {
    var u User
    row := db.QueryRow("SELECT name, email FROM users WHERE id = $1", id)
    err := row.Scan(&u.Name, &u.Email)
    if errors.Is(err, sql.ErrNoRows) {
        return nil, fmt.Errorf("get user %s: %w", id, ErrNotFound)
    }
    if err != nil {
        return nil, fmt.Errorf("get user %s: %w", id, err)
    }
    return &u, nil
}
```

**Custom error types — when callers need structured detail:**

```go
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation: %s: %s", e.Field, e.Message)
}

func ParseAge(s string) (int, error) {
    n, err := strconv.Atoi(s)
    if err != nil {
        return 0, &ValidationError{Field: "age", Message: "must be a number"}
    }
    if n < 0 || n > 150 {
        return 0, &ValidationError{Field: "age", Message: "out of range"}
    }
    return n, nil
}

// Caller inspects:
var ve *ValidationError
if errors.As(err, &ve) {
    respondJSON(w, 422, map[string]string{"field": ve.Field, "error": ve.Message})
}
```

---

## 4. The "Log or Return, Never Both" Rule

Every error should be either returned (with context) to the caller OR
logged and handled — never both. Logging and returning produces duplicate
log lines that make debugging harder, not easier. Log errors at **process
boundaries**: HTTP handlers, main(), background workers, message consumers.

**Bad — log AND return at every layer:**

```go
func getUser(id string) (*User, error) {
    u, err := db.FindUser(id)
    if err != nil {
        log.Printf("failed to find user: %v", err) // logged here
        return nil, fmt.Errorf("get user: %w", err) // AND returned
    }
    return u, nil
}

func handleGetUser(w http.ResponseWriter, r *http.Request) {
    u, err := getUser(r.URL.Query().Get("id"))
    if err != nil {
        log.Printf("handleGetUser error: %v", err) // logged AGAIN
        http.Error(w, "internal error", 500)
        return
    }
    // ...
}
```

**Good — inner functions return, boundary logs:**

```go
func getUser(id string) (*User, error) {
    u, err := db.FindUser(id)
    if err != nil {
        return nil, fmt.Errorf("get user: %w", err) // return only
    }
    return u, nil
}

func handleGetUser(w http.ResponseWriter, r *http.Request) {
    u, err := getUser(r.URL.Query().Get("id"))
    if err != nil {
        log.Printf("handleGetUser: %v", err) // log once, at the boundary
        http.Error(w, "internal error", 500)
        return
    }
    json.NewEncoder(w).Encode(u)
}
```

---

## 5. Error Context Stacking

Build readable error chains by having each function prepend its own
operation name. The resulting chain reads like a stack trace in plain
English: `"start server: load config: parse yaml: line 12: invalid key"`.
Keep prefixes short and lowercase. Don't include "error" or "failed" — the
fact that it's an error is already clear from the return position.

**Bad — verbose, noisy prefixes:**

```go
return nil, fmt.Errorf("Error: failed to read configuration file: %w", err)
// produces: "Error: failed to read configuration file: open config.yaml: no such file"
```

**Good — terse, stacking naturally:**

```go
// In main:
return fmt.Errorf("start server: %w", err)

// In loadConfig:
return nil, fmt.Errorf("load config: %w", err)

// In parseYAML:
return nil, fmt.Errorf("parse yaml: %w", err)

// Final message: "start server: load config: parse yaml: unexpected field at line 12"
```

Each layer names its own operation. The chain is readable left-to-right
from high-level to low-level.

---

## 6. When to Use panic vs Error Return

`panic` is reserved for **programmer errors** (invariant violations, impossible
states) and **irrecoverable startup failures** (missing required env, broken
database migration). Anything that can happen at runtime due to user input,
network conditions, or file system state must be returned as an error.

**Bad — panic on normal runtime failure:**

```go
func ParseConfig(data []byte) *Config {
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        panic(err) // malformed input is NOT a programmer error
    }
    return &cfg
}
```

**Good — return an error for expected failures:**

```go
func ParseConfig(data []byte) (*Config, error) {
    var cfg Config
    if err := json.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("parse config: %w", err)
    }
    return &cfg, nil
}
```

**Acceptable panic — startup invariant:**

```go
func mustLoadTemplates() *template.Template {
    t, err := template.ParseGlob("templates/*.html")
    if err != nil {
        panic(fmt.Sprintf("load templates: %v", err)) // app cannot function without these
    }
    return t
}

// Convention: prefix function name with "must" when it panics on error.
```

**Acceptable panic — impossible state:**

```go
func direction(d int) string {
    switch d {
    case 0: return "north"
    case 1: return "east"
    case 2: return "south"
    case 3: return "west"
    default:
        panic(fmt.Sprintf("invalid direction: %d", d)) // programmer bug
    }
}
```

**Recovering from panics at boundaries:**

Even though your own code should not panic for runtime errors, third-party
libraries or unexpected nil dereferences can still panic. Use `defer`/`recover`
at goroutine boundaries and HTTP middleware to convert panics into errors
instead of crashing the entire process.

```go
// HTTP middleware — convert panics to 500 responses
func recoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if v := recover(); v != nil {
                log.Printf("panic recovered: %v\n%s", v, debug.Stack())
                http.Error(w, "internal error", 500)
            }
        }()
        next.ServeHTTP(w, r)
    })
}

// Goroutine boundary — prevent one task from killing the process
func safeGo(fn func() error) <-chan error {
    ch := make(chan error, 1)
    go func() {
        defer func() {
            if v := recover(); v != nil {
                ch <- fmt.Errorf("panic: %v", v)
            }
        }()
        ch <- fn()
    }()
    return ch
}
```

Never use `recover` to swallow panics silently — always log them. And never
use `recover` as a substitute for proper error returns in your own code.

---

## 7. errors.Join for Multi-Errors (Go 1.20+)

`errors.Join` combines multiple errors into one. The result works with
both `errors.Is` and `errors.As` — it checks all joined children.
Use it for operations that can produce multiple independent failures
(batch processing, cleanup, multi-step validation).

**Example — batch processing with collected errors:**

```go
func validateUser(u User) error {
    var errs []error
    if u.Name == "" {
        errs = append(errs, &ValidationError{Field: "name", Message: "required"})
    }
    if u.Email == "" {
        errs = append(errs, &ValidationError{Field: "email", Message: "required"})
    }
    if u.Age < 0 {
        errs = append(errs, &ValidationError{Field: "age", Message: "must be positive"})
    }
    return errors.Join(errs...) // returns nil if errs is empty
}
```

**Example — cleanup with deferred error collection:**

```go
func process(r io.ReadCloser) (err error) {
    defer func() {
        if cerr := r.Close(); cerr != nil {
            err = errors.Join(err, fmt.Errorf("close reader: %w", cerr))
        }
    }()

    data, err := io.ReadAll(r)
    if err != nil {
        return fmt.Errorf("read: %w", err)
    }
    // ... process data
    return nil
}
```

`errors.Is` and `errors.As` both work on joined errors:

```go
err := errors.Join(ErrNotFound, ErrForbidden)
errors.Is(err, ErrNotFound)  // true
errors.Is(err, ErrForbidden) // true
```

**Multiple `%w` in `fmt.Errorf` (Go 1.20+):**

Since Go 1.20, `fmt.Errorf` supports multiple `%w` verbs in a single call.
The resulting error wraps all of them, so `errors.Is` and `errors.As` match
against every wrapped error. This is useful when a single operation fails
for two distinguishable reasons you want callers to inspect independently.

```go
err := fmt.Errorf("save order: %w, also: %w", ErrValidation, ErrConflict)
errors.Is(err, ErrValidation) // true
errors.Is(err, ErrConflict)   // true
```

Prefer `errors.Join` when collecting a slice of independent errors (batch
processing). Prefer multiple `%w` when you want a single descriptive message
that attributes two known causes inline.

---

## 8. Common Anti-Patterns

### 8a. Naked returns without context

```go
// Bad
if err != nil {
    return err
}

// Good
if err != nil {
    return fmt.Errorf("save order: %w", err)
}
```

Every `return err` is a missed opportunity to add context. The only
exception is when you are a trivially thin wrapper and adding context
would stutter (e.g., a one-line function that just delegates).

### 8b. Logging and returning the same error

```go
// Bad — produces duplicate log entries
if err != nil {
    log.Printf("query failed: %v", err)
    return fmt.Errorf("query: %w", err)
}

// Good — return with context, let the boundary log
if err != nil {
    return fmt.Errorf("query users: %w", err)
}
```

### 8c. Comparing wrapped errors with ==

```go
// Bad — fragile, breaks when errors are wrapped
if err == sql.ErrNoRows {
    return nil, ErrNotFound
}

// Good — walks the entire error chain
if errors.Is(err, sql.ErrNoRows) {
    return nil, ErrNotFound
}
```

### 8d. Using strings.Contains on error messages

```go
// Bad — brittle, breaks on message changes, impossible to refactor safely
if strings.Contains(err.Error(), "not found") {
    return nil, ErrNotFound
}

// Good — use sentinel errors or error types
if errors.Is(err, ErrNotFound) {
    return nil, ErrNotFound
}
```

Error messages are for humans. Program logic should use `errors.Is`,
`errors.As`, or sentinel values — never string matching.

### 8e. Panic for validation or IO failures

```go
// Bad — validation failure is normal, not a programmer error
func MustParseAge(s string) int {
    n, err := strconv.Atoi(s)
    if err != nil {
        panic(err)
    }
    return n
}

// Good — return the error
func ParseAge(s string) (int, error) {
    n, err := strconv.Atoi(s)
    if err != nil {
        return 0, fmt.Errorf("parse age: %w", err)
    }
    return n, nil
}
```

---

## Quick Decision Guide

| Situation | Action |
|---|---|
| Function fails, caller should decide | Return `fmt.Errorf("op: %w", err)` |
| Caller needs to check error kind | Wrap a sentinel: `fmt.Errorf("op: %w", ErrNotFound)` |
| Caller needs structured error data | Return `&CustomError{...}` |
| Multiple independent failures | Collect and `errors.Join(errs...)` |
| Process boundary (handler, main) | Log the error, respond/exit |
| Impossible state, broken invariant | `panic(...)` |
| App cannot start without resource | `panic(...)` or `log.Fatal(...)` |

---

## Imports Cheat Sheet

```go
import (
    "errors" // errors.New, errors.Is, errors.As, errors.Join
    "fmt"    // fmt.Errorf with %w
)
```
