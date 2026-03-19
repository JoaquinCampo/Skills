# Go Generics Reference

## The "Concrete First" Rule

Always write the concrete version first. Generalize only when you have two or more
callers that share the same shape. If the generic version is harder to explain than
the concrete version, keep the concrete version.

```go
// GOOD: You have a concrete function that works.
func SumInts(nums []int) int {
    var total int
    for _, n := range nums {
        total += n
    }
    return total
}

// Later you discover you also need SumFloat64s with identical logic.
// NOW generalize:
func Sum[T int | int64 | float64](nums []T) T {
    var total T
    for _, n := range nums {
        total += n
    }
    return total
}
```

Do not start with the generic version. Earn it through real duplication.

---

## Good Uses of Generics

### Reusable containers

```go
// Generic Set
type Set[T comparable] map[T]struct{}

func NewSet[T comparable](items ...T) Set[T] {
    s := make(Set[T], len(items))
    for _, item := range items {
        s[item] = struct{}{}
    }
    return s
}

func (s Set[T]) Add(item T)           { s[item] = struct{}{} }
func (s Set[T]) Contains(item T) bool { _, ok := s[item]; return ok }
func (s Set[T]) Remove(item T)        { delete(s, item) }
```

### Algorithms: Min, Max, Contains

> **Note (Go 1.21+):** The stdlib now provides `min()` and `max()` as builtins,
> plus `slices.Contains`, `slices.SortFunc`, and `maps.Keys`. Do not rewrite
> these — use the stdlib versions. The examples below are illustrative only.

```go
func Min[T cmp.Ordered](a, b T) T {
    if a < b {
        return a
    }
    return b
}

func Contains[T comparable](slice []T, target T) bool {
    for _, v := range slice {
        if v == target {
            return true
        }
    }
    return false
}
```

### Result type

> **House opinion:** `Result[T]` is uncommon in Go. The established idiom for fallibility is the `(T, error)` return pattern. This generic wrapper is illustrative but not widely adopted.

```go
type Result[T any] struct {
    Value T
    Err   error
}

func Ok[T any](v T) Result[T]       { return Result[T]{Value: v} }
func Fail[T any](err error) Result[T] { return Result[T]{Err: err} }

func (r Result[T]) Unwrap() (T, error) { return r.Value, r.Err }
```

---

## Bad Uses of Generics

### Generic business logic with one caller

```go
// BAD: Only ever called with *Order. No second type exists.
func ProcessEntity[T Processable](e T) error {
    // ... 50 lines of order-specific logic
}

// GOOD: Just use *Order directly.
func ProcessOrder(o *Order) error { ... }
```

### Generic wrappers that obscure behavior

```go
// BAD: A generic "DoWith" that wraps a function for no reason.
func DoWith[T any](val T, fn func(T) error) error {
    return fn(val)
}

// This adds a layer of indirection with zero value. Call fn(val) directly.
```

### Premature framework-building

```go
// BAD: Building a generic repository when you have one entity.
type Repository[T any, ID comparable] interface {
    Get(id ID) (T, error)
    Save(entity T) error
    Delete(id ID) error
}

// GOOD: Write a concrete UserRepository. Add generics later if you
// genuinely have 5+ repositories with identical CRUD patterns.
```

---

## Type Constraints

### Built-in constraints

| Constraint   | Meaning                                    |
|--------------|--------------------------------------------|
| `any`        | No restriction (alias for `interface{}`)   |
| `comparable` | Supports `==` and `!=`; usable as map keys |

### The `cmp` and `constraints` packages

```go
import "cmp"

// cmp.Ordered covers all int, uint, float, and string types.
func Clamp[T cmp.Ordered](val, lo, hi T) T {
    return max(lo, min(val, hi))
}
```

### Custom constraints

```go
type Number interface {
    ~int | ~int8 | ~int16 | ~int32 | ~int64 |
    ~float32 | ~float64
}

func Sum[T Number](nums []T) T {
    var total T
    for _, n := range nums {
        total += n
    }
    return total
}
```

---

## Type Inference

Go can infer type parameters when arguments provide enough information.

```go
// Inference works — type is deduced from the argument.
result := Min(3, 7)          // T inferred as int
names := Contains(ss, "bob") // T inferred as string

// Inference fails — no argument carries the type. You must specify.
func Zero[T any]() T { var zero T; return zero }
v := Zero[int]()
```

Rule of thumb: if every type parameter appears in at least one function argument,
inference will work. If a type parameter appears only in the return type, you must
provide it explicitly.

---

## Generic Functions vs Generic Types

> **Key restriction:** Go does not allow type parameters on individual methods,
> only on the type itself. If you need a method parameterized by a new type,
> make it a top-level generic function instead.

### Use generic functions for stateless operations

> **House opinion:** `Map`, `Filter`, and `Reduce` are illustrative of generic functions, but the Go community has not widely adopted functional-style slice operations. The stdlib `slices` package favors callback-variant patterns like `slices.SortFunc` and `slices.ContainsFunc` instead.

