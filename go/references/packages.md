# Go Package Design & Project Layout Reference

## 1. Package Naming

A package name answers: **"What does this package provide?"**

The name should be a noun that describes the thing, not the action.

```
GOOD            BAD
────            ───
http            util
json            common
user            helpers
auth            base
metric          shared
payment         misc
invoice         stuff
```

**Rules:**

- Lowercase, single word, no underscores, no mixedCaps.
- Short and specific — `bytes`, `net`, `os`, not `bytebuffers`, `networking`.
- Do not repeat the surrounding context: `http.Server`, not `http.HTTPServer`.
- Do not use generic grab-bag names. If you cannot name it specifically, you have not found the right boundary yet.
- The package name is part of every qualified call: `invoice.Create()` reads well; `util.CreateInvoice()` does not.

```go
// Good: the package name gives context to every symbol.
payment.Process(order)
metric.Record(latency)

// Bad: the package name adds nothing.
util.ProcessPayment(order)
helpers.RecordMetric(latency)
```

**The "what does it provide" test:** describe the package in one sentence without using "and." If you need "and," you probably need two packages.

---

## 2. Package Responsibility

Each package owns **one clear job**. Cohesion over convenience.

A `user` package handles user domain logic. It does not also handle email sending, database migrations, and CSV exports.

```go
// package user — manages user accounts.
type User struct { ... }
func Create(ctx context.Context, u User) error { ... }
func ByID(ctx context.Context, id string) (User, error) { ... }

// package email — sends emails. Separate concern.
func Send(ctx context.Context, msg Message) error { ... }
```

**Signs a package is doing too much:**

- It has many unrelated exported types.
- You struggle to write a single-sentence doc comment for the package.
- Callers import it but only use 10% of its surface.

**Signs you have too many packages:**

- Most packages export one or two types.
- You create packages just to mirror a directory tree.
- You constantly fight circular imports.

---

## 3. Export Discipline

**Unexported by default.** Export only when another package genuinely needs the symbol.

Every exported name is a **public promise**. Once external code depends on it, removing or changing it is a breaking change.

```go
// package auth

// Token is exported — callers need to pass it around.
type Token struct {
    Value     string
    ExpiresAt time.Time
}

// validate is unexported — internal detail, not a promise.
func validate(t Token) error { ... }

// Issue is exported — this is the package's job.
func Issue(ctx context.Context, creds Credentials) (Token, error) {
    if err := validate(Token{}); err != nil { ... }
    ...
}
```

**Guidelines:**

- Start unexported. Promote to exported when a real consumer needs it.
- Do not export "just in case." You can always export later; unexporting is a breaking change.
- Exported struct fields should be intentional. If a field is only set internally, keep it unexported and expose it via a method if needed.
- Prefer returning concrete types from constructors but accepting interfaces in function parameters.

---

## 4. Internal Packages

The `internal/` directory is **compiler-enforced** access control. Code under `internal/` can only be imported by code rooted at the parent of `internal/`.

```
myapp/
├── cmd/
│   └── server/
│       └── main.go          # can import myapp/internal/*
├── internal/
│   ├── auth/                 # only myapp and its subtree can import this
│   ├── postgres/             # database adapter — internal detail
│   └── worker/               # background job runner
└── go.mod
```

Use `internal/` for:

- Implementation details that callers should not depend on.
- Adapters (database, third-party API clients) that you want to swap freely.
- Domain logic that is not part of the public contract.

For libraries, `internal/` prevents users from depending on your implementation details, giving you freedom to refactor.

---

## 5. Application Layout

A practical layout for a Go service:

```
myapp/
├── cmd/
│   ├── server/
│   │   └── main.go           # entry point: wiring, config, run
│   └── migrate/
│       └── main.go           # separate binary for migrations
├── internal/
│   ├── auth/                  # authentication logic
│   ├── order/                 # order domain
│   ├── postgres/              # database adapter
│   ├── server/                # HTTP handlers, routing
│   └── config/                # configuration loading
├── go.mod
└── go.sum
```

**`cmd/`** — Each subdirectory is a `main` package producing one binary. Keep `main.go` thin: parse config, wire dependencies, call `run()`. No business logic here.

```go
// cmd/server/main.go
func main() {
    cfg := config.Load()
    db := postgres.Connect(cfg.DatabaseURL)
    srv := server.New(db, cfg)
    if err := srv.Run(); err != nil {
        log.Fatal(err)
    }
}
```

**`internal/`** — All application packages live here. Organized by **domain concern**, not by technical layer.

```
PREFERRED (by domain)      LESS IDIOMATIC (by layer)
─────────────────          ────────────────────────
internal/order/            internal/controllers/
internal/payment/          internal/services/
internal/invoice/          internal/repositories/
internal/postgres/         internal/models/
```

