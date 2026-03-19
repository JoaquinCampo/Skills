# Go Configuration — Reference

Configuration should be explicit and boring. Load it near program startup, parse into
typed structs, validate once, then pass the pieces each component needs. Never scatter
`os.Getenv` through business logic or rely on global config variables.

---

## 1. Config as Explicit Structs

Always define typed structs. Never use `map[string]interface{}`.

```go
type ServerConfig struct {
    Host         string        `yaml:"host" env:"SERVER_HOST"`
    Port         int           `yaml:"port" env:"SERVER_PORT"`
    ReadTimeout  time.Duration `yaml:"read_timeout" env:"SERVER_READ_TIMEOUT"`
    WriteTimeout time.Duration `yaml:"write_timeout" env:"SERVER_WRITE_TIMEOUT"`
}

type DatabaseConfig struct {
    DSN             string `yaml:"dsn" env:"DATABASE_DSN"`
    MaxOpenConns    int    `yaml:"max_open_conns" env:"DATABASE_MAX_OPEN_CONNS"`
    MaxIdleConns    int    `yaml:"max_idle_conns" env:"DATABASE_MAX_IDLE_CONNS"`
    ConnMaxLifetime time.Duration `yaml:"conn_max_lifetime" env:"DATABASE_CONN_MAX_LIFETIME"`
}

// RedisConfig and LogConfig are defined in their respective packages
// (e.g., redis/config.go, log/config.go) and imported here.

// Top-level config composes component configs.
type Config struct {
    Server   ServerConfig   `yaml:"server"`
    Database DatabaseConfig `yaml:"database"`
    Redis    RedisConfig    `yaml:"redis"`
    Log      LogConfig      `yaml:"log"`
}
```

Split by component. If a struct has 50 fields, break it apart.

---

## 2. Loading from Environment

Load at startup in `main()` or an `initConfig()` called from `main()`.

**Plain `os.Getenv` (small projects):**

```go
func loadConfig() Config {
    port, _ := strconv.Atoi(os.Getenv("SERVER_PORT")) // error intentionally ignored — falls back to 0
    if port == 0 {
        port = 8080
    }
    return Config{
        Server: ServerConfig{
            Host: envOrDefault("SERVER_HOST", "0.0.0.0"),
            Port: port,
        },
    }
}

func envOrDefault(key, fallback string) string {
    if v := os.Getenv(key); v != "" {
        return v
    }
    return fallback
}
```

**Third-party options** (convenient but not stdlib):

Using `github.com/caarlos0/env`:

```go
func loadConfig() (Config, error) {
    var cfg Config
    if err := env.Parse(&cfg); err != nil {
        return Config{}, fmt.Errorf("parsing config from env: %w", err)
    }
    return cfg, nil
}
```

Using `github.com/ilyakaznacheev/cleanenv`:

```go
func loadConfig(path string) (Config, error) {
    var cfg Config
    if err := cleanenv.ReadConfig(path, &cfg); err != nil {
        return Config{}, fmt.Errorf("reading config %s: %w", path, err)
    }
    return cfg, nil
}
```

> **Note:** The stdlib approach is `os.Getenv` + manual parsing (shown above) for environment variables, and the `flag` package for CLI arguments. Third-party libraries add convenience but are not necessary.

---

## 3. Loading from Files

| Format | When to use |
|--------|------------|
| YAML   | Human-edited config, K8s-adjacent projects |
| TOML   | CLI tools, simple key-value needs |
| JSON   | Machine-generated config, API responses |

```go
func loadFromYAML(path string) (Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return Config{}, fmt.Errorf("reading config file: %w", err)
    }
    var cfg Config
    if err := yaml.Unmarshal(data, &cfg); err != nil {
        return Config{}, fmt.Errorf("parsing config YAML: %w", err)
    }
    return cfg, nil
}
```

Prefer env vars for deployment-specific values (ports, DSNs, secrets) and files for
structural config that rarely changes per environment.

---

## 4. Validation at Load Time

Validate once, fail fast. Do not let invalid config propagate.