```go
func Map[T, U any](s []T, f func(T) U) []U {
    out := make([]U, len(s))
    for i, v := range s {
        out[i] = f(v)
    }
    return out
}

func Filter[T any](s []T, pred func(T) bool) []T {
    var out []T
    for _, v := range s {
        if pred(v) {
            out = append(out, v)
        }
    }
    return out
}

func Reduce[T, U any](s []T, init U, f func(U, T) U) U {
    acc := init
    for _, v := range s {
        acc = f(acc, v)
    }
    return acc
}
```

### Use generic types when state is parameterized

```go
type Cache[K comparable, V any] struct {
    mu    sync.RWMutex
    items map[K]V
}

func NewCache[K comparable, V any]() *Cache[K, V] {
    return &Cache[K, V]{items: make(map[K]V)}
}

func (c *Cache[K, V]) Get(key K) (V, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    v, ok := c.items[key]
    return v, ok
}

func (c *Cache[K, V]) Set(key K, val V) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.items[key] = val
}
```

---

## Interface Constraints with Methods

Define behavior constraints when you need to call methods on the type parameter.

```go
type Stringer interface {
    String() string
}

func JoinStrings[T Stringer](items []T, sep string) string {
    parts := make([]string, len(items))
    for i, item := range items {
        parts[i] = item.String()
    }
    return strings.Join(parts, sep)
}

// Combine method constraints with type constraints.
// NOTE: OrderedStringer is illustrative — no stdlib type satisfies both
// cmp.Ordered and String() simultaneously. Use it as a pattern template.
type OrderedStringer interface {
    cmp.Ordered
    String() string
}
```

---

## The `~` Underlying Type Constraint

The `~` prefix matches any type whose underlying type is the specified type.
Without `~`, only the exact named type matches.

```go
type Celsius float64
type Fahrenheit float64

// Without ~: Celsius and Fahrenheit would NOT satisfy `float64`.
// With ~: any type whose underlying type is float64 is accepted.
type Temperature interface {
    ~float64
}

func Average[T Temperature](temps []T) T {
    var sum T
    for _, t := range temps {
        sum += t
    }
    return sum / T(len(temps))
}

// Both work:
var c []Celsius
var f []Fahrenheit
_ = Average(c)
_ = Average(f)
```

Use `~` when your constraint should accept user-defined types built on primitives.
This is almost always what you want for numeric and string constraints.

---

## Common Patterns

### Generic Optional

> **House opinion:** `Optional[T]` is uncommon in Go. The established idioms for optionality are `*T` (nil means absent) or `(T, bool)` returns. This pattern is illustrative but not widely adopted.

```go
type Optional[T any] struct {
    value T
    valid bool
}

func Some[T any](v T) Optional[T] { return Optional[T]{value: v, valid: true} }
func None[T any]() Optional[T]    { return Optional[T]{} }

func (o Optional[T]) Get() (T, bool)  { return o.value, o.valid }
func (o Optional[T]) OrElse(def T) T {
    if o.valid {
        return o.value
    }
    return def
}
```

---

## Anti-Patterns with Corrections

### Using `any` when a concrete type works

```go
// BAD: Loses type safety for no reason.
func PrintAll(items []any) {
    for _, item := range items {
        fmt.Println(item)
    }
}

// GOOD: If you always pass strings, say so.
func PrintAll(items []string) {
    for _, item := range items {
        fmt.Println(item)
    }
}

// ALSO GOOD: If you truly need multiple types, use a constraint.
func PrintAll[T fmt.Stringer](items []T) {
    for _, item := range items {
        fmt.Println(item.String())
    }
}
```

### Generic function with only one instantiation

```go
// BAD: Only ever called with string. The generic adds nothing.
func Wrap[T any](v T) *T { return &v }
// Every call site: Wrap("hello")

// GOOD: Just write the concrete helper.
func WrapString(v string) *string { return &v }
```

### Over-constrained type parameters

```go
// BAD: The constraint is tighter than what the body actually uses.
func First[T cmp.Ordered](s []T) T { return s[0] }

// GOOD: The body only indexes — any is sufficient.
func First[T any](s []T) T { return s[0] }
```

### Generics that make error messages unreadable

```go
// BAD: Deeply nested generic types that produce cryptic compiler errors.
type Store[K comparable, V Validator[K, V]] interface {
    Get(K) Result[V, StoreError[K]]
}

// GOOD: Flatten. Use concrete error types. Keep type param depth <= 2.
type Store[K comparable, V any] interface {
    Get(K) (V, error)
}
```

---

## Summary Checklist

1. Can you solve it without generics? Do that first.
2. Do you have 2+ concrete implementations with the same shape? Now consider generics.
3. Is the generic version as easy to read as the concrete? Ship it.
4. Is the generic version harder to explain? Keep the concrete version.
5. Use `~` in constraints when accepting named types over primitives.
6. Keep type parameter nesting shallow (depth <= 2).
7. Match constraint strictness to what the function body actually requires.
