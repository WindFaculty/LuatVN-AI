# Security & Secret Policy

- **Visibility**: Private repository under `github.com/WindFaculty` (per ADR-01).
- **Secrets**: Never commit API keys, database credentials, auth tokens, signing keys, `.env` files, or cloud service account keys. Use environment-scoped Secrets Manager.
- **Data & Privacy**: Never commit real user chats, PII, unapproved legal source dumps, or G5 holdout evaluation data. Use labeled synthetic fixtures only.
- **External Effects & Mutations**: Any agent-proposed write/external operation requires explicit human approval scoped to environment, actor, input hash, and expiry.
- **Reporting**: Report any suspected leak or security issue immediately to the project owner (`Trần Xuân Khoa`), revoke affected credentials, and follow the incident response procedure in `LuatVN-AI-control/docs/g0/08-security-threat-model.md`.
