# Infrastructure Documentation

Complete documentation for Boursomatic GCP infrastructure.

## Documents

### 📘 [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
**Start here!** Quick commands and 5-minute setup guide.
- Prerequisites checklist
- Fast development setup
- Common commands
- Quick troubleshooting
- **Best for**: Getting started quickly

### 📗 [GCP_SETUP.md](GCP_SETUP.md)
Complete step-by-step deployment guide.
- Detailed prerequisites
- Full setup walkthrough
- Environment configurations
- Cost optimization
- Maintenance procedures
- **Best for**: First-time deployment

### 📕 [SECRETS.md](SECRETS.md)
Secret and environment variable reference.
- All secrets documented
- Security best practices
- Rotation procedures
- Access control
- Local development
- **Best for**: Managing secrets securely

### 📙 [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md)
Comprehensive deployment verification checklist.
- Pre-deployment checks
- Infrastructure deployment
- Post-deployment configuration
- Testing and verification
- Environment-specific checklists
- **Best for**: Ensuring complete deployment

### 📔 [CI_CD.md](CI_CD.md)
Continuous integration and deployment guide.
- GitHub Actions workflow
- Workload Identity Federation
- Branch strategy
- Rollback procedures
- **Best for**: Automating deployments

### 📓 [PHASE_0.3_SUMMARY.md](PHASE_0.3_SUMMARY.md)
Phase 0.3 completion summary and technical details.
- What was delivered
- Architecture overview
- Acceptance criteria
- Technical highlights
- **Best for**: Understanding what was built

## Recommended Reading Order

### For First-Time Users
1. **QUICK_REFERENCE.md** - Get oriented quickly
2. **GCP_SETUP.md** - Follow detailed setup
3. **SECRETS.md** - Configure secrets properly
4. **SETUP_CHECKLIST.md** - Verify everything works

### For Developers
1. **QUICK_REFERENCE.md** - Common commands
2. **CI_CD.md** - Automate deployments
3. **SECRETS.md** - Local development setup

### For Operators
1. **SETUP_CHECKLIST.md** - Deployment verification
2. **GCP_SETUP.md** - Troubleshooting
3. **SECRETS.md** - Secret rotation

## Quick Start

```bash
# 1. Read the quick reference
cat QUICK_REFERENCE.md

# 2. Follow the setup guide
cat GCP_SETUP.md

# 3. Check secrets documentation
cat SECRETS.md

# 4. Use the checklist
cat SETUP_CHECKLIST.md
```

## Documentation Statistics

- **Total Documents**: 6
- **Total Characters**: ~45,000
- **Coverage**: 
  - ✅ Setup and deployment
  - ✅ Security and secrets
  - ✅ Troubleshooting
  - ✅ CI/CD automation
  - ✅ Cost optimization
  - ✅ Environment management

## Support

If you can't find what you need:
1. Check the relevant document above
2. Search for keywords in all docs
3. Review the Phase 0.3 summary
4. Check Terraform module READMEs

## Additional Resources

- **Terraform Docs**: `../terraform/README.md`
- **Main Infra README**: `../README.md`
- **Backend Docs**: `../../backend/docs/`

---

**Version**: 0.1.0  
**Last Updated**: 2024-01
