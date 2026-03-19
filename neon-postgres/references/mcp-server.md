# Neon MCP Server

Neon has an **official MCP server** (Model Context Protocol) maintained by the Neon team.
Repository: https://github.com/neondatabase/mcp-server-neon

## Quick Setup

```bash
# One command setup (configures Cursor, VS Code, Claude Code)
npx neonctl@latest init

# Or add just the MCP server
npx add-mcp https://mcp.neon.tech/mcp

# With API key (for remote agents)
npx add-mcp https://mcp.neon.tech/mcp --header "Authorization: Bearer $NEON_API_KEY"

# Global setup (user-level, not project-level)
npx add-mcp -g https://mcp.neon.tech/mcp
```

## Manual Configuration

### OAuth (recommended - no API key needed)
```json
{
  "mcpServers": {
    "neon": {
      "type": "http",
      "url": "https://mcp.neon.tech/mcp"
    }
  }
}
```

### API Key Authentication
```json
{
  "mcpServers": {
    "neon": {
      "type": "http",
      "url": "https://mcp.neon.tech/mcp",
      "headers": {
        "Authorization": "Bearer <NEON_API_KEY>"
      }
    }
  }
}
```

### Read-Only Mode
```json
{
  "mcpServers": {
    "neon": {
      "url": "https://mcp.neon.tech/mcp",
      "headers": {
        "X-Neon-Read-Only": "true"
      }
    }
  }
}
```

## Available Tools

### Project Management
- `list_projects` - List first 10 projects (configurable limit)
- `list_shared_projects` - List shared projects (search + limit params)
- `describe_project` - Get project details (ID, name, branches, databases)
- `create_project` - Create new project
- `delete_project` - Delete project and all resources
- `list_organizations` - List accessible organizations

### Branch Management
- `create_branch` - Create branch for dev/testing/migrations
- `delete_branch` - Delete a branch
- `describe_branch` - Get branch details and schema

### SQL Operations
- `run_sql` - Execute SQL queries against any branch
- `get_connection_string` - Get connection string for a branch

### Migration Workflow (Branch-Based)
- `prepare_migration` - Create a temporary branch + apply schema changes safely
- `complete_migration` - Merge migration branch into target branch

### Documentation
- `get_doc_resource` - Fetch Neon docs as markdown
- `list_docs_resources` - Discover available doc pages

## OAuth Scopes

- `read` - List projects, describe schemas, query data, view metrics
- `write` - Create/modify projects, branches, run DDL
- `*` - Both read and write (default with "Full access")

## Safety Notes

- The MCP Server is intended for **local development and IDE integrations only**
- Not recommended for production environments
- Can execute powerful operations (project deletion, DDL changes)
- Use read-only mode to restrict available tools