> **House opinion:** Domain-over-layer is our preferred layout. Layer-organized projects are not categorically wrong, but they tend to be less idiomatic in Go and scatter related code across directories.

Organizing by domain puts related code together. A developer working on orders finds handlers, types, and storage logic in one place, not scattered across three layer directories.

**`pkg/`** — Use sparingly or not at all. Only justified when you explicitly intend for other projects to import the code. Most applications do not need it. If in doubt, use `internal/`.

---

## 6. Library Layout

**Flat layout** — preferred for small-to-medium libraries:

```
errors/
├── errors.go
├── wrap.go
├── format.go
└── errors_test.go
```

Users import `errors` and get everything. Simple.

**Nested layout** — justified when sub-packages are independently useful:

```
cloud/
├── storage/
│   ├── storage.go
│   └── gcs/
│       └── gcs.go
├── pubsub/
│   └── pubsub.go
└── cloud.go               # package cloud — shared types, if any
```

**When to split into sub-packages:**

- The sub-package is independently useful (importable on its own).
- It has a distinct, nameable responsibility.
- It reduces the dependency footprint — users who need only `storage` should not pull in `pubsub` dependencies.

**When NOT to split:**

- You are splitting just because a file is long. Use multiple files in one package instead.
- The sub-package has one type and one function. Merge it up.
- The split creates circular dependencies.

---

## 7. Avoiding Circular Imports

Go forbids circular imports at compile time. If package A imports B and B imports A, the build fails. This is a feature — it forces clean dependency direction.

**Technique 1: Dependency inversion with interfaces**

```go
// package order — defines what it needs, does not import postgres.
type Store interface {
    Save(ctx context.Context, o Order) error
    ByID(ctx context.Context, id string) (Order, error)
}

// package postgres — implements order.Store without order importing postgres.
type OrderStore struct{ db *sql.DB }
func (s *OrderStore) Save(ctx context.Context, o order.Order) error { ... }
```

Dependency flows one way: `postgres` imports `order`. `order` knows nothing about `postgres`.

**Technique 2: Extract shared types into a third package**

If A and B both need type `T`, move `T` into package C that both import.

```go
// package domain — shared types, no logic, no dependencies.
type UserID string
type Order struct { ... }
```

**Technique 3: Merge the packages**

If two packages are so intertwined that separating them creates cycles, they probably belong together. A package can have multiple files.

**Technique 4: Wire at the top**

`cmd/main.go` is the composition root. It imports everything and wires dependencies. Domain packages import only what they define or what lives below them in the dependency graph.

---

## 8. Package Documentation

Every package should have a **doc comment** — a comment directly preceding the `package` clause.

For packages with multiple files, use a `doc.go` file:

```go
// doc.go

// Package auth provides authentication and token management for the
// application. It supports JWT-based authentication and integrates
// with external identity providers.
//
// Basic usage:
//
//     token, err := auth.Issue(ctx, creds)
//     if err != nil { ... }
//
//     claims, err := auth.Verify(ctx, token)
package auth
```

**Guidelines:**

- Start with "Package {name} ..." — `go doc` expects this format.
- Describe what the package provides, not how it works internally.
- Include a short usage example if the API is not obvious.
- Keep it updated. A stale doc comment is worse than none.
- Go 1.19+ doc comments support headings (`# Heading`), links (`[pkg.Symbol]`), and lists. Use them for richer `go doc` and `pkg.go.dev` output.

---

## 9. init() Functions

`init()` runs automatically at program start, in dependency order. It cannot be called or controlled by the caller.

**When acceptable:**

- Registering a database driver (`database/sql` pattern).
- Registering an encoding format (`image/png`).
- Setting up package-level compile-time checks.

```go
// Acceptable: compile-time interface check.
var _ http.Handler = (*Server)(nil)
```

**When to avoid (most of the time):**

- Loading configuration — use explicit initialization.
- Connecting to databases — use constructors.
- Anything with side effects that callers should control.

```go
// Bad: hidden side effect, untestable, panics at import time.
func init() {
    db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
    if err != nil {
        panic(err)
    }
    globalDB = db
}

// Good: explicit, testable, caller controls when and how.
func Connect(dsn string) (*Store, error) {
    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, fmt.Errorf("connect: %w", err)
    }
    return &Store{db: db}, nil
}
```

**Rule of thumb:** if it can fail, it should not be in `init()`.

---

## 10. API Evolution by Addition

Public Go APIs must evolve by **adding**, not by changing or removing.

**Adding a new function:**

```go
// v1 — original.
func Parse(s string) (T, error) { ... }

// v1.x — new capability, does not break existing callers.
func ParseWithOptions(s string, opts Options) (T, error) { ... }
```

**Functional options pattern for extensible constructors:**

