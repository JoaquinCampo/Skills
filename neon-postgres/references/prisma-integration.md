# Prisma ORM with Neon

## Connection Setup

Prisma requires **two connection URLs** when using Neon with connection pooling:

```prisma
// prisma/schema.prisma
generator client {
  provider = "prisma-client-js"
  output   = "../generated/prisma"
}

datasource db {
  provider  = "postgresql"
  url       = env("DATABASE_URL")      // Pooled — for app queries
  directUrl = env("DIRECT_URL")        // Direct — for migrations
}
```

```env
# .env
# Pooled connection (PgBouncer) — app runtime
DATABASE_URL="postgresql://user:pass@ep-xyz-pooler.region.aws.neon.tech/dbname?sslmode=require"

# Direct connection — migrations, introspection, db push
DIRECT_URL="postgresql://user:pass@ep-xyz.region.aws.neon.tech/dbname?sslmode=require"
```

**Why two URLs?** Prisma Migrate needs a direct connection because migrations use advisory locks and session-level features incompatible with PgBouncer's transaction mode. The `directUrl` is used automatically by `prisma migrate` and `prisma db push`.

## Prisma Client Singleton (Next.js)

```typescript
// src/server/db.ts
import { PrismaClient } from "../../generated/prisma";

const createPrismaClient = () =>
  new PrismaClient({
    log:
      process.env.NODE_ENV === "development"
        ? ["query", "error", "warn"]
        : ["error"],
  });

const globalForPrisma = globalThis as unknown as {
  prisma: ReturnType<typeof createPrismaClient> | undefined;
};

export const db = globalForPrisma.prisma ?? createPrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = db;
```

**Why the global singleton?** Next.js hot-reloads in dev, which would create a new PrismaClient on every reload and exhaust Neon's connection limit. The global pattern reuses the client across hot reloads.

## Prisma Commands

```bash
# Create and apply migration (development)
npx prisma migrate dev --name <migration-name>

# Apply pending migrations (production/CI)
npx prisma migrate deploy

# Push schema without migration files (prototyping only)
npx prisma db push

# Pull existing DB schema into schema.prisma
npx prisma db pull

# Regenerate Prisma Client after schema changes
npx prisma generate

# Open Prisma Studio (visual DB browser)
npx prisma studio

# Reset database (destructive — drops all data)
npx prisma migrate reset

# Check migration status
npx prisma migrate status
```

## Package.json Scripts (typical)

```json
{
  "scripts": {
    "db:generate": "prisma generate",
    "db:migrate": "prisma migrate dev",
    "db:push": "prisma db push",
    "db:studio": "prisma studio"
  }
}
```

## Migration Workflow with Neon Branches

1. Create a dev branch: `neonctl branches create --name dev/feature-x`
2. Get connection strings: `neonctl connection-string dev/feature-x` (and `--pooled`)
3. Set `DATABASE_URL` and `DIRECT_URL` to the dev branch's connection strings
4. Modify schema in `prisma/schema.prisma`
5. Create migration: `npx prisma migrate dev --name add-feature-x`
6. Test the application against the dev branch
7. Compare schemas: `neonctl branches schema-diff main dev/feature-x`
8. Once verified, apply migration to production: `npx prisma migrate deploy` (pointing at main)
9. Delete dev branch: `neonctl branches delete dev/feature-x`

### Important Notes

- Always use `directUrl` (non-pooled) for migrations — Prisma handles this automatically via the `directUrl` field in schema.prisma
- Pooled connections cause errors during schema changes (advisory locks, prepared statements)
- `prisma migrate dev` is for development; use `prisma migrate deploy` in CI/production
- Never run `prisma migrate reset` against production — it drops all data

## Prisma with Neon Serverless Driver

For edge runtime compatibility, you can use the Neon serverless driver as Prisma's connection adapter:

```bash
npm install @prisma/adapter-neon @neondatabase/serverless
```

```prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["driverAdapters"]
  output          = "../generated/prisma"
}
```

```typescript
// src/server/db-edge.ts (for Edge API routes)
import { Pool, neonConfig } from "@neondatabase/serverless";
import { PrismaNeon } from "@prisma/adapter-neon";
import { PrismaClient } from "../../generated/prisma";

neonConfig.useSecureWebSocket = true;

const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const adapter = new PrismaNeon(pool);
export const db = new PrismaClient({ adapter });
```

**When to use the adapter**: Only needed for Edge Runtime (`export const runtime = 'edge'`). Standard Node.js runtime works fine with the default Prisma client and Neon's pooled connection.

## Neon-Specific Prisma Tips

- **Connection limit**: Neon 0.25 CU allows ~97 usable connections. Prisma's default pool is 10 connections — fine for most serverless apps
- **Idle timeout**: Prisma connections may be dropped when Neon scales to zero. The default Prisma client handles reconnection automatically
- **pgbouncer query param**: Not needed with Neon — use the `-pooler` hostname instead. Do NOT add `?pgbouncer=true` to the URL
- **Schema migrations**: Always run against `DIRECT_URL` (Prisma does this automatically via `directUrl`)
