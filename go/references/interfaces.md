# Go Interface Design Reference

## 1. Concrete First

Start with concrete types. Do not reach for an interface until you feel real pain without one.

```go
// GOOD — start concrete
type UserStore struct {
    db *sql.DB
}

func (s *UserStore) FindByID(ctx context.Context, id int64) (*User, error) {
    // ...
}

func NewService(store *UserStore) *Service {
    return &Service{store: store}
}
```

```go
// BAD — premature interface, one implementation exists
type UserRepository interface {
    FindByID(ctx context.Context, id int64) (*User, error)
}

type userRepositoryImpl struct { db *sql.DB }
```

A concrete type is simpler to navigate, debug, and refactor. Introduce an interface
only when a second consumer or a test boundary forces you to.

---

## 2. Consumer-Side Interfaces

Define interfaces where they are **used**, not where they are implemented.
The consumer knows what it needs; the producer should not guess.

```go
// package order — the CONSUMER defines what it needs
type PaymentCharger interface {
    Charge(ctx context.Context, amount Money) (Receipt, error)
}

type Service struct {
    charger PaymentCharger
}
```

```go
// package payment — the PRODUCER exports a concrete type, no interface
type StripeClient struct { /* ... */ }

func (c *StripeClient) Charge(ctx context.Context, amount Money) (Receipt, error) {
    // ...
}
```

The `order` package never imports a `payment.PaymentCharger` interface.
It declares its own narrow contract. `StripeClient` satisfies it implicitly.

```go
// BAD — producer-exported interface
package payment

type Charger interface {          // Who consumes this? Everyone? Nobody?
    Charge(ctx context.Context, amount Money) (Receipt, error)
    Refund(ctx context.Context, id string) error
    ListTransactions(ctx context.Context) ([]Tx, error)
}
```

---

## 3. Small Interfaces

The best Go interfaces have one or two methods. The stdlib sets the standard:

| Interface      | Methods |
|---------------|---------|
| `io.Reader`    | 1       |
| `io.Writer`    | 1       |
| `fmt.Stringer` | 1       |
| `io.Closer`    | 1       |
| `sort.Interface` | 3     |

```go
// GOOD — single-method interface, infinitely composable
type Validator interface {
    Validate() error
}

type Sender interface {
    Send(ctx context.Context, msg Message) error
}
```

```go
// BAD — kitchen-sink interface
type EmailService interface {
    Send(ctx context.Context, msg Message) error
    SendBatch(ctx context.Context, msgs []Message) error
    Validate(addr string) error
    ListTemplates() ([]Template, error)
    RenderTemplate(id string, data any) (string, error)
    Subscribe(addr string) error
    Unsubscribe(addr string) error
}
```

If a consumer only needs `Send`, it should not depend on seven other methods.

---

## 4. Interface Segregation

When you must group capabilities, split them into focused interfaces.

```go
// GOOD — focused interfaces
type Reader interface {
    Read(ctx context.Context, id string) (*Record, error)
}

type Writer interface {
    Write(ctx context.Context, r *Record) error
}

type Deleter interface {
    Delete(ctx context.Context, id string) error
}

// Compose only when a consumer truly needs all three
type ReadWriter interface {
    Reader
    Writer
}
```

```go
// BAD — monolithic CRUD interface forced on every consumer
type Repository interface {
    Create(ctx context.Context, r *Record) error
    Read(ctx context.Context, id string) (*Record, error)
    Update(ctx context.Context, r *Record) error
    Delete(ctx context.Context, id string) error
    List(ctx context.Context, filter Filter) ([]*Record, error)
    Count(ctx context.Context, filter Filter) (int, error)
}
```

A handler that only reads should accept `Reader`, not `Repository`.

---

## 5. Implicit Satisfaction

Go interfaces are satisfied **structurally**. There is no `implements` keyword.

```go
type Stringer interface {
    String() string
}

type City struct{ Name string }

// City satisfies Stringer without declaring it.
func (c City) String() string { return c.Name }

func Print(s Stringer) { fmt.Println(s.String()) }

func main() {
    Print(City{Name: "Berlin"}) // works — no explicit declaration needed
}
```

Why this matters:
- A type in package A can satisfy an interface in package B **without importing B**.
- Consumer-side interfaces work because producers do not need to know about them.
- You can define an interface **after** the concrete type already exists.
- Third-party types can satisfy your interfaces without modification.

