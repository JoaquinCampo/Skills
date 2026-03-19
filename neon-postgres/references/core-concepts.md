# Neon Core Concepts

## Architecture

Neon separates **storage and compute**. Storage is distributed and persistent; compute (Postgres instances) are ephemeral and can scale independently.

- **Project**: Top-level container. Contains branches, databases, roles, and computes.
- **Branch**: A copy-on-write clone of your data. Created in ~1 second regardless of DB size. You only pay for unique (diverged) data.
- **Compute Endpoint**: A Postgres instance attached to a branch. Measured in Compute Units (CU). 1 CU = 1 vCPU + 4 GB RAM.
- **Autoscaling**: Dynamically adjusts CPU/RAM based on workload within configured min/max CU range.
- **Scale-to-Zero**: Computes suspend after configurable idle timeout (default 5 min on free tier). Cold start: 500ms-2s for first query, then sub-100ms.

## Connection String Format

```
# Pooled (for application queries - default in console)
postgresql://user:password@ep-cool-darkness-123456-pooler.us-east-2.aws.neon.tech/dbname?sslmode=require

# Direct (for migrations, pg_dump, schema changes)
postgresql://user:password@ep-cool-darkness-123456.us-east-2.aws.neon.tech/dbname?sslmode=require
```

The `-pooler` suffix in the hostname routes through PgBouncer.

## Environment Variables Pattern

```env
# .env / .env.local
# Pooled connection - use for application runtime queries
DATABASE_URL="postgresql://user:pass@ep-xyz-pooler.region.aws.neon.tech/dbname?sslmode=require"

# Direct connection - use for migrations (Drizzle Kit, Prisma Migrate)
DIRECT_URL="postgresql://user:pass@ep-xyz.region.aws.neon.tech/dbname?sslmode=require"
```

**Rule**: Always use `DATABASE_URL` (pooled) for app queries, `DIRECT_URL` (direct) for migrations.

## Connection Pooling (PgBouncer)

Neon uses PgBouncer in **transaction mode** (`pool_mode=transaction`). Connections return to the pool after each transaction completes.

### Configuration (Not User-Configurable)

```
pool_mode=transaction
max_client_conn=10000
default_pool_size=0.9 * max_connections
max_prepared_statements=1000
query_wait_timeout=120 seconds
```

### max_connections by Compute Size

| CU | RAM | max_connections |
|----|-----|----------------|
| 0.25 | 1 GB | 104 |
| 0.50 | 2 GB | 209 |
| 1 | 4 GB | 419 |
| 2 | 8 GB | 839 |
| 4 | 16 GB | 1,678 |
| 8 | 32 GB | 3,357 |
| 9+ | 36+ GB | 4,000 (cap) |

7 connections are reserved for Neon superuser. On 0.25 CU, you get 97 usable connections.

### Not Supported with Pooled Connections

- `SET` / `RESET` (session variables)
- `LISTEN` / `NOTIFY`
- `PREPARE` / `DEALLOCATE` (SQL-level prepared statements)
- `WITH HOLD CURSOR`
- Temporary tables with `PRESERVE` / `DELETE ROWS`
- Session-level advisory locks

**Protocol-level prepared statements ARE supported** (via PgBouncer 1.22.0+, up to 1000 per connection).

### When to Use Direct vs Pooled

| Use Case | Connection Type |
|----------|----------------|
| Application queries | Pooled (`-pooler`) |
| Serverless/Edge functions | Pooled (`-pooler`) |
| Migrations (Drizzle Kit, Prisma) | Direct (no `-pooler`) |
| `pg_dump` / `pg_restore` | Direct |
| `LISTEN`/`NOTIFY` | Direct |
| Interactive transactions | Either (pooled fine in txn mode) |

## Performance Best Practices

### Cold Start Mitigation

1. **Use connection pooling** (pooled connection string) - PgBouncer masks most cold starts
2. **Set minimum compute size** for production to hold working set in memory
3. **Use HTTP driver** for one-shot queries (fewer round trips than TCP)
4. **Configure auto-suspend timeout** - increase beyond 5 min for production

### Query Optimization

1. **Use HTTP for single queries** - ~3 round trips vs ~8 for TCP
2. **Batch queries** with `sql.transaction([...])` for multiple reads
3. **Use pooled connections** for application queries
4. **Avoid SQL-level PREPARE** - use protocol-level prepared statements instead

### Connection Management

1. **Serverless functions**: Create and close Pool/Client within each request
2. **Don't create pools outside request handlers** in edge/serverless
3. **Use HTTP driver** when possible - no connection management needed
4. **Set reasonable pool sizes** to avoid exhausting `max_connections`

### Latency Benchmarks (2025-2026)

- TCP connection (warm): ~3ms average (Fluid compute)
- HTTP query: ~6ms average
- WebSocket (established): ~4ms
- Cold start: 500ms-2s (first query after scale-to-zero)
