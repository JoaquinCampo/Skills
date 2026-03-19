# Go Testing Reference

## Table-Driven Tests

The canonical Go testing pattern. Use when testing a function with multiple input/output combinations. Skip when a single case is enough or when setup dominates the test body.

```go
func TestParseSize(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    int64
		wantErr bool
	}{
		{name: "bytes", input: "100B", want: 100},
		{name: "kilobytes", input: "2KB", want: 2048},
		{name: "empty string", input: "", wantErr: true},
		{name: "negative", input: "-5B", wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ParseSize(tt.input)
			if tt.wantErr {
				if err == nil {
					t.Fatal("expected error, got nil")
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got != tt.want {
				t.Errorf("ParseSize(%q) = %d, want %d", tt.input, got, tt.want)
			}
		})
	}
}
```

When a simple test is fine — don't force a table when there's one case:

```go
func TestNewClient_defaults(t *testing.T) {
	c := NewClient()
	if c.Timeout != 30*time.Second {
		t.Errorf("default timeout = %v, want 30s", c.Timeout)
	}
}
```

## Test Naming Conventions

Pattern: `TestUnit_Scenario_ExpectedBehavior`. Subtests use human-readable names.

```go
func TestCache_Get_returnsStoredValue(t *testing.T) { ... }
func TestCache_Get_missReturnsError(t *testing.T) { ... }
func TestCache_Eviction_removesOldest(t *testing.T) { ... }
```

For table-driven subtests, use descriptive names that read well in output:

```go
// Good: --- FAIL: TestParse/negative_number
t.Run("negative number", func(t *testing.T) { ... })

// Bad: --- FAIL: TestParse/test_case_3
t.Run(fmt.Sprintf("test_case_%d", i), func(t *testing.T) { ... })
```

## testify/require vs stdlib

> **House opinion:** Recommending testify is a team preference. Canonical Go uses only the stdlib `testing` package. Many Go projects avoid third-party test dependencies entirely.

Use `testify/require` when it improves readability — deep equality, JSON comparison, error wrapping checks. Use stdlib when the assertion is trivial. Never build a custom test DSL.

```go
// testify adds value: deep struct comparison
require.Equal(t, expectedUser, gotUser)

// testify adds value: error type checking
require.ErrorIs(t, err, ErrNotFound)

// stdlib is fine: simple boolean or string check
if got != "hello" {
	t.Errorf("got %q, want %q", got, "hello")
}
```

Use `require` (not `assert`) when failure should stop the test — a nil-check before dereferencing:

```go
// Good: stops test on failure, prevents nil panic below
require.NoError(t, err)
require.NotNil(t, resp)
_ = resp.Body // safe

// Bad: assert continues, next line panics
assert.NoError(t, err)
assert.NotNil(t, resp)
_ = resp.Body // panic if resp is nil
```

## httptest

Use `httptest.NewServer` for integration-style tests. Use `httptest.NewRecorder` for unit-testing handlers directly.

### Testing a handler

```go
func TestHealthHandler(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()

	HealthHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", rec.Code, http.StatusOK)
	}
	if body := rec.Body.String(); body != `{"status":"ok"}` {
		t.Errorf("body = %s", body)
	}
}
```

### Testing middleware

```go
func TestAuthMiddleware_rejectsMissingToken(t *testing.T) {
	inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Fatal("handler should not be called")
	})

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rec := httptest.NewRecorder()

	AuthMiddleware(inner).ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", rec.Code)
	}
}
```

### Testing an HTTP client with a fake server

```go
func TestClient_FetchUser(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/users/42" {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, `{"id":42,"name":"Alice"}`)
	}))
	defer srv.Close()

	client := NewAPIClient(srv.URL)
	user, err := client.FetchUser(42)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if user.Name != "Alice" {
		t.Errorf("name = %q, want Alice", user.Name)
	}
}
```

## Testing with Interfaces

Inject interfaces at boundaries where the real dependency is expensive or external (network, disk, third-party API). Do not create interfaces for everything.

```go
// Good: interface at the boundary
type OrderStore interface {
	Save(ctx context.Context, order Order) error
	FindByID(ctx context.Context, id string) (Order, error)
}

type OrderService struct {
	store OrderStore
}

// Bad: interface for a pure function or value type
type StringFormatter interface {
	Format(s string) string
}
```

Rule of thumb: if the concrete type lives in the same package and has no I/O, pass it directly.

## Mocking Strategy

**When to mock:** external services (HTTP APIs, databases, message queues), time, filesystem in certain cases.

**When NOT to mock:** pure functions, your own structs, simple in-memory code.

### Prefer hand-written fakes over mocking libraries

