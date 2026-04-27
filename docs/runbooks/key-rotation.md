# Key Rotation Runbook

## Scope
Rotate third-party API credentials and local secret references safely.

## Supported secret backends
- `env`
- `keychain`
- `op` (1Password)
- `bw` (Bitwarden)

## Rotation steps
1. Create a new key/token in provider console.
2. Update secret backend entry:
   - env: update `.env`
   - keychain: update service/account secret
   - op/bw: update referenced item
3. Validate retrieval path:
   - run a focused tool test using that key
4. Revoke old key in provider console.

## Recommended order
1. Non-critical services first (search/fetch integrations)
2. Notification channels
3. Financial/telephony/trading providers

## Verification commands
- `python3 -m pytest tests/test_config.py -q`
- provider-specific focused tests (for example Helius, telephony, trading)

## Emergency rotation
For suspected compromise:
1. Trigger stop (`python3 -m jarvis stop`)
2. Rotate all affected secrets
3. Revoke old credentials immediately
4. Run verification tests
5. Resume only after successful validation
