# Neon Branching Workflows

## Concepts

- Branches are **copy-on-write** clones - instant creation (~1 second), billed only for diverged data
- Every project starts with a `main` (root) branch
- Child branches inherit parent's schema + data at creation time
- Protected branches auto-generate new credentials for child branches (production isolation)
- Schema-only branching available for dev without production data

## Environment Pattern

```
main (production)
  |-- staging (long-lived, reset periodically from main)
  |-- feature/user-auth (short-lived, per feature)
  |-- preview/pr-42 (auto-created by CI, auto-deleted on merge)
```

## Branch Operations

### Create
```bash
# Standard branch from main
neonctl branches create --name dev/feature-x

# Branch from specific parent
neonctl branches create --name staging --parent main

# Schema-only (no data)
neonctl branches create --name clean-dev --parent main --schema-only

# Point-in-time branch
neonctl branches create --name restore-point --parent main --timestamp "2026-03-15T10:00:00Z"
```

### Reset (Sync with Parent)
```bash
# Reset branch to parent's current state (discards branch changes)
neonctl branches reset dev/feature-x --parent
```

### Restore
```bash
# Restore branch to a previous state
neonctl branches restore dev --source main --timestamp "2026-03-15T10:00:00Z"
```

### Schema Diff
```bash
# Compare branch to parent
neonctl branches schema-diff dev/feature-x

# Compare two specific branches
neonctl branches schema-diff main dev/feature-x

# Compare to a point in time
neonctl branches schema-diff dev --timestamp "2026-03-15T10:00:00Z"
```

Also available via API: `GET /projects/{project_id}/branches/{branch_id}/schema?compare_branch_id={other_id}`

### Expiration
```bash
# Auto-delete branch after date (for preview environments)
neonctl branches set-expiration preview/pr-42 --expiration "2026-04-01T00:00:00Z"
```

## GitHub Actions: Preview Branch per PR

```yaml
# .github/workflows/preview-branch.yml
name: Create Neon Branch for PR
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  create-branch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: neondatabase/create-branch-action@v5
        id: create-branch
        with:
          project_id: ${{ secrets.NEON_PROJECT_ID }}
          branch_name: preview/pr-${{ github.event.pull_request.number }}
          api_key: ${{ secrets.NEON_API_KEY }}
      - name: Run migrations
        run: npx prisma migrate deploy
        env:
          DIRECT_URL: ${{ steps.create-branch.outputs.db_url }}
          DATABASE_URL: ${{ steps.create-branch.outputs.db_url_pooled }}
```

```yaml
# .github/workflows/cleanup-branch.yml
name: Delete Neon Branch on PR Close
on:
  pull_request:
    types: [closed]

jobs:
  delete-branch:
    runs-on: ubuntu-latest
    steps:
      - uses: neondatabase/delete-branch-action@v3
        with:
          project_id: ${{ secrets.NEON_PROJECT_ID }}
          branch: preview/pr-${{ github.event.pull_request.number }}
          api_key: ${{ secrets.NEON_API_KEY }}
```

## Migration Strategy with Branches

1. Create dev branch: `neonctl branches create --name dev/feature-x`
2. Get connection strings: `neonctl connection-string dev/feature-x` (direct) and `--pooled`
3. Set `DATABASE_URL` and `DIRECT_URL` to the dev branch's connection strings
4. Modify schema in `prisma/schema.prisma`
5. Create and apply migration: `npx prisma migrate dev --name add-feature-x`
6. Test against dev branch
7. Compare: `neonctl branches schema-diff main dev/feature-x`
8. Apply to production (main branch): `npx prisma migrate deploy`
9. Delete dev branch: `neonctl branches delete dev/feature-x`

## Vercel Preview Integration

Neon integrates with Vercel to auto-create branches for preview deployments:
1. Install "Neon for Vercel" from Vercel Marketplace
2. Each preview deployment gets its own Neon branch
3. Environment variables auto-provisioned
4. Branch deleted when preview is removed
