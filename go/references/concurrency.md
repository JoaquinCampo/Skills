# Go Concurrency Reference

> Concurrency is for coordination, not decoration. If sequential code is fast enough, keep it sequential.

---

## 1. Goroutine Lifecycle Management

Every goroutine must have a clear start, stop, and error path. Never spawn a goroutine without knowing how it ends.

**Bad — fire-and-forget with no lifecycle control:**
```go
func startWorkers() {
    for i := 0; i < 100; i++ {
        go process(i) // no way to stop, wait, or observe errors
    }
}
```

**Good — goroutine with explicit lifecycle:**
```go
// One writer per channel: if multiple goroutines share a channel, do NOT close
// it here — use a sync.WaitGroup and close after all writers finish.
func startWorker(ctx context.Context, id int, results chan<- Result) {
    defer close(results) // sender closes (safe only when this is the sole writer)
    for {
        select {
        case <-ctx.Done():
            return
        default:
            r, err := doWork(id)
            if err != nil {
                results <- Result{Err: err}
                return
            }
            results <- r
        }
    }
}
```

**Rule:** Before writing `go func()`, answer: (1) What stops this goroutine? (2) Who waits for it? (3) Where do errors go?

---

## 2. Context for Cancellation

`context.Context` is mandatory for any request-scoped or long-running operation.

```go
// WithCancel — manual cancellation
ctx, cancel := context.WithCancel(parentCtx)
defer cancel() // always defer cancel to avoid leaks

// WithTimeout — automatic deadline
ctx, cancel := context.WithTimeout(parentCtx, 5*time.Second)
defer cancel()

// WithDeadline — fixed point in time
deadline := time.Now().Add(30 * time.Second)
ctx, cancel := context.WithDeadline(parentCtx, deadline)
defer cancel()

// WithCancelCause (Go 1.20+) — attach a specific error reason to cancellation
ctx, cancel := context.WithCancelCause(parentCtx)
cancel(fmt.Errorf("upstream service unhealthy")) // cancel with a cause
// Later, retrieve the cause:
//   err := context.Cause(ctx) // returns the error passed to cancel
```

**Respecting cancellation inside goroutines:**
```go
func fetch(ctx context.Context, url string) ([]byte, error) {
    req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
    if err != nil {
        return nil, err
    }
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return nil, err // includes context cancellation
    }
    defer resp.Body.Close()
    return io.ReadAll(resp.Body)
}
```

**Checking ctx.Done() in loops:**
```go
func processItems(ctx context.Context, items []Item) error {
    for _, item := range items {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
        }
        if err := handle(item); err != nil {
            return err
        }
    }
    return nil
}
```

---

## 3. Channel Patterns

### Unbuffered vs Buffered

| Type | Behavior | Use when |
|------|----------|----------|
| `make(chan T)` | Sender blocks until receiver is ready | Synchronization / handoff |
| `make(chan T, n)` | Sender blocks only when buffer is full | Decoupling producer/consumer speed |

### Ownership Rules

- The **sender** owns the channel and is responsible for closing it.
- The **receiver** never closes a channel.
- Closing a channel is a signal that no more values will be sent.

```go
// Good — sender closes
func produce(out chan<- int) {
    defer close(out)
    for i := 0; i < 10; i++ {
        out <- i
    }
}

func consume(in <-chan int) {
    for v := range in { // range exits when channel closes
        fmt.Println(v)
    }
}
```

**Bad — receiver closes (causes panic if sender writes after close):**
```go
func consume(ch chan int) {
    for v := range ch {
        if v == -1 {
            close(ch) // WRONG: receiver should not close
            return
        }
    }
}
```

### Done Channel Pattern

```go
func doWork(done <-chan struct{}) <-chan Result {
    results := make(chan Result)
    go func() {
        defer close(results)
        for {
            select {
            case <-done:
                return
            case results <- compute():
            }
        }
    }()
    return results
}
```

---

## 4. Channels vs Mutexes

| Use channels when | Use mutexes when |
|-------------------|------------------|
| Passing ownership of data between goroutines | Protecting shared state accessed by multiple goroutines |
| Coordinating multiple goroutines | Simple counter or flag |
| Implementing pipelines | Cache or map with concurrent access |
| Signaling events (done, ready) | Struct field protection |

**Mutex for shared state:**
```go
type Counter struct {
    mu    sync.Mutex
    count int
}

func (c *Counter) Increment() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.count++
}

func (c *Counter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.count
}
```

**Use `sync.RWMutex` when reads vastly outnumber writes:**
```go
type Cache struct {
    mu   sync.RWMutex
    data map[string]string
}

func (c *Cache) Get(key string) (string, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    v, ok := c.data[key]
    return v, ok
}

func (c *Cache) Set(key, value string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.data[key] = value
}
```