```go
func (c Config) Validate() error {
    var errs []string

    if c.Server.Port < 1 || c.Server.Port > 65535 {
        errs = append(errs, fmt.Sprintf("invalid server port: %d", c.Server.Port))
    }
    if c.Database.DSN == "" {
        errs = append(errs, "database DSN is required")
    }
    if c.Database.MaxOpenConns < 1 {
        errs = append(errs, "database max_open_conns must be >= 1")
    }
    if c.Server.ReadTimeout < time.Second {
        errs = append(errs, "server read_timeout must be >= 1s")
    }

    if len(errs) > 0 {
        return fmt.Errorf("config validation failed:\n  - %s", strings.Join(errs, "\n  - "))
    }
    return nil
}
```

Call in `main()`:

```go
cfg, err := loadConfig()
if err != nil {
    log.Fatalf("loading config: %v", err)
}
if err := cfg.Validate(); err != nil {
    log.Fatalf("invalid config: %v", err)
}
```

---

## 5. Passing Config to Components

Pass specific config pieces, not the entire Config struct.

```go
// Good — component receives only what it needs.
func NewServer(cfg ServerConfig, handler http.Handler) *http.Server {
    return &http.Server{
        Addr:         net.JoinHostPort(cfg.Host, strconv.Itoa(cfg.Port)),
        Handler:      handler,
        ReadTimeout:  cfg.ReadTimeout,
        WriteTimeout: cfg.WriteTimeout,
    }
}

// Good — database package knows nothing about server config.
func NewDB(cfg DatabaseConfig) (*sql.DB, error) {
    db, err := sql.Open("postgres", cfg.DSN)
    if err != nil {
        return nil, err
    }
    db.SetMaxOpenConns(cfg.MaxOpenConns)
    db.SetMaxIdleConns(cfg.MaxIdleConns)
    db.SetConnMaxLifetime(cfg.ConnMaxLifetime)
    return db, nil
}
```

Wire in `main()`:

```go
func main() {
    cfg := mustLoadConfig()

    db, err := NewDB(cfg.Database)
    // ...
    srv := NewServer(cfg.Server, router)
    // ...
}
```

> **Treat config as immutable after startup.** Once loaded and validated, do not mutate
> config values at runtime. If a component needs runtime-adjustable settings, use a
> separate mechanism (feature flags, a watched config source) rather than modifying the
> config struct in place.

---

## 6. Default Values

Set defaults explicitly — struct tags or a constructor function.

**Struct tags (with `github.com/caarlos0/env`):**

```go
type ServerConfig struct {
    Host         string        `env:"SERVER_HOST" envDefault:"0.0.0.0"`
    Port         int           `env:"SERVER_PORT" envDefault:"8080"`
    ReadTimeout  time.Duration `env:"SERVER_READ_TIMEOUT" envDefault:"5s"`
    WriteTimeout time.Duration `env:"SERVER_WRITE_TIMEOUT" envDefault:"10s"`
}
```

**Constructor function (for file-based loading):**

```go
func DefaultConfig() Config {
    return Config{
        Server: ServerConfig{
            Host:         "0.0.0.0",
            Port:         8080,
            ReadTimeout:  5 * time.Second,
            WriteTimeout: 10 * time.Second,
        },
        Database: DatabaseConfig{
            MaxOpenConns:    25,
            MaxIdleConns:    5,
            ConnMaxLifetime: 5 * time.Minute,
        },
    }
}
```

Load defaults first, then overlay file/env values on top.

---

## 7. Secrets Handling

- **Never log secrets.** Implement `fmt.Stringer` to redact.
- **Use env vars for secrets**, never config files checked into VCS.
- **Separate secret config** from non-sensitive config.

```go
type SecretConfig struct {
    DatabaseDSN string `env:"DATABASE_DSN,required"`
    APIKey      string `env:"API_KEY,required"`
    JWTSecret   string `env:"JWT_SECRET,required"`
}

// Prevent accidental logging via fmt.
func (s SecretConfig) String() string {
    return "[REDACTED]"
}

func (s SecretConfig) GoString() string {
    return "[REDACTED]"
}

// Also implement slog.LogValuer to redact in structured logging (slog).
func (s SecretConfig) LogValue() slog.Value {
    return slog.StringValue("[REDACTED]")
}
```

