# Go HTTP Handlers & Servers — Reference

## 1. Handler Structure

Every handler follows the same five-step rhythm: **decode → validate → call → encode → error-map**.
Keep the transport layer boring. No business logic lives here.

```go
func handleCreateOrder(svc OrderService) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        // 1. Decode input
        var req CreateOrderRequest
        if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
            respondError(w, http.StatusBadRequest, "invalid JSON body")
            return
        }

        // 2. Validate at the boundary
        if err := req.Validate(); err != nil {
            respondError(w, http.StatusUnprocessableEntity, err.Error())
            return
        }

        // 3. Call domain logic (the handler owns ZERO business rules)
        order, err := svc.Create(r.Context(), req)
        if err != nil {
            mapError(w, err) // 5. Map domain errors → HTTP codes
            return
        }

        // 4. Encode output
        respondJSON(w, http.StatusCreated, order)
    }
}
```

Anti-pattern — handler doing everything:

```go
// BAD: handler contains SQL, retries, email sending, validation rules
func handleCreateOrder(w http.ResponseWriter, r *http.Request) {
    var req CreateOrderRequest
    json.NewDecoder(r.Body).Decode(&req)
    db.Exec("INSERT INTO orders ...")  // direct SQL
    if tries < 3 { /* retry logic */ } // hidden retries
    smtp.Send(...)                     // orchestrating half the system
}
```

---

## 2. http.HandlerFunc vs http.Handler

```go
// http.Handler — an interface. Use when the handler carries dependencies or state.
type Handler interface {
    ServeHTTP(http.ResponseWriter, *http.Request)
}

// http.HandlerFunc — a function type that satisfies http.Handler.
// Prefer for most handlers via the closure-over-dependencies pattern.
type HandlerFunc func(http.ResponseWriter, *http.Request)
```

Closure adapter (preferred pattern):

```go
// Returns http.HandlerFunc, captures dependencies via closure.
func handleGetUser(repo UserRepo, log *slog.Logger) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        // repo and log are available here
    }
}
```

Struct adapter (use when handler has many deps or needs setup):

```go
type OrderHandler struct {
    svc    OrderService
    logger *slog.Logger
}

func (h *OrderHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
    // ...
}

// Register: mux.Handle("POST /orders", &OrderHandler{svc: svc, logger: log})
```

---

## 3. Request Decoding

### JSON Body

Limit the body size with `http.MaxBytesReader` before decoding to prevent
clients from sending arbitrarily large payloads:

```go
func decodeJSON[T any](w http.ResponseWriter, r *http.Request, maxBytes int64) (T, error) {
    var v T
    // Cap body size — returns 413 Request Entity Too Large on overflow.
    r.Body = http.MaxBytesReader(w, r.Body, maxBytes)
    dec := json.NewDecoder(r.Body)
    dec.DisallowUnknownFields() // reject unexpected keys
    if err := dec.Decode(&v); err != nil {
        return v, fmt.Errorf("decode json: %w", err)
    }
    return v, nil
}
```

### Path Parameters (Go 1.22+)

```go
mux.HandleFunc("GET /users/{id}", func(w http.ResponseWriter, r *http.Request) {
    id := r.PathValue("id")
    // ...
})
```

### Query Parameters

```go
func paginationFromQuery(r *http.Request) (limit, offset int) {
    limit, _ = strconv.Atoi(r.URL.Query().Get("limit"))
    offset, _ = strconv.Atoi(r.URL.Query().Get("offset"))
    if limit <= 0 || limit > 100 {
        limit = 20
    }
    return limit, offset
}
```

### Headers

```go
token := r.Header.Get("Authorization")
contentType := r.Header.Get("Content-Type")
requestID := r.Header.Get("X-Request-ID")
```

---

## 4. Response Encoding

```go
func respondJSON(w http.ResponseWriter, status int, data any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(status)
    if data != nil {
        // Encode error means the client likely disconnected; log and move on.
        // We cannot change the status code — headers are already sent.
        if err := json.NewEncoder(w).Encode(data); err != nil {
            slog.Warn("respondJSON: failed to encode response", "error", err)
        }
    }
}

// Consistent error envelope — every error from every endpoint looks the same.
type ErrorResponse struct {
    Error   string `json:"error"`
    Code    string `json:"code,omitempty"`
    TraceID string `json:"trace_id,omitempty"`
}

func respondError(w http.ResponseWriter, status int, msg string) {
    respondJSON(w, status, ErrorResponse{Error: msg})
}
```

---

## 5. Middleware Patterns

The canonical shape: `func(http.Handler) http.Handler`.

### Chaining

```go
// Apply from outermost to innermost.
handler := recoveryMiddleware(
    requestIDMiddleware(
        loggingMiddleware(
            router,
        ),
    ),
)
```

Or build a helper:

```go
func chain(h http.Handler, mw ...func(http.Handler) http.Handler) http.Handler {
    for i := len(mw) - 1; i >= 0; i-- {
        h = mw[i](h)
    }
    return h
}

handler := chain(router, recoveryMiddleware, requestIDMiddleware, loggingMiddleware)
```