**Compile-time satisfaction check**: since there is no `implements` keyword, use a
blank variable declaration to verify a type satisfies an interface at compile time:

```go
// Fails to compile if *StripeClient does not implement PaymentCharger.
var _ PaymentCharger = (*StripeClient)(nil)
```

This is a zero-cost idiom (no runtime allocation) and is the standard way to catch
missing methods early, especially when the interface is defined in a different package.

---

## 6. Accept Interfaces, Return Structs

This proverb means: function **parameters** can be interfaces (to accept multiple types),
but **return types** should be concrete (to give callers full access).

```go
// GOOD — accepts interface, returns concrete
func CopyToFile(r io.Reader, path string) (*os.File, error) {
    f, err := os.Create(path)
    if err != nil {
        return nil, err
    }
    if _, err := io.Copy(f, r); err != nil {
        f.Close()
        return nil, err
    }
    return f, nil
}
```

```go
// BAD — returns interface, hides concrete type from caller
func NewStore(dsn string) (StoreInterface, error) {
    // Caller cannot access concrete methods, type-assert is fragile
}
```

**Nuance**: returning an interface is fine when the concrete type is truly private
or when the stdlib pattern demands it (e.g., `errors.New` returns `error`).
The rule is about defaults, not absolutes.

---

## 7. When You DO Need an Interface

### Testing boundaries
When you need to replace an external dependency (database, HTTP client, clock) in tests:

```go
// In your consuming package
type Clock interface {
    Now() time.Time
}

type realClock struct{}
func (realClock) Now() time.Time { return time.Now() }

// In tests
type fakeClock struct{ fixed time.Time }
func (c fakeClock) Now() time.Time { return c.fixed }
```

### Multiple real implementations
When two or more concrete types legitimately exist:

```go
type Notifier interface {
    Notify(ctx context.Context, msg string) error
}

type SlackNotifier struct{ /* ... */ }
type EmailNotifier struct{ /* ... */ }
type PagerDutyNotifier struct{ /* ... */ }
```

### Plugin / extension systems
When third-party code must provide implementations:

```go
type Driver interface {
    Open(name string) (Conn, error)
}
// database/sql uses this pattern for pluggable drivers
```

### Stdlib compatibility
When your type should work with `io.Reader`, `fmt.Stringer`, `sort.Interface`,
`encoding.BinaryMarshaler`, etc., you satisfy existing interfaces — you do not define new ones.

---

## 8. When You DON'T Need an Interface

- **Single implementation, no tests substituting it**: use the concrete type directly.
- **Internal package code**: if the type never crosses a package boundary that
  requires abstraction, skip the interface.
- **No substitution boundary**: if you cannot name two real types that would
  satisfy it, you do not need it yet.
- **"Future-proofing"**: Go interfaces can be introduced later without changing
  the implementing type. There is no cost to waiting.

```go
// BAD — interface for the sake of it
type Logger interface {
    Info(msg string)
    Error(msg string)
}

type logger struct{}           // the only implementation, ever
func (l *logger) Info(msg string)  { /* ... */ }
func (l *logger) Error(msg string) { /* ... */ }

func NewLogger() Logger { return &logger{} }
```

```go
// GOOD — just export the struct
type Logger struct{ /* ... */ }

func (l *Logger) Info(msg string)  { /* ... */ }
func (l *Logger) Error(msg string) { /* ... */ }

func NewLogger() *Logger { return &Logger{} }
```

---

## 9. Embedding Interfaces

Compose small interfaces into larger ones using embedding.

```go
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

type Closer interface {
    Close() error
}

// Composed interfaces
type ReadWriter interface {
    Reader
    Writer
}

type ReadWriteCloser interface {
    Reader
    Writer
    Closer
}
```

Rules of thumb:
- Compose **only** interfaces that a real consumer needs together.
- Do not create a `ReadWriteCloseSeekFlusher` that nobody asks for.
- Embedding also works in structs to provide default implementations:

```go
// Embed an interface in a struct for partial test fakes
type fakeStore struct {
    Reader                                    // embeds interface
    writeCalled bool
}

func (f *fakeStore) Write(ctx context.Context, r *Record) error {
    f.writeCalled = true
    return nil
}
```