Keep `SecretConfig` as a separate struct passed only to components that need it.
For production systems, consider pulling secrets from a vault (AWS SSM, HashiCorp Vault)
at startup rather than plain env vars.

---

## 8. Feature Flags

For simple cases, boolean config fields are sufficient.

```go
type FeatureFlags struct {
    EnableNewCheckout  bool `env:"FF_NEW_CHECKOUT" envDefault:"false"`
    EnableBetaSearch   bool `env:"FF_BETA_SEARCH" envDefault:"false"`
    MaintenanceMode    bool `env:"FF_MAINTENANCE_MODE" envDefault:"false"`
}
```

Pass to handlers that check them:

```go
func NewCheckoutHandler(flags FeatureFlags, repo CheckoutRepo) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if flags.EnableNewCheckout {
            // new path
        } else {
            // old path
        }
    })
}
```

For dynamic feature flags (runtime toggling, percentage rollouts, user targeting),
use a dedicated system (LaunchDarkly, Unleash, or a DB-backed service).
Do not overload static config for dynamic behavior.

---

## 9. Testing Config

Provide helpers that return valid test configs. Override only what the test needs.

```go
func TestConfig() Config {
    dsn := os.Getenv("TEST_DATABASE_DSN")
    if dsn == "" {
        dsn = "postgres://localhost:5432/testdb?sslmode=disable"
    }

    return Config{
        Server: ServerConfig{
            Host:         "127.0.0.1",
            Port:         0, // random available port
            ReadTimeout:  1 * time.Second,
            WriteTimeout: 1 * time.Second,
        },
        Database: DatabaseConfig{
            DSN:          dsn,
            MaxOpenConns: 2,
            MaxIdleConns: 1,
        },
    }
}

func TestWithPort(cfg Config, port int) Config {
    cfg.Server.Port = port
    return cfg
}
```

Tests should never depend on the host machine's environment. Either use `TestConfig()`
or `t.Setenv()` for env-based loading:

```go
func TestLoadConfig(t *testing.T) {
    t.Setenv("SERVER_PORT", "9090")
    t.Setenv("DATABASE_DSN", "postgres://test:test@localhost/test")

    cfg, err := loadConfig()
    require.NoError(t, err)
    assert.Equal(t, 9090, cfg.Server.Port)
}
```

---

## 10. Common Anti-Patterns

### Global config variable

```go
// BAD — hidden dependency, impossible to test cleanly.
var AppConfig Config

func HandleRequest(w http.ResponseWriter, r *http.Request) {
    timeout := AppConfig.Server.ReadTimeout // implicit global access
}

// GOOD — pass config through constructor or function parameter.
func NewHandler(cfg ServerConfig) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        timeout := cfg.ReadTimeout
    }
}
```

### os.Getenv scattered through business logic

```go
// BAD — config read buried in domain code.
func (s *OrderService) PlaceOrder(ctx context.Context, order Order) error {
    if os.Getenv("ENABLE_FRAUD_CHECK") == "true" { // hidden config read
        // ...
    }
}

// GOOD — inject the flag at construction time.
type OrderService struct {
    fraudCheckEnabled bool
}
```

### Monster config struct

```go
// BAD — one struct with 50 fields, passed everywhere.
type Config struct {
    ServerHost, ServerPort, DBHost, DBPort, DBUser, DBPass string
    RedisHost, RedisPort, CacheEnabled string
    // ... 40 more fields
}

// GOOD — split by component (see Section 1).
```

### No validation at startup

```go
// BAD — missing DSN discovered 20 minutes into runtime.
db, err := sql.Open("postgres", cfg.Database.DSN) // DSN is empty string

// GOOD — validate at startup (see Section 4), crash immediately.
```

### Secrets in config files

```go
// BAD — config.yaml checked into git:
//   database:
//     dsn: "postgres://admin:s3cret@prod-db:5432/app"

// GOOD — secrets from env only, config file holds non-sensitive defaults.
//   database:
//     max_open_conns: 25
//   (DSN comes from DATABASE_DSN env var)
```
