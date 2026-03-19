# Neon Pricing & Limits (2026)

## Free Tier

| Feature | Limit |
|---------|-------|
| Projects | Up to 100 |
| Branches | 10 per project |
| Compute | 100 CU-hours/project/month |
| Autoscaling | Up to 2 CU (8 GB RAM) |
| Storage | 0.5 GB per project |
| Scale-to-zero timeout | 5 minutes (fixed) |
| Point-in-time restore | 6 hours, 1 GB change history |
| Organization members | Unlimited |

100 CU-hours = 0.25 CU running continuously for ~400 hours/month, or 1 CU for 100 hours.

## Launch Plan (Pay-as-you-go)

| Feature | Price/Limit |
|---------|------------|
| Compute | $0.106/CU-hour |
| Storage | $0.30/GB-month (first 50 GB), $0.15/GB-month after |
| Autoscaling | Up to 16 CU (64 GB RAM) |
| Branches | 10 included, $1.50/branch-month extra |
| Projects | 100 |
| Auto-suspend | Configurable (down to 0 = always on) |
| Point-in-time restore | Up to 7 days, $0.20/GB-month |

## Scale Plan (Pay-as-you-go)

| Feature | Price/Limit |
|---------|------------|
| Compute | $0.222/CU-hour |
| Storage | $0.30/GB-month (first 100 GB), $0.15/GB-month after |
| Autoscaling | Up to 16 CU (fixed computes up to 56 CU / 224 GB RAM) |
| Branches | 25 included, $1.50/branch-month extra |
| Projects | 1,000 (can increase on request) |
| Point-in-time restore | Up to 30 days, $0.20/GB-month |

## Agent Plan

For AI agent platforms provisioning thousands of databases. Custom resource limits and credits. Contact Neon sales.

## Key Formulas

```
CU-hours = compute_size_in_CU x hours_running

Examples:
  0.25 CU for 4 hours   = 1 CU-hour
  2 CU for 3 hours      = 6 CU-hours
  0.25 CU for 400 hours = 100 CU-hours (full free tier)
```

## What is a CU?

A Compute Unit (CU) allocates approximately 4 GB of RAM, along with associated CPU and local SSD resources. Scaling up increases these resources linearly:
- 1 CU = 1 vCPU, 4 GB RAM
- 2 CU = 2 vCPU, 8 GB RAM
- 4 CU = 4 vCPU, 16 GB RAM

## Storage Billing

- Measured in GB-months (1 GB stored for 1 month)
- Metered hourly, summed over the month
- Child branches: billed for min(accumulated_changes, logical_data_size)
- Delete unused branches to control costs

## Console Features

- **SQL Editor**: Run queries with `\d`, `\h` support (Postgres 18 compatible)
- **Monitoring Dashboard**: Real-time graphs for connections (Postgres + pooler)
- **Branch Management**: Create, delete, reset, compare branches visually
- **Schema Diff**: Side-by-side schema comparison between branches
- **Data Masking**: Address-specific masking for sensitive data
- **Connection Details**: Toggle pooled/direct connection strings
- **Autoscaling Config**: Set min/max CU, auto-suspend timeout
- **IP Allow List**: Restrict access by IP

## Recent Changes (Post-Databricks Acquisition, 2025)

- Compute costs reduced 15-25% across all tiers
- Storage pricing dropped from $1.75 to $0.35/GB-month
- Free plan doubled from 50 to 100 CU-hours/month
- Cold start latency improved to ~3ms average (Fluid compute)
- Data API launched (PostgREST-compatible, Early Access)
- Neon Auth for JWT-based RLS
