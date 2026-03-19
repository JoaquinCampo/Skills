# MercadoPago MCP Servers Reference

## Table of Contents
1. [Official MCP Server (Remote)](#official-mcp-server)
2. [Demo MCP Server (Local)](#demo-mcp-server)
3. [Community MCP Server (27+ Tools)](#community-mcp-server)
4. [Troubleshooting](#troubleshooting)

---

## Official MCP Server

The official Mercado Pago MCP Server is remote-hosted at `https://mcp.mercadopago.com/mcp` using Streamable HTTP Transport. It translates MP's API and documentation into MCP tools that AI assistants can invoke.

### Supported Clients
Cursor (v1+), VS Code, Windsurf, Cline, Claude Desktop, Claude Code, ChatGPT.

### Prerequisites
- Node.js 20+ with npx
- MercadoPago access token (from [Your Integrations dashboard](https://www.mercadopago.com.ar/developers/panel/app))

### Configuration

#### Cursor / VS Code (native Streamable HTTP support)
```json
{
  "mcpServers": {
    "mercadopago-mcp-server": {
      "url": "https://mcp.mercadopago.com/mcp",
      "headers": {
        "Authorization": "Bearer <ACCESS_TOKEN>"
      }
    }
  }
}
```

#### Claude Code (via mcp-remote bridge)
```json
{
  "mcpServers": {
    "mercadopago": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote@latest",
        "https://mcp.mercadopago.com/mcp",
        "--header", "Authorization:Bearer <ACCESS_TOKEN>"
      ]
    }
  }
}
```

#### Claude Desktop (via mcp-remote bridge)
Same as Claude Code config, placed in:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### Available Tools

The official server exposes tools focused on documentation search and integration guidance:

| Tool | Description |
|------|-------------|
| `search-documentation` | Search Mercado Pago's official developer documentation in multiple languages and sites. Parameters: `query`, `language`, `siteId`, `limit`. |

### Use Cases
1. **Search documentation through IDE** — Ask natural-language questions about MP features, payment methods, APIs
2. **Generate integration code** — Request code generation based on MP docs context
3. **Test and debug** — Get guidance on testing flows, QR code testing, sandbox setup

---

## Demo MCP Server

The demo server from MercadoLibre's official GitHub. Local STDIO-based, provides `search_documentation` tool.

### Setup
```bash
git clone https://github.com/mercadolibre/demo-mercadopago-mcp-server.git
cd demo-mercadopago-mcp-server
npm install
npm run build
```

### Configuration
```json
{
  "mcpServers": {
    "mercadopago": {
      "command": "node",
      "args": ["/path/to/demo-mercadopago-mcp-server/build/index.js"],
      "env": {
        "CLIENT_ID": "your-mercadopago-client-id",
        "CLIENT_SECRET": "your-mercadopago-client-secret",
        "DEBUG": "true"
      }
    }
  }
}
```

### Tool
| Tool | Description |
|------|-------------|
| `search_documentation` | Search MP developer docs. Params: `language`, `query`, `siteId`, `limit` |

---

## Community MCP Server

Comprehensive MCP server by [hdbookie](https://github.com/hdbookie/mercado-pago-mcp) with 27+ tools for full payment operations.

### Quick Install
```json
{
  "mcpServers": {
    "mercado-pago": {
      "command": "npx",
      "args": ["mercado-pago-mcp"],
      "env": {
        "MERCADOPAGO_ACCESS_TOKEN": "YOUR_ACCESS_TOKEN",
        "MERCADOPAGO_ENVIRONMENT": "sandbox"
      }
    }
  }
}
```

Or install globally: `npm install -g mercado-pago-mcp`

### Full Tool List

#### Core Payment Tools
| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_payment` | Create a new payment | `amount`, `description`, `payerEmail`, `paymentMethod` |
| `get_payment` | Get payment details | `paymentId` (required) |
| `search_payments` | Search with filters | `status`, `dateFrom`, `dateTo`, `payerEmail`, `limit` |
| `create_payment_link` | Create checkout preference (payment link) | `title`, `amount`, `quantity`, `expirationDate`, `successUrl`, `failureUrl`, `pendingUrl` |
| `refund_payment` | Refund a payment | `paymentId`, `amount` (optional for partial) |
| `create_customer` | Create/manage customer | Customer details |

#### Advanced Payment Tools (v2.0+)
| Tool | Description |
|------|-------------|
| `create_pix_payment` | Create PIX payment with QR code (Brazil) |
| `create_subscription` | Create recurring subscription |
| `batch_create_payments` | Batch payment creation |
| `manage_saved_cards` | Manage customer's saved cards |
| `split_payment` | Marketplace split payments |

#### Business Intelligence Tools (v3.0+)
| Tool | Description |
|------|-------------|
| `monitor_payment` | Real-time payment status monitoring |
| `analyze_fraud` | Risk scoring and fraud detection |
| `generate_report` | Payment reports and analytics |
| `export_to_accounting` | Export to QuickBooks, Xero, Sage, CSV |
| `calculate_tax` | Brazilian tax calculations (ICMS, PIS, COFINS, ISS) |
| `retry_payment` | Automatic retry for failed payments |
| `schedule_reminder` | Payment reminder scheduling |
| `simulate_webhook` | Simulate webhook notifications for testing |

### create_payment_link Example
```json
{
  "title": "Premium Subscription",
  "amount": 29.99,
  "quantity": 1,
  "successUrl": "https://mysite.com/success",
  "failureUrl": "https://mysite.com/failure"
}
```

---

## Troubleshooting

### Connection Testing (Terminal)
```bash
npx -y mcp-remote@latest https://mcp.mercadopago.com/mcp --header 'Authorization:Bearer <ACCESS_TOKEN>'
```

Expected output:
```
Connected to remote server using StreamableHTTPClientTransport
Local STDIO server running
Proxy established successfully
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `TransformStream is not defined` | Node.js too old | Upgrade to Node.js 20+ |
| `command not found: npx` | NPX not installed | Install Node.js (includes npm/npx) |
| Connection timeout | Firewall/proxy blocking | Check network, try direct HTTPS |
| 401 Unauthorized | Bad access token | Regenerate token in MP dashboard |
| Tools not loading | Client version too old | Update Cursor/VS Code/Claude Desktop |

### Environment Switching
- **Sandbox**: Use test credentials from MP dashboard; set `MERCADOPAGO_ENVIRONMENT=sandbox` for community MCP
- **Production**: Use production credentials; set `MERCADOPAGO_ENVIRONMENT=production`

### Node.js Version Check
```bash
node --version  # Must be v20.0.0 or higher
npx --version   # Should be available
```
