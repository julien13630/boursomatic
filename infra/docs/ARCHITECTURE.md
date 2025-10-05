# Architecture Diagram

Visual representation of the Boursomatic GCP infrastructure.

## High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Google Cloud Platform                       │
│                         Project: boursomatic                    │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                         Region: europe-west1                    │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Cloud Run (Backend Service)                │  │
│  │  • FastAPI application                                  │  │
│  │  • Auto-scaling: 0-10 instances                        │  │
│  │  • CPU: 1 vCPU, Memory: 512MB                         │  │
│  │  • Service Account: boursomatic-run-{env}              │  │
│  └──────┬──────────────────────────────────────┬───────────┘  │
│         │                                       │               │
│         │ Cloud SQL Proxy                      │ VPC Connector │
│         │                                       │               │
│  ┌──────▼────────────────┐              ┌──────▼───────────┐  │
│  │   Cloud SQL           │              │   Memorystore    │  │
│  │   (PostgreSQL 15)     │              │   (Redis 7.0)    │  │
│  │                       │              │                  │  │
│  │  • Instance: db-*-*   │              │  • 1GB Basic     │  │
│  │  • Auto-backups       │              │  • VPC-private   │  │
│  │  • SSL enforced       │              │  • LRU eviction  │  │
│  │  • Point-in-time      │              │                  │  │
│  │    recovery (prod)    │              │                  │  │
│  └───────────────────────┘              └──────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Secret Manager                              │  │
│  │  • db-password (auto-generated)                         │  │
│  │  • secret-key (manual)                                  │  │
│  │  • jwt-secret (manual)                                  │  │
│  │  • api-keys (manual)                                    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              VPC Network (boursomatic-vpc-{env})        │  │
│  │  • Subnet: 10.0.0.0/24                                  │  │
│  │  • VPC Connector: 10.8.0.0/28                          │  │
│  │  • Private Google Access: Enabled                       │  │
│  │  • Firewall: Restrictive rules                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────┐         HTTPS           ┌─────────────┐
│  Client  │────────────────────────▶│  Cloud Run  │
│ (Browser)│◀────────────────────────│  (Backend)  │
└──────────┘      JSON Response      └──────┬──────┘
                                             │
                                             │
                    ┌────────────────────────┼────────────────────┐
                    │                        │                    │
                    │                        │                    │
              ┌─────▼──────┐          ┌─────▼──────┐      ┌─────▼──────┐
              │  Cloud SQL │          │   Redis    │      │   Secret   │
              │ (Database) │          │  (Cache)   │      │  Manager   │
              └────────────┘          └────────────┘      └────────────┘
                    │                        │                    │
                    │   Store/Retrieve       │   Cache/           │  Read
                    │   User Data,           │   Rate Limit       │  Secrets
                    │   Instruments,         │                    │
                    │   Recommendations      │                    │
                    │                        │                    │
                    └────────────────────────┴────────────────────┘
```

## Network Architecture

```
Internet
    │
    │ HTTPS (443)
    ▼
┌────────────────────────────────────────┐
│  Cloud Run Service                     │
│  (Public endpoint with auth)           │
└────────┬───────────────────────────────┘
         │
         │ VPC Access Connector
         │ (10.8.0.0/28)
         ▼
┌────────────────────────────────────────┐
│  VPC Network (10.0.0.0/24)             │
│  ┌──────────────┐   ┌──────────────┐  │
│  │  Cloud SQL   │   │    Redis     │  │
│  │  (Private)   │   │  (Private)   │  │
│  │  SSL:5432    │   │  :6379       │  │
│  └──────────────┘   └──────────────┘  │
└────────────────────────────────────────┘