### Logging Middleware

```go
func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        sw := &statusWriter{ResponseWriter: w, status: http.StatusOK}

        next.ServeHTTP(sw, r)

        slog.Info("request",
            "method", r.Method,
            "path", r.URL.Path,
            "status", sw.status,
            "duration", time.Since(start),
        )
    })
}

type statusWriter struct {
    http.ResponseWriter
    status int
}

func (w *statusWriter) WriteHeader(code int) {
    w.status = code
    w.ResponseWriter.WriteHeader(code)
}
```

### Recovery Middleware

```go
func recoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if err := recover(); err != nil {
                slog.Error("panic recovered", "error", err, "stack", string(debug.Stack()))
                respondError(w, http.StatusInternalServerError, "internal error")
            }
        }()
        next.ServeHTTP(w, r)
    })
}
```

### Request ID Middleware

```go
func requestIDMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        id := r.Header.Get("X-Request-ID")
        if id == "" {
            id = uuid.NewString()
        }
        ctx := context.WithValue(r.Context(), requestIDKey, id)
        w.Header().Set("X-Request-ID", id)
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}
```

### Auth Middleware

```go
func authMiddleware(verifier TokenVerifier) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            token := strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")
            claims, err := verifier.Verify(r.Context(), token)
            if err != nil {
                respondError(w, http.StatusUnauthorized, "invalid token")
                return
            }
            ctx := context.WithValue(r.Context(), userClaimsKey, claims)
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}
```

---

## 6. Error Handling in Handlers

Map domain errors to HTTP status codes in one place.

```go
// Domain errors (defined in your domain package, NOT in the handler).
var (
    ErrNotFound     = errors.New("not found")
    ErrConflict     = errors.New("conflict")
    ErrUnauthorized = errors.New("unauthorized")
    ErrForbidden    = errors.New("forbidden")
)

// mapError translates domain errors to HTTP responses.
func mapError(w http.ResponseWriter, err error) {
    switch {
    case errors.Is(err, ErrNotFound):
        respondError(w, http.StatusNotFound, err.Error())
    case errors.Is(err, ErrConflict):
        respondError(w, http.StatusConflict, err.Error())
    case errors.Is(err, ErrUnauthorized):
        respondError(w, http.StatusUnauthorized, err.Error())
    case errors.Is(err, ErrForbidden):
        respondError(w, http.StatusForbidden, err.Error())
    default:
        slog.Error("unhandled error", "error", err)
        respondError(w, http.StatusInternalServerError, "internal error")
    }
}
```

For richer errors, one approach is a custom type with domain-level error kinds
(not raw HTTP status codes — that couples domain to transport):

> **House opinion:** The `ErrorKind` enum below is one reasonable approach, not the only or canonical way. Simpler alternatives -- direct error type switches with `errors.Is`/`errors.As` (shown above), or sentinel errors -- are equally valid and often sufficient.

```go
// ErrorKind represents a domain-level error category.
// The HTTP layer translates these to status codes; the domain never knows about HTTP.
type ErrorKind int

const (
    KindNotFound     ErrorKind = iota // resource does not exist
    KindConflict                      // duplicate or state conflict
    KindUnauthorized                  // missing or invalid credentials
    KindForbidden                     // authenticated but not allowed
    KindValidation                    // input failed validation
    KindInternal                      // unexpected failure
)

type DomainError struct {
    Code    string    // machine-readable, e.g. "order.already_shipped"
    Message string    // human-readable
    Kind    ErrorKind // domain category — NOT an HTTP status code
}

func (e *DomainError) Error() string { return e.Message }

// httpStatus lives in the transport layer, translating domain kinds to HTTP.
func httpStatus(k ErrorKind) int {
    switch k {
    case KindNotFound:
        return http.StatusNotFound
    case KindConflict:
        return http.StatusConflict
    case KindUnauthorized:
        return http.StatusUnauthorized
    case KindForbidden:
        return http.StatusForbidden
    case KindValidation:
        return http.StatusUnprocessableEntity
    default:
        return http.StatusInternalServerError
    }
}
```

---

## 7. Server Configuration

Always set timeouts. A naked `http.ListenAndServe` is a production incident waiting to happen.

```go
srv := &http.Server{
    Addr:              ":8080",
    Handler:           handler,
    ReadTimeout:       5 * time.Second,
    ReadHeaderTimeout: 2 * time.Second,  // mitigates slowloris attacks
    WriteTimeout:      10 * time.Second,
    IdleTimeout:       120 * time.Second,
}
```

### Graceful Shutdown

```go
func run(ctx context.Context, handler http.Handler) error {
    srv := &http.Server{
        Addr:              ":8080",
        Handler:           handler,
        ReadTimeout:       5 * time.Second,
        ReadHeaderTimeout: 2 * time.Second,
        WriteTimeout:      10 * time.Second,
        IdleTimeout:       120 * time.Second,
    }

    // Start server in a goroutine.
    errCh := make(chan error, 1)
    go func() { errCh <- srv.ListenAndServe() }()

    // Wait for interrupt or server error.
    select {
    case err := <-errCh:
        // ErrServerClosed is returned on normal Shutdown; not an error.
        if !errors.Is(err, http.ErrServerClosed) {
            return err
        }
        return nil
    case <-ctx.Done():
        // Give in-flight requests time to finish.
        shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
        defer cancel()
        return srv.Shutdown(shutdownCtx)
    }
}
```

