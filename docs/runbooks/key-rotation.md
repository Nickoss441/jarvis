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

## Troubleshooting Anthropic key failures

### 401 Unauthorized
Use this when runtime output includes `401`, `Unauthorized`, or `authentication_error`.

1. Confirm `ANTHROPIC_API_KEY` is set and non-empty in your active backend.
2. Confirm Jarvis reads the active key:
   - `python3 -c "from jarvis.config import Config; c=Config.from_env(); v=(c.get_secret('ANTHROPIC_API_KEY') or c.anthropic_api_key or ''); print(bool(v), len(v))"`
3. Ensure no stale shell session is overriding values.
4. Generate a fresh key in the Anthropic console and replace the existing one.
5. Revoke the old key after validation.
6. Re-run smoke:
   - `python3 -m jarvis run`

### 429 Rate limit exceeded
Use this when runtime output includes `rate_limit_error` or HTTP `429`.

1. Wait briefly and retry the same prompt.
2. Reduce prompt size and avoid repeated rapid retries.
3. Run smoke with minimal prompts first (for example one short prompt + `quit`).
4. If persistent, review organization/model rate limits and request an increase.

## Emergency rotation
For suspected compromise:
1. Trigger stop (`python3 -m jarvis stop`)
2. Rotate all affected secrets
3. Revoke old credentials immediately
4. Run verification tests
5. Resume only after successful validation