```go
type Option func(*Server)

func WithTimeout(d time.Duration) Option {
    return func(s *Server) { s.timeout = d }
}

func WithLogger(l *slog.Logger) Option {
    return func(s *Server) { s.logger = l }
}

func New(addr string, opts ...Option) *Server {
    s := &Server{addr: addr, timeout: 30 * time.Second}
    for _, o := range opts {
        o(s)
    }
    return s
}

// Callers:
srv := server.New(":8080")                                     // works today
srv := server.New(":8080", server.WithTimeout(10*time.Second)) // works tomorrow
```

**Deprecation:**

```go
// Deprecated: Use ParseWithOptions instead.
func Parse(s string) (T, error) { ... }
```

The `// Deprecated:` comment is recognized by `go doc`, `staticcheck`, and IDEs. Keep the old function working; do not remove it until a major version bump.

**Major version import paths (`/v2`, `/v3`, ...):**

When you make a backward-incompatible change, Go modules require a new major version suffix on the module path:

```
module example.com/foo/v2
```

Callers import `example.com/foo/v2` and can coexist with `v1` in the same build. The source tree typically lives on a `v2` branch or under a `v2/` directory. Do not bump major versions lightly — prefer evolving by addition (see above) whenever possible.

---

## 11. Common Anti-Patterns

### The `util/common/helpers` package

```go
// BAD: grab-bag package with no identity.
package util

func FormatDate(t time.Time) string { ... }
func HashPassword(p string) (string, error) { ... }
func ParseCSV(r io.Reader) ([][]string, error) { ... }
```

**Fix:** Move each function to the package where it belongs.

```go
// FormatDate -> package report (or wherever dates are formatted for display)
// HashPassword -> package auth
// ParseCSV -> package importer
```

### One package per file / one type per package

```
BAD                         GOOD
───                         ────
models/                     order/
  user.go    (package models)   order.go      (types + logic)
  order.go   (package models)   store.go      (persistence interface)
  invoice.go (package models)   handler.go    (HTTP, if applicable)
```

A package can and should have multiple files. Files within a package all share the same namespace. Split by *concern within the package*, not by type.

### Deep nested hierarchies (Java-style)

```
BAD
───
com/
  mycompany/
    myapp/
      domain/
        entities/
          user/
            user.go
```

Go has no requirement for domain-based directory structures. Flat is better.

```
GOOD
────
internal/
  user/
    user.go
```

### Mechanical layering

```
LESS IDIOMATIC — organizes by technical role, scatters related code.
internal/
  controllers/
    order_controller.go
    user_controller.go
  services/
    order_service.go
    user_service.go
  repositories/
    order_repository.go
    user_repository.go
```

```
PREFERRED — organizes by domain, keeps related code together.
internal/
  order/
    order.go          # types
    service.go        # business logic
    handler.go        # HTTP handler
    store.go          # storage interface
  user/
    user.go
    service.go
    handler.go
    store.go
  postgres/
    order.go          # implements order.Store
    user.go           # implements user.Store
```

### Exporting everything "just in case"

```go
// BAD: everything exported, massive API surface.
type OrderService struct {
    DB        *sql.DB
    Cache     *redis.Client
    Logger    *slog.Logger
    Validator *validate.Validate
}

// GOOD: only export what callers need.
type Service struct {
    db        *sql.DB
    cache     *redis.Client
    logger    *slog.Logger
    validator *validate.Validate
}

func New(db *sql.DB, opts ...Option) *Service { ... }
func (s *Service) Create(ctx context.Context, o Order) error { ... }
```

Note: the struct name is `Service`, not `OrderService` — the package name `order` already provides context. Callers write `order.Service`, not `order.OrderService`.

---

## 12. Testing Packages

### Black-box vs white-box tests

Go supports two styles of test packages:

**White-box (same package):** Test file declares `package foo`. Tests can access unexported symbols. Use when you need to test internal state, edge cases in unexported helpers, or complex internal logic that is hard to exercise through the public API alone.

**Black-box (external test package):** Test file declares `package foo_test`. Tests can only use exported symbols — exactly like a real caller. Prefer this by default: it validates your public API, catches accidental export gaps, and keeps tests decoupled from implementation details.

```go
// order_test.go — black-box: tests the public contract.
package order_test

import (
    "testing"
    "myapp/internal/order"
)

func TestCreate(t *testing.T) {
    err := order.Create(ctx, validOrder)
    ...
}
```

```go
// order_internal_test.go — white-box: tests unexported internals.
package order

func Test_validate(t *testing.T) {
    err := validate(Order{})
    ...
}
```

**Rule of thumb:** start with `package foo_test`. Drop to `package foo` only when you cannot adequately cover a code path through the public API.

### The `testdata/` directory

Go's toolchain ignores directories named `testdata/` during builds. Use it for test fixtures — golden files, sample inputs, certificates, SQL dumps, etc. Tests read from it via relative paths (`"testdata/golden.json"`). This convention keeps test assets out of production binaries and clearly separated from source.