```go
// Fake implementation — simple, readable, no library needed
type fakeStore struct {
	orders map[string]Order
}

func (f *fakeStore) Save(_ context.Context, o Order) error {
	f.orders[o.ID] = o
	return nil
}

func (f *fakeStore) FindByID(_ context.Context, id string) (Order, error) {
	o, ok := f.orders[id]
	if !ok {
		return Order{}, ErrNotFound
	}
	return o, nil
}

func TestOrderService_PlaceOrder(t *testing.T) {
	store := &fakeStore{orders: make(map[string]Order)}
	svc := NewOrderService(store)

	err := svc.PlaceOrder(context.Background(), Order{ID: "1", Item: "widget"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	got, err := store.FindByID(context.Background(), "1")
	if err != nil {
		t.Fatalf("order not found: %v", err)
	}
	if got.Item != "widget" {
		t.Errorf("item = %q, want widget", got.Item)
	}
}
```

Use a mocking library (`gomock`, `mockery`) only when the interface is large and you only care about specific calls. Even then, consider if the interface is too big.

## Race Detection

Always run `go test -race` in CI. Use it locally when working on concurrent code.

```bash
go test -race ./...
```

Write tests that exercise concurrent paths:

```go
func TestCounter_concurrent(t *testing.T) {
	c := NewCounter()
	var wg sync.WaitGroup

	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			c.Inc()
		}()
	}
	wg.Wait()

	if got := c.Value(); got != 100 {
		t.Errorf("counter = %d, want 100", got)
	}
}
```

The race detector adds overhead. It is not a substitute for thoughtful design, but it catches real bugs that are invisible to normal tests.

## Benchmarks

Use `testing.B` for performance-sensitive code. Don't benchmark everything — benchmark what matters.

```go
// Requires Go 1.24+; for older versions use `for i := 0; i < b.N; i++`
func BenchmarkParseSize(b *testing.B) {
	for b.Loop() {
		ParseSize("256KB")
	}
}
```

For benchmarks that allocate, report allocations:

```go
var benchSink []byte // package-level sink to prevent dead-code elimination

func BenchmarkEncodeJSON(b *testing.B) {
	data := makeLargePayload()
	b.ResetTimer()
	b.ReportAllocs()
	for b.Loop() {
		out, err := json.Marshal(data)
		if err != nil {
			b.Fatal(err)
		}
		benchSink = out
	}
}
```

Running and reading results:

```bash
go test -bench=BenchmarkParseSize -benchmem ./...
# BenchmarkParseSize-8    5000000    234 ns/op    48 B/op    2 allocs/op
```

Compare before/after with `benchstat`:

```bash
go test -bench=. -count=10 ./... > old.txt
# make changes
go test -bench=. -count=10 ./... > new.txt
benchstat old.txt new.txt
```

## Test Helpers and t.Helper()

Extract repeated setup into helpers. Always call `t.Helper()` so failures report the caller's line.

```go
func newTestDB(t *testing.T) *sql.DB {
	t.Helper()
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return db
}

func TestUserRepo_Create(t *testing.T) {
	db := newTestDB(t)
	repo := NewUserRepo(db)
	// ...
}
```

Use `t.Cleanup` instead of `defer` in helpers — cleanup runs after the test that registered it, even for subtests.

### t.Setenv (Go 1.17+)

Use `t.Setenv` to set environment variables scoped to a single test. It automatically restores the original value when the test finishes. Cannot be used in parallel tests.

```go
func TestConfigFromEnv(t *testing.T) {
	t.Setenv("APP_PORT", "9090")
	cfg := LoadConfig()
	if cfg.Port != 9090 {
		t.Errorf("port = %d, want 9090", cfg.Port)
	}
}
```

### Custom assertion helper

```go
func requireJSONEqual(t *testing.T, want, got string) {
	t.Helper()
	var wantV, gotV any
	if err := json.Unmarshal([]byte(want), &wantV); err != nil {
		t.Fatalf("bad want JSON: %v", err)
	}
	if err := json.Unmarshal([]byte(got), &gotV); err != nil {
		t.Fatalf("bad got JSON: %v", err)
	}
	if !reflect.DeepEqual(wantV, gotV) {
		t.Errorf("JSON mismatch:\n  want: %s\n  got:  %s", want, got)
	}
}
```

## t.Parallel()

Call `t.Parallel()` at the start of a test or subtest to allow it to run concurrently with other parallel tests. This speeds up suites with many I/O-bound or sleep-heavy tests.

```go
func TestFetchAll(t *testing.T) {
	t.Parallel() // top-level test opts in

	tests := []struct {
		name string
		url  string
	}{
		{name: "users", url: "/users"},
		{name: "orders", url: "/orders"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel() // subtest also opts in
			resp := fetch(tt.url)
			if resp.StatusCode != 200 {
				t.Errorf("status = %d", resp.StatusCode)
			}
		})
	}
}
```

