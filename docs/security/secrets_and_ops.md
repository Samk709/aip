# Secrets and Ops Hardening

## Secrets management
- Do not store production secrets in `.env` files committed to Git.
- Use cloud secrets manager (AWS Secrets Manager / GCP Secret Manager / Azure Key Vault).
- Inject secrets at runtime through environment variables.

## Minimum required secrets
- `SECRET_KEY`
- `OPENAI_API_KEY`
- DB credentials (`DATABASE_URL` or `POSTGRES_*`)

## CI/CD security recommendations
- Enable branch protection and required checks.
- Run dependency vulnerability scans (e.g., `pip-audit`) in CI.
- Use image scanning for Docker images.

## Runtime hardening
- Put app behind HTTPS reverse proxy.
- Enable rate limits + WAF.
- Add centralized logging and alerting.
- Rotate secrets regularly.
