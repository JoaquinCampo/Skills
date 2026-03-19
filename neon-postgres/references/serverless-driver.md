# Neon Serverless Driver (`@neondatabase/serverless`)

The driver is GA (v1.0.0+). Requires Node.js 19+.

## Installation

```bash
npm install @neondatabase/serverless
```

## HTTP Driver (Recommended for Serverless/Edge)

Faster for single, non-interactive "one-shot" queries. Uses `fetch` under the hood.

```typescript
import { neon } from '@neondatabase/serverless';

const sql = neon(process.env.DATABASE_URL!);

// Single query (tagged template literal)
const posts = await sql`SELECT * FROM posts WHERE id = ${postId}`;

// Parameterized query
const users = await sql`SELECT * FROM users WHERE email = ${email}`;

// Multiple queries in a single non-interactive transaction
const [posts, tags] = await sql.transaction([
  sql`SELECT * FROM posts ORDER BY created_at DESC LIMIT 10`,
  sql`SELECT * FROM tags`,
], {
  isolationLevel: 'RepeatableRead',
  readOnly: true,
});

// Function-style transaction
const [authors, books] = await sql.transaction((txn) => [
  txn`SELECT * FROM authors`,
  txn`SELECT * FROM books`,
]);
```

### Transaction Options

- `isolationLevel`: `'ReadUncommitted'`, `'ReadCommitted'`, `'RepeatableRead'`, `'Serializable'`
- `readOnly`: `boolean`
- `deferrable`: `boolean`
- `arrayMode`: return rows as arrays instead of objects
- `fullResults`: include row count, fields metadata
- `fetchOptions`: custom `fetch` options

Note: options cannot be set per-query within a transaction.

## WebSocket Driver (for Sessions/Interactive Transactions)

Drop-in replacement for `pg` (node-postgres). Use when you need interactive transactions or `pg` API compatibility.

```typescript
import { Pool, neonConfig } from '@neondatabase/serverless';
import ws from 'ws';

// Required in Node.js (not needed in edge/browser environments)
neonConfig.webSocketConstructor = ws;

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

// Interactive transaction
const client = await pool.connect();
try {
  await client.query('BEGIN');
  const { rows } = await client.query('SELECT * FROM accounts WHERE id = $1', [accountId]);
  await client.query('UPDATE accounts SET balance = balance - $1 WHERE id = $2', [amount, accountId]);
  await client.query('COMMIT');
} catch (e) {
  await client.query('ROLLBACK');
  throw e;
} finally {
  client.release();
}
```

### Important: Serverless Lifecycle

In serverless environments (Vercel Edge, Cloudflare Workers), WebSocket connections cannot outlive a single request:
- Create `Pool`/`Client` **inside** the request handler
- Do NOT create them outside or reuse across requests
- Always close/release connections to avoid exhaustion

## When to Use Which

| Feature | HTTP (`neon()`) | WebSocket (`Pool`/`Client`) |
|---------|----------------|---------------------------|
| Single queries | Best (~3 round trips) | Good (~4 round trips) |
| Non-interactive transactions | Supported | Supported |
| Interactive transactions | Not supported | Supported |
| Session features (SET, LISTEN) | Not supported | Supported |
| Edge Runtime compatible | Yes | Yes |
| Latency (established conn) | ~6ms | ~4ms |
| Connection management needed | No | Yes |

## Connection Caching (Experimental)

```typescript
import { neon, neonConfig } from '@neondatabase/serverless';
neonConfig.fetchConnectionCache = true;
const sql = neon(process.env.DATABASE_URL!);
```

Opt-in only. Edge Runtime's scheduler prioritizes cached HTTP connections.
