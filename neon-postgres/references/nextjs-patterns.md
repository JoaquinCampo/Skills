# Neon with Next.js

## Server Components (App Router)

### With Prisma (default for this project)

```typescript
// app/posts/page.tsx (Server Component - default)
import { db } from "@/server/db";

export default async function PostsPage() {
  const posts = await db.post.findMany({
    orderBy: { createdAt: "desc" },
  });

  return (
    <ul>
      {posts.map((post) => (
        <li key={post.id}>{post.title}</li>
      ))}
    </ul>
  );
}
```

### With raw Neon driver (no ORM)

```typescript
// app/posts/page.tsx
import { neon } from "@neondatabase/serverless";

export default async function PostsPage() {
  const sql = neon(process.env.DATABASE_URL!);
  const posts = await sql`SELECT * FROM posts ORDER BY created_at DESC`;

  return (
    <ul>
      {posts.map((post) => (
        <li key={post.id}>{post.title}</li>
      ))}
    </ul>
  );
}
```

## Server Actions

```typescript
// app/posts/actions.ts
"use server";

import { db } from "@/server/db";
import { revalidatePath } from "next/cache";
import { z } from "zod";

const createPostSchema = z.object({
  title: z.string().min(1),
  content: z.string().min(1),
});

export async function createPost(formData: FormData) {
  const parsed = createPostSchema.safeParse({
    title: formData.get("title"),
    content: formData.get("content"),
  });

  if (!parsed.success) {
    return { error: "Invalid input" };
  }

  await db.post.create({ data: parsed.data });
  revalidatePath("/posts");
}
```

## Edge Runtime (API Route)

For edge routes, use the Neon serverless driver directly (Prisma's default client doesn't run on Edge):

```typescript
// app/api/posts/route.ts
import { neon } from "@neondatabase/serverless";
import { NextResponse } from "next/server";

export const runtime = "edge";

export async function GET() {
  const sql = neon(process.env.DATABASE_URL!);
  const posts =
    await sql`SELECT * FROM posts ORDER BY created_at DESC LIMIT 20`;
  return NextResponse.json(posts);
}
```

Or use Prisma with the Neon adapter (see `prisma-integration.md` for setup):

```typescript
// app/api/posts/route.ts
import { db } from "@/server/db-edge";
import { NextResponse } from "next/server";

export const runtime = "edge";

export async function GET() {
  const posts = await db.post.findMany({
    orderBy: { createdAt: "desc" },
    take: 20,
  });
  return NextResponse.json(posts);
}
```

## Route Handler (Node.js Runtime)

```typescript
// app/api/posts/route.ts
import { db } from "@/server/db";
import { NextResponse } from "next/server";

export async function GET() {
  const posts = await db.post.findMany({
    orderBy: { createdAt: "desc" },
    take: 20,
  });
  return NextResponse.json(posts);
}
```

## Driver Selection for Next.js

| Context                | Recommended Approach                  | Why                                      |
| ---------------------- | ------------------------------------- | ---------------------------------------- |
| Server Components      | Prisma (`db.model.findMany()`)        | Type-safe, singleton pattern             |
| Server Actions         | Prisma                                | Type-safe mutations, auto-cleanup        |
| Edge API Routes        | HTTP driver (`neon()`) or Prisma+adapter | Edge-compatible, minimal overhead        |
| Node.js API Routes     | Prisma                                | Full feature set, type safety            |
| Middleware             | HTTP driver (`neon()`)                | Must be edge-compatible                  |

## Environment Setup

```env
# .env.local
DATABASE_URL="postgresql://user:pass@ep-xyz-pooler.region.aws.neon.tech/dbname?sslmode=require"
DIRECT_URL="postgresql://user:pass@ep-xyz.region.aws.neon.tech/dbname?sslmode=require"
```

## Vercel Integration

Neon integrates natively with Vercel via the Vercel Marketplace:

1. Install "Neon for Vercel" from Vercel Marketplace
2. Environment variables are automatically provisioned
3. Preview deployments can auto-create Neon branches
4. Branch is deleted when preview deployment is removed