**Anti-pattern — using a channel where a mutex is simpler:**
```go
// Overcomplicated: channel as mutex
sem := make(chan struct{}, 1)
sem <- struct{}{} // "lock"
count++
<-sem             // "unlock"

// Just use sync.Mutex instead.
```

---

## 5. sync.WaitGroup

```go
func processAll(ctx context.Context, items []Item) error {
    var wg sync.WaitGroup
    errs := make(chan error, len(items))

    for _, item := range items {
        wg.Add(1) // Add BEFORE launching goroutine
        go func(it Item) {
            defer wg.Done()
            if err := process(ctx, it); err != nil {
                errs <- err
            }
        }(item)
    }

    wg.Wait()
    close(errs)

    for err := range errs {
        return err // return first error
    }
    return nil
}
```

### Common Pitfalls

```go
// BAD: Add inside the goroutine — race condition
go func() {
    wg.Add(1) // might not execute before wg.Wait()
    defer wg.Done()
    work()
}()
wg.Wait()

// BAD: forgetting Done
wg.Add(1)
go func() {
    // no defer wg.Done() — wg.Wait() blocks forever
    work()
}()
```

---

## 6. errgroup.Group

`errgroup` combines WaitGroup + error propagation + context cancellation. Prefer it over raw WaitGroup when goroutines can fail.

```go
import "golang.org/x/sync/errgroup"

func fetchAll(ctx context.Context, urls []string) ([]Response, error) {
    g, ctx := errgroup.WithContext(ctx)
    responses := make([]Response, len(urls))

    for i, url := range urls {
        i, url := i, url // capture loop vars (Go <1.22; unnecessary in Go 1.22+ where loop vars are per-iteration)
        g.Go(func() error {
            resp, err := fetch(ctx, url)
            if err != nil {
                return err // cancels ctx for other goroutines
            }
            responses[i] = resp // safe: each goroutine writes to its own index
            return nil
        })
    }

    if err := g.Wait(); err != nil {
        return nil, err
    }
    return responses, nil
}
```

**With concurrency limit (Go 1.20+):**
```go
g, ctx := errgroup.WithContext(ctx)
g.SetLimit(10) // at most 10 goroutines active at once

for _, url := range urls {
    url := url
    g.Go(func() error {
        return fetch(ctx, url)
    })
}
```

---

## 7. Bounded Parallelism

### Worker Pool

```go
func workerPool(ctx context.Context, jobs []Job, numWorkers int) <-chan Result {
    jobsCh := make(chan Job)
    results := make(chan Result)

    // Start workers
    var wg sync.WaitGroup
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobsCh {
                select {
                case <-ctx.Done():
                    return
                case results <- process(job):
                }
            }
        }()
    }

    // Send jobs
    go func() {
        defer close(jobsCh)
        for _, job := range jobs {
            select {
            case <-ctx.Done():
                return
            case jobsCh <- job:
            }
        }
    }()

    // Close results when all workers finish
    go func() {
        wg.Wait()
        close(results)
    }()

    return results
}
```

### Semaphore Pattern

```go
func bounded(ctx context.Context, items []Item, maxConcurrency int) error {
    sem := make(chan struct{}, maxConcurrency)
    var wg sync.WaitGroup

loop:
    for _, item := range items {
        select {
        case <-ctx.Done():
            break loop // break out of the for loop, not just the select
        case sem <- struct{}{}: // acquire
        }

        wg.Add(1)
        go func(it Item) {
            defer wg.Done()
            defer func() { <-sem }() // release
            process(ctx, it)
        }(item)
    }

    wg.Wait()
    return ctx.Err()
}
```

---

## 8. sync.Once, sync.Map, sync.Pool

### sync.Once — one-time initialization

```go
var (
    instance *DB
    once     sync.Once
)

func GetDB() *DB {
    once.Do(func() {
        instance = connectDB() // runs exactly once, even under contention
    })
    return instance
}

// sync.OnceValue / sync.OnceValues (Go 1.21+) — cleaner one-shot init with return values
var getDB = sync.OnceValue(func() *DB {
    return connectDB()
})
// Usage: db := getDB()

// For functions that return (T, error):
var getConfig = sync.OnceValues(func() (*Config, error) {
    return loadConfig()
})
// Usage: cfg, err := getConfig()
```

### sync.Map — concurrent map (limited use cases)

Use `sync.Map` only when: (1) keys are stable (write-once, read-many), or (2) disjoint goroutines write to disjoint key sets. Otherwise, prefer `map` + `sync.RWMutex`.