> **Warning**: calling any method on an embedded interface that has not been
> explicitly implemented will panic at runtime with a nil pointer dereference.
> Only embed an interface in a struct when you are certain unimplemented methods
> will never be called (e.g., in focused test fakes).

---

## 10. The Empty Interface (`any`)

`any` (alias for `interface{}`) means "I accept anything." It has its places
and its abuses.

### Acceptable uses

```go
// Logging / structured fields — values are genuinely heterogeneous
func (l *Logger) Info(msg string, fields ...any)

// JSON / serialization boundaries
func json.Marshal(v any) ([]byte, error)

// fmt-style formatting
func fmt.Sprintf(format string, a ...any) string
```

### Unacceptable uses

```go
// BAD — avoiding design
func Process(data any) any {
    switch v := data.(type) {
    case string:  // ...
    case int:     // ...
    case []byte:  // ...
    }
    // This function has no contract. Callers must guess.
}
```

```go
// GOOD — use generics or specific types
// (Processable and Result are illustrative placeholders;
// define them as your own constraint and return type.)
func Process[T Processable](data T) Result {
    // Clear contract, compile-time safety
}
```

If you reach for `any`, ask: "Am I avoiding the work of defining what this
function actually accepts?" If yes, define the type or use a generic constraint.

---

## 11. Common Anti-Patterns

### Anti-pattern: Interface-first design (Java-style)

```go
// BAD — defining the interface before any implementation exists
type UserService interface {
    Create(ctx context.Context, u *User) error
    Get(ctx context.Context, id string) (*User, error)
    Update(ctx context.Context, u *User) error
    Delete(ctx context.Context, id string) error
}

type userServiceImpl struct{}  // the only implementation
```

**Fix**: write `UserService` as a struct. Extract an interface later if needed.

### Anti-pattern: Giant "service" interfaces

```go
// BAD — 10+ methods, no consumer uses all of them
type OrderManager interface {
    Create(ctx context.Context, o *Order) error
    Get(ctx context.Context, id string) (*Order, error)
    Update(ctx context.Context, o *Order) error
    Cancel(ctx context.Context, id string) error
    List(ctx context.Context, f Filter) ([]*Order, error)
    AddItem(ctx context.Context, orderID string, item Item) error
    RemoveItem(ctx context.Context, orderID, itemID string) error
    ApplyDiscount(ctx context.Context, orderID string, code string) error
    CalculateTotal(ctx context.Context, orderID string) (Money, error)
    Ship(ctx context.Context, orderID string) error
    Refund(ctx context.Context, orderID string) error
}
```

**Fix**: each consumer defines only the methods it needs.

```go
// In the shipping package
type OrderGetter interface {
    Get(ctx context.Context, id string) (*Order, error)
}

// In the billing package
type Refunder interface {
    Refund(ctx context.Context, orderID string) error
}
```

### Anti-pattern: Producer-exported interfaces

```go
// BAD — package user exports an interface it implements
package user

type Service interface { /* ... */ }
type serviceImpl struct{}
func New() Service { return &serviceImpl{} }
```

**Fix**: export the concrete type. Let consumers define their own interfaces.

```go
package user

type Service struct{ /* ... */ }
func New() *Service { return &Service{} }
```

### Anti-pattern: "Just in case" interfaces

```go
// BAD — wrapping every struct in an interface preemptively
type ConfigLoader interface { Load() (*Config, error) }
type configLoader struct{}

// There will never be another implementation.
```

**Fix**: `ConfigLoader` should be a struct. Go's implicit satisfaction means
you can introduce an interface later at zero cost to existing code.

### Anti-pattern: `interface{}` to avoid thinking about types

```go
// BAD
func Store(key string, value interface{}) { /* ... */ }

// Caller has no idea what types are valid. Runtime panics await.
```

**Fix**: use a concrete type, a defined interface, or generics.

```go
// GOOD — generic with constraint
func Store[V Storable](key string, value V) { /* ... */ }
```

---

## Quick Decision Checklist

1. Do I have (or foresee) **two or more real implementations**? → interface may help.
2. Do I need to **substitute in tests**? → consumer-side interface at the test boundary.
3. Is the interface **one to three methods**? → good size. More than five? Split it.
4. Am I defining this where it is **consumed**? → correct. Where it is implemented? → move it.
5. Is there only **one implementation** and no test substitution need? → use a concrete type.
6. Can I introduce this interface **later** without breaking callers? → yes, so wait.