Firewall Rules:
• allow-internal: VPC internal traffic
• allow-cloud-sql-proxy: Cloud Run → Cloud SQL
```

## IAM & Security Model

```
┌──────────────────────────────────────────────────────────┐
│                    Service Accounts                       │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  boursomatic-run-{env}@PROJECT.iam.gserviceaccount.com   │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Roles:                                            │  │
│  │  • roles/cloudsql.client (Cloud SQL access)       │  │
│  │  • roles/secretmanager.secretAccessor (secrets)   │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  Used by:                                                 │
│  • Cloud Run service                                      │
│                                                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    Secret Manager                         │
├──────────────────────────────────────────────────────────┤
│  db-password-{env}      ────▶  Auto-generated (32 chars) │
│  secret-key-{env}       ────▶  Manual (application)      │
│  jwt-secret-{env}       ────▶  Manual (JWT signing)      │
│  api-keys-{env}         ────▶  Manual (external APIs)    │
└──────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Developer Workflow                      │
└─────────────────────────────────────────────────────────┘
                            │
                            │
              ┌─────────────┼─────────────┐
              │                           │
              ▼                           ▼
    ┌──────────────────┐        ┌──────────────────┐
    │   Local Dev      │        │  GitHub Actions  │
    │   Environment    │        │     (CI/CD)      │
    └────────┬─────────┘        └────────┬─────────┘
             │                           │
             │                           │
             └───────────┬───────────────┘
                         │
                         │ terraform apply
                         │ docker push
                         │
                         ▼
              ┌────────────────────┐
              │   GCP Services     │
              │  • Cloud SQL       │
              │  • Cloud Run       │
              │  • Redis           │
              │  • Secret Manager  │
              └────────────────────┘
```

## Environment Topology

```
┌──────────────────────────────────────────────────────────┐
│                      Development                          │
│  • db-f1-micro (free tier)                               │
│  • 1GB Redis                                             │
│  • 0-10 Cloud Run instances                              │
│  • Deletion protection: OFF                              │
│  Cost: ~$10-20/month                                     │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                       Staging                             │
│  • db-g1-small                                           │
│  • 1GB Redis                                             │
│  • 1-10 Cloud Run instances                              │
│  • Deletion protection: ON                               │
│  Cost: ~$50-100/month                                    │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                      Production                           │
│  • db-custom-2-7680 (2 vCPU, 7.5GB RAM)                 │
│  • 2GB Redis (consider STANDARD_HA)                      │
│  • 1-20 Cloud Run instances                              │
│  • Deletion protection: ON                               │
│  • 30-day backups + PITR                                 │
│  Cost: ~$200-500/month                                   │
└──────────────────────────────────────────────────────────┘
```

## Component Relationships

```
main.tf
  │
  ├─► modules/networking
  │     └─► VPC, Subnet, Firewall, VPC Connector
  │
  ├─► modules/cloud_sql
  │     └─► PostgreSQL instance, Database, Auto-backups
  │
  ├─► modules/redis
  │     └─► Memorystore instance (requires VPC)
  │
  ├─► modules/secret_manager
  │     └─► Secrets (db-password auto-created)
  │
  └─► modules/cloud_run
        └─► Service, Service Account, IAM bindings
            (requires: VPC Connector, Cloud SQL, Redis, Secrets)
```

## Access Patterns

### External → Cloud Run
- HTTPS only (443)
- Public URL with optional authentication
- CORS configured
- Health checks: `/health`

### Cloud Run → Cloud SQL
- Via Cloud SQL Proxy (Unix socket)
- SSL enforced
- Connection: `/cloudsql/PROJECT:REGION:INSTANCE`
- Credentials from Secret Manager

### Cloud Run → Redis
- Via VPC Access Connector
- Private IP only (no public access)
- Standard Redis protocol (6379)

### Cloud Run → Secret Manager
- Via Secret Manager API
- IAM-controlled access
- Latest version by default

## Terraform Module Dependencies

```
networking ──┐
             ├──► redis
             │
             └──► cloud_run ◄──┬── cloud_sql
                               │
                               └── secret_manager
```

All modules deploy in dependency order:
1. networking (VPC, subnet, connector)
2. cloud_sql (database, auto-password to Secret Manager)
3. redis (cache, requires VPC)
4. secret_manager (application secrets)
5. cloud_run (backend service, requires all above)

---

**Version**: 0.1.0  
**Last Updated**: 2024-01