**Closure-capture gotcha (pre-Go 1.22):** Before Go 1.22, the loop variable `tt` was shared across iterations. If a subtest captured `tt` by reference without re-declaring it, all goroutines would see the last value. The fix was to shadow the variable:

```go
// Required before Go 1.22 — shadow the loop variable
for _, tt := range tests {
	tt := tt // <- capture current value
	t.Run(tt.name, func(t *testing.T) {
		t.Parallel()
		// use tt safely
	})
}
```

Starting with Go 1.22, each loop iteration gets its own variable, so the re-declaration is unnecessary. However, if your module targets Go <1.22, always add the shadow line.

**When NOT to use `t.Parallel()`:**
- Tests that mutate shared package-level state.
- Tests that use `t.Setenv` (panics if combined with `t.Parallel()`).
- Tests where ordering or isolation matters more than speed.

## Integration Tests with Build Tags

Separate slow/external tests with build tags so `go test ./...` stays fast.

```go
//go:build integration

package store_test

import (
	"database/sql"
	"os"
	"testing"
)

func TestPostgresStore_RoundTrip(t *testing.T) {
	dsn := os.Getenv("TEST_DATABASE_URL")
	if dsn == "" {
		t.Skip("TEST_DATABASE_URL not set")
	}
	db, err := sql.Open("postgres", dsn)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	defer db.Close()
	// ... test real database operations
}
```

Run them explicitly:

```bash
go test -tags=integration ./...
```

In CI, run unit tests on every push, integration tests on merge or nightly.

## TestMain

Use `TestMain` for package-level setup/teardown. Common uses: start a test database, seed data, set environment.

```go
func TestMain(m *testing.M) {
	// Setup
	pool, err := startTestPostgres()
	if err != nil {
		log.Fatalf("start postgres: %v", err)
	}

	code := m.Run()

	// Teardown
	pool.Purge()
	os.Exit(code)
}
```

Rules for `TestMain`:
- Must call `os.Exit(m.Run())` or tests won't report properly.
- Keep setup minimal. If only some tests need the resource, use a helper instead.
- Don't use `TestMain` to set global state that makes tests order-dependent.

## Common Anti-Patterns

### Mock-heavy tests for simple code

```go
// Bad: mocking a formatter to test a greeting
type MockFormatter struct{ mock.Mock }
func (m *MockFormatter) Format(s string) string { ... }

func TestGreet(t *testing.T) {
	f := new(MockFormatter)
	f.On("Format", "Alice").Return("ALICE")
	result := Greet(f, "Alice")
	f.AssertExpectations(t)
	// ... 15 more lines of mock setup for a 3-line function
}

// Good: just call the function
func TestGreet(t *testing.T) {
	got := Greet(strings.ToUpper, "Alice")
	if got != "Hello, ALICE!" {
		t.Errorf("got %q", got)
	}
}
```

### Asserting private implementation details

```go
// Bad: testing that an internal cache map has a specific key
if _, ok := svc.cache["user:42"]; !ok {
	t.Error("cache miss")
}

// Good: test the observable behavior
user, err := svc.GetUser(ctx, 42) // first call populates cache
require.NoError(t, err)

user2, err := svc.GetUser(ctx, 42) // second call should also work
require.NoError(t, err)
require.Equal(t, user, user2)
```

### Giant shared test harnesses

```go
// Bad: every test uses a 200-line setupEverything() that starts
// a database, message queue, cache, and three services
func TestUserCreate(t *testing.T) {
	env := setupEverything(t) // slow, fragile, hard to understand
	env.svc.CreateUser(...)
}

// Good: each test sets up only what it needs
func TestUserCreate(t *testing.T) {
	store := &fakeStore{users: map[string]User{}}
	svc := NewUserService(store)
	err := svc.CreateUser(ctx, User{Name: "Alice"})
	require.NoError(t, err)
}
```

### Tests that depend on execution order

```go
// Bad: TestA creates data that TestB reads
func TestA_CreateUser(t *testing.T) {
	globalDB.Insert(User{ID: 1})
}
func TestB_GetUser(t *testing.T) {
	u, _ := globalDB.Get(1) // fails if TestA didn't run first
}

// Good: each test is self-contained
func TestGetUser(t *testing.T) {
	db := newTestDB(t)
	db.Insert(User{ID: 1, Name: "Alice"})

	got, err := db.Get(1)
	require.NoError(t, err)
	require.Equal(t, "Alice", got.Name)
}
```

Go tests within a package run sequentially by default, but `go test` does not guarantee package-level ordering and `-shuffle` will break order-dependent tests. Each test must stand alone.
