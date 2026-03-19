# Neon CLI (`neonctl`) and Management API

## CLI Installation

```bash
# Homebrew (macOS)
brew install neonctl

# npm
npm i -g neonctl

# Without installing
npx neonctl <command>
```

## CLI Authentication

```bash
# Interactive (opens browser OAuth flow)
neonctl auth

# API key (for CI/automation)
export NEON_API_KEY=your_api_key
neonctl projects list
```

## CLI Commands Reference

### Projects
```bash
neonctl projects list
neonctl projects create --name my-project
neonctl projects update <project-id> --name new-name
neonctl projects delete <project-id>
neonctl projects get <project-id>
```

### Branches
```bash
neonctl branches list --project-id <project-id>
neonctl branches create --name dev --project-id <project-id>
neonctl branches create --name staging --parent main
neonctl branches create --name clean-dev --parent main --schema-only
neonctl branches create --name restore --parent main --timestamp "2026-03-15T10:00:00Z"
neonctl branches reset dev --parent
neonctl branches restore dev --source main
neonctl branches rename old-name new-name
neonctl branches set-default dev
neonctl branches set-expiration dev --expiration "2026-04-01T00:00:00Z"
neonctl branches add-compute dev
neonctl branches delete dev
neonctl branches get dev
neonctl branches schema-diff main dev
```

### Databases
```bash
neonctl databases list --branch main
neonctl databases create --name mydb --branch main
neonctl databases delete mydb --branch main
```

### Roles
```bash
neonctl roles list --branch main
neonctl roles create --name app_user --branch main
neonctl roles delete app_user --branch main
```

### Connection Strings
```bash
neonctl connection-string main                    # direct
neonctl connection-string main --pooled           # pooled
neonctl connection-string dev --pooled            # specific branch
```

### Context (Set Defaults)
```bash
neonctl set-context --project-id <project-id>     # avoid --project-id every time
```

### Init (MCP + AI Setup)
```bash
neonctl init  # sets up MCP server, agent skills, VS Code extension
```

### Output Formats
```bash
neonctl branches list -o json    # JSON
neonctl branches list -o yaml    # YAML
neonctl branches list -o table   # Table (default)
```

### Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output` | Output format (json/yaml/table) | table |
| `--config-dir` | Config directory path | `~/.config/neonctl` |
| `--api-key` | Neon API key | `NEON_API_KEY` env var |
| `--no-color` | Disable colorized output | false |
| `-v, --version` | Show version | - |
| `-h, --help` | Show help | - |

---

## Neon Management API

### Authentication

```bash
# API Key types: Personal, Organization, Project-scoped
Authorization: Bearer <NEON_API_KEY>
```

### Base URL

```
https://console.neon.tech/api/v2
```

### Key Endpoints

```bash
# Projects
GET    /projects
POST   /projects
GET    /projects/{project_id}
DELETE /projects/{project_id}

# Branches
GET    /projects/{project_id}/branches
POST   /projects/{project_id}/branches
GET    /projects/{project_id}/branches/{branch_id}
DELETE /projects/{project_id}/branches/{branch_id}
POST   /projects/{project_id}/branches/{branch_id}/reset

# Databases
GET    /projects/{project_id}/branches/{branch_id}/databases
POST   /projects/{project_id}/branches/{branch_id}/databases

# Roles
GET    /projects/{project_id}/branches/{branch_id}/roles
POST   /projects/{project_id}/branches/{branch_id}/roles

# Endpoints (compute)
GET    /projects/{project_id}/endpoints
POST   /projects/{project_id}/endpoints

# Schema Diff
GET    /projects/{project_id}/branches/{branch_id}/schema?compare_branch_id={other_branch_id}

# Connection URI
GET    /projects/{project_id}/connection_uri?branch_id={branch_id}&pooled=true
```

### Example: Create Branch via API

```bash
curl -X POST "https://console.neon.tech/api/v2/projects/${PROJECT_ID}/branches" \
  -H "Authorization: Bearer ${NEON_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "branch": {
      "name": "dev/feature-x",
      "parent_id": "br-main-123456"
    },
    "endpoints": [{
      "type": "read_write"
    }]
  }'
```

### Neon Data API (PostgREST-compatible)

Query your database directly over HTTPS without a driver (Early Access):

```bash
# Enable via Neon Console > Project Settings > Data API

# Read
GET    https://<endpoint>.neon.tech/rest/v1/posts?select=id,title&order=created_at.desc

# Create
POST   https://<endpoint>.neon.tech/rest/v1/posts
Content-Type: application/json
{"title": "New Post", "content": "Hello"}

# Update
PATCH  https://<endpoint>.neon.tech/rest/v1/posts?id=eq.1

# Delete
DELETE https://<endpoint>.neon.tech/rest/v1/posts?id=eq.1
```

Supports JWT-based auth tied to Postgres RLS, or bring-your-own JWKS.