---

## 8. Routing

### Stdlib Mux (Go 1.22+)

Go 1.22 added method + path-parameter matching. This is enough for most services.

```go
mux := http.NewServeMux()

mux.HandleFunc("GET /users/{id}", handleGetUser(repo))
mux.HandleFunc("POST /users", handleCreateUser(repo))
mux.HandleFunc("DELETE /users/{id}", handleDeleteUser(repo))
mux.HandleFunc("GET /health", handleHealth)

// Wildcard catch-all:
mux.HandleFunc("GET /files/{path...}", handleFiles)
```

### When chi/gorilla Earns Its Cost

Reach for `chi` or similar when you need:
- Route groups with per-group middleware (e.g., `/admin` routes get extra auth).
- URL parameter regex constraints (`{id:[0-9]+}`).
- Mount sub-routers from different packages cleanly.

If you only need basic param routing, the stdlib is enough. Do not import a router "just in case."

```go
// chi example — only if the above needs apply.
r := chi.NewRouter()
r.Use(loggingMiddleware, recoveryMiddleware)

r.Route("/admin", func(r chi.Router) {
    r.Use(adminAuthMiddleware)
    r.Get("/dashboard", handleDashboard)
})
```

---

## 9. Testing with httptest

### Testing a Handler

```go
func TestHandleGetUser(t *testing.T) {
    repo := &stubUserRepo{user: User{ID: "1", Name: "Alice"}}
    handler := handleGetUser(repo)

    req := httptest.NewRequest(http.MethodGet, "/users/1", nil)
    req.SetPathValue("id", "1") // Go 1.22+

    rec := httptest.NewRecorder()
    handler.ServeHTTP(rec, req)

    if rec.Code != http.StatusOK {
        t.Fatalf("expected 200, got %d", rec.Code)
    }

    var got User
    json.NewDecoder(rec.Body).Decode(&got)
    if got.Name != "Alice" {
        t.Errorf("expected Alice, got %s", got.Name)
    }
}
```

### Testing Middleware

```go
func TestRequestIDMiddleware(t *testing.T) {
    inner := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        id := r.Context().Value(requestIDKey)
        if id == nil || id == "" {
            t.Fatal("expected request ID in context")
        }
        w.WriteHeader(http.StatusOK)
    })

    handler := requestIDMiddleware(inner)
    req := httptest.NewRequest(http.MethodGet, "/", nil)
    rec := httptest.NewRecorder()
    handler.ServeHTTP(rec, req)

    if rec.Header().Get("X-Request-ID") == "" {
        t.Fatal("expected X-Request-ID in response header")
    }
}
```

### Integration Test with httptest.NewServer

```go
func TestIntegration(t *testing.T) {
    mux := setupRouter(testDeps) // wire up real mux with stub deps
    ts := httptest.NewServer(mux)
    defer ts.Close()

    resp, err := http.Get(ts.URL + "/users/1")
    if err != nil {
        t.Fatal(err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        t.Fatalf("expected 200, got %d", resp.StatusCode)
    }
}
```

---

## 10. Common Anti-Patterns

### Business Logic in Handlers

```go
// BAD: handler decides shipping rules
func handleShipOrder(w http.ResponseWriter, r *http.Request) {
    order := fetchOrder(r)
    if order.Weight > 50 { /* pick freight carrier */ }
    if order.Country == "US" { /* calculate tax */ }
    db.Exec("UPDATE orders SET status = 'shipped' ...")
}

// GOOD: handler is thin, logic lives in the service
func handleShipOrder(svc OrderService) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        id := r.PathValue("id")
        if err := svc.Ship(r.Context(), id); err != nil {
            mapError(w, err)
            return
        }
        respondJSON(w, http.StatusOK, nil)
    }
}
```

### No Timeouts on http.Server

```go
// BAD: slowloris and leaked goroutines
http.ListenAndServe(":8080", handler)

// GOOD: always configure timeouts (see section 7)
```

### Not Draining the Request Body

```go
// If you don't read the body, the connection can't be reused.
// Always drain or close:
defer func() {
    io.Copy(io.Discard, r.Body)
    r.Body.Close()
}()
```

### Inconsistent Error Shapes

```go
// BAD: some endpoints return {"error": "..."}, others return {"message": "...", "status": 400}
// Pick ONE envelope (see section 4) and use it everywhere via respondError().
```

### Giant Do-Everything Handlers

If a handler exceeds ~30 lines, it is likely doing too much. Extract:
- Decoding into a helper or generic function.
- Validation into a method on the request type.
- Error mapping into a shared function.

The handler itself should read like a table of contents, not an essay.
