# Xin Platform Helm Chart

The `xin-platform` chart deploys the orchestrator, channel gateway, and ingestion worker services. It ships with sane staging defaults in `values-staging.yaml` and production defaults in `values-production.yaml`.

## Enabling External Secrets Operator (ESO)

Production clusters should source application secrets from [External Secrets Operator](https://external-secrets.io/). The chart exposes an `externalSecrets` block you can copy into your environment values file:

```yaml
externalSecrets:
  enabled: true
  refreshInterval: 30m
  secretStoreRef:
    name: doppler-prod
    kind: ClusterSecretStore
  items:
    - name: orchestrator-secrets
      target:
        name: xin-orchestrator-secrets
      dataFrom:
        - extract:
            key: xin/platform/prod/orchestrator
    - name: channel-gateway-secrets
      target:
        name: xin-channel-gateway-secrets
      data:
        - secretKey: GATEWAY_INSTAGRAM_TOKEN
          remoteRef:
            key: xin/platform/prod/channel-gateway
            property: INSTAGRAM_TOKEN
```

Recommended workflow:

1. Install ESO CRDs and controller (see `docs/RUNBOOK.md` for exact commands).
2. Create a `ClusterSecretStore` (or `SecretStore`) that points to your backing secret manager (Vault, Doppler, AWS Secrets Manager, etc.).
3. Enable the `externalSecrets` block (as above) in your environment values file.
4. Reference the projected Kubernetes Secret names via the `secretRefs` list under each service stanza (already present in `values-production.yaml`).
5. Run `scripts/preflight_check.sh <namespace> <release> <values-file>` to confirm required secrets exist before deploying.

If your secret names differ, override both the `items[*].target.name` entries and the service-specific `secretRefs` arrays so pods mount the Kubernetes Secret you provision.