```go
var cache sync.Map

func CachedLookup(key string) (Value, error) {
    if v, ok := cache.Load(key); ok {
        return v.(Value), nil
    }
    v, err := expensiveLookup(key)
    if err != nil {
        return Value{}, err
    }
    cache.Store(key, v)
    return v, nil
}
```

### sync.Pool — reusable temporary objects

Use for reducing GC pressure on frequently allocated short-lived objects. Objects may be collected at any time.

```go
var bufPool = sync.Pool{
    New: func() any {
        return new(bytes.Buffer)
    },
}

func process(data []byte) string {
    buf := bufPool.Get().(*bytes.Buffer)
    defer func() {
        buf.Reset()
        bufPool.Put(buf)
    }()
    buf.Write(data)
    return buf.String()
}
```

---

## 9. Select Statement Patterns

### Timeout

```go
select {
case result := <-ch:
    handle(result)
case <-time.After(3 * time.Second):
    return ErrTimeout
}
```

### Cancellation with context

```go
select {
case result := <-ch:
    handle(result)
case <-ctx.Done():
    return ctx.Err()
}
```

### Non-blocking send/receive

```go
// Non-blocking receive
select {
case msg := <-ch:
    handle(msg)
default:
    // channel empty, do something else
}

// Non-blocking send (drop if full)
select {
case ch <- msg:
default:
    log.Warn("channel full, dropping message")
}
```

### Priority select (drain high-priority first)

```go
for {
    select {
    case <-ctx.Done():
        return
    case msg := <-highPriority:
        handleHigh(msg)
    default:
        select {
        case <-ctx.Done():
            return
        case msg := <-highPriority:
            handleHigh(msg)
        case msg := <-lowPriority:
            handleLow(msg)
        }
    }
}
```

---

## 10. Common Anti-Patterns

### Unbounded goroutine creation

```go
// BAD: one goroutine per request with no limit
func handler(w http.ResponseWriter, r *http.Request) {
    go expensiveTask(r.Context()) // can exhaust memory under load
}

// GOOD: use a worker pool or semaphore to bound concurrency
// import "golang.org/x/sync/semaphore"
// var sem = semaphore.NewWeighted(100)
func handler(w http.ResponseWriter, r *http.Request) {
    if err := sem.Acquire(r.Context(), 1); err != nil {
        http.Error(w, "too busy", http.StatusServiceUnavailable)
        return
    }
    go func() {
        defer sem.Release(1)
        expensiveTask(r.Context())
    }()
}
```

### Goroutine without cancellation

```go
// BAD: runs forever if parent doesn't signal
go func() {
    for {
        poll()
        time.Sleep(time.Second)
    }
}()

// GOOD: respects cancellation
go func(ctx context.Context) {
    ticker := time.NewTicker(time.Second)
    defer ticker.Stop()
    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            poll()
        }
    }
}(ctx)
```

### Data race from shared state

```go
// BAD: concurrent map write without synchronization
m := make(map[string]int)
for i := 0; i < 10; i++ {
    go func(id int) {
        m[fmt.Sprint(id)] = id // RACE
    }(i)
}

// GOOD: protect with mutex or use sync.Map
var mu sync.Mutex
m := make(map[string]int)
for i := 0; i < 10; i++ {
    go func(id int) {
        mu.Lock()
        m[fmt.Sprint(id)] = id
        mu.Unlock()
    }(i)
}
```

### Goroutine leak from forgotten context

```go
// BAD: goroutine blocks forever if nobody reads from ch
func leaky() <-chan int {
    ch := make(chan int)
    go func() {
        val := expensiveCompute()
        ch <- val // blocks forever if caller abandons ch
    }()
    return ch
}

// GOOD: accept context so caller can cancel
func safe(ctx context.Context) <-chan int {
    ch := make(chan int, 1) // buffer of 1 prevents leak if unread
    go func() {
        val := expensiveCompute()
        select {
        case ch <- val:
        case <-ctx.Done():
        }
    }()
    return ch
}
```

---

## Quick Decision Guide

```
Need concurrency? → Is sequential fast enough? → YES → Don't use goroutines.
                                                → NO  ↓
Passing data between goroutines? → YES → Use channels.
                                 → NO  ↓
Protecting shared state? → YES → Use sync.Mutex or sync.RWMutex.
                         → NO  ↓
Running N tasks, collecting errors? → YES → Use errgroup.Group.
                                    → NO  ↓
Running N tasks, no errors needed? → YES → Use sync.WaitGroup.
                                   → NO  ↓
Need bounded concurrency? → YES → Use semaphore or errgroup.SetLimit().
```
