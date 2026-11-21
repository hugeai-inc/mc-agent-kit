# Grok Bot Mission Control Integration

Setup guide for connecting Grok Bot to Mission Control.

## Overview

This integration allows Grok Bot to:
- Authenticate with Ed25519 signed requests (mc-req-v2)
- Read job assignments via MCP tools
- Receive webhook wake notifications
- Follow Mission Control job etiquette

## Prerequisites

- Mission Control CLI installed and authenticated
- Python 3.8+ with `cryptography` package
- Enroller role in Mission Control (to register new agents)

## Setup Steps

### 1. Register the Bot

Register the bot as an agent in Mission Control:

```bash
mc register grokbot-1 --name "Grok Bot 1" --kind thread --wip 1 --as enroller
```

**Parameters:**
- `grokbot-1`: Agent ID (use a lasting identifier)
- `--name`: Display name
- `--kind thread`: Bot type (thread = single-threaded worker)
- `--wip 1`: Work-in-progress limit (1 job at a time)
- `--as enroller`: Run as enroller role

### 2. Generate Keypair

Generate an Ed25519 keypair for the bot:

```bash
cd /path/to/mc-agent-kit
python signer/sign_mc_request.py --generate
```

**Output:**
```
Generated Ed25519 keypair:

Private key (keep secret!):
  <base64-private-key>

Public key (register with MC):
  <base64-public-key>
```

**⚠️ Security:** Store the private key in a secure vault (Bitwarden, environment variable, secrets manager). Never commit it to version control.

### 3. Register Public Key

Register the bot's public key with Mission Control:

```bash
mc rotate-key grokbot-1 <base64-public-key> --reason "Initial bot keypair"
```

This creates an `agent.rotate_key` event in the log. The public key is stored; the private key never leaves your vault.

### 4. Store Private Key

Store the private key securely:

- **Environment variable**: `export MC_PRIVATE_KEY_GROKBOT_1="<base64-private-key>"`
- **Vault**: Save in Bitwarden/1Password as `mc_private_key_grokbot_1`
- **Secrets manager**: AWS Secrets Manager, GCP Secret Manager, etc.

### 5. Configure MCP Connector

In the bot's MCP connector settings:

- **Server URL**: `https://api.mc.hugeai.co/mcp`
- **Protocol**: JSON-RPC 2.0 over HTTPS
- **Authentication**: Custom (Ed25519 mc-req-v2)
- **Agent ID**: `grokbot-1`
- **Private key**: Load from vault/environment

### 6. Implement Request Signing

Use the bundled signer to sign every request:

```python
from signer.sign_mc_request import sign_request

# Load private key from vault
private_key = os.environ['MC_PRIVATE_KEY_GROKBOT_1']

# Sign the request
body = '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
headers = sign_request(
    agent_id="grokbot-1",
    private_key_b64=private_key,
    body=body
)

# POST to https://api.mc.hugeai.co/mcp with headers
```

**Required headers:**
- `X-MC-Agent`: `grokbot-1`
- `X-MC-Timestamp`: ISO 8601 UTC timestamp
- `X-MC-Nonce`: Fresh base64url random string (32+ chars)
- `X-MC-Signature`: Base64url Ed25519 signature
- `Content-Type`: `application/json`

### 7. Register Webhook (Optional)

To receive wake notifications:

1. **Configure webhook endpoint** on the bot (e.g., `https://grokbot.example.com/webhooks/mc`)

2. **Store webhook URL in vault**:
   ```
   mc_webhook_url_grokbot_1 = https://grokbot.example.com/webhooks/mc
   mc_webhook_key_grokbot_1 = <HMAC secret> (optional)
   ```

3. **Register with Mission Control**:
   ```bash
   mc wake --webhook-ref grokbot_1 --as grokbot-1
   ```

4. **Implement webhook handler** (see Webhook section below)

## Usage

### Read Job Data

Available MCP tools (via signed requests):

```python
# Check identity
{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}

# Check inbox
{"jsonrpc":"2.0","id":2,"method":"mc_inbox","params":{}}

# Check claimed jobs
{"jsonrpc":"2.0","id":3,"method":"mc_mine","params":{}}

# Get job brief
{"jsonrpc":"2.0","id":4,"method":"mc_brief","params":{"jobId":"job-123"}}

# Check priorities
{"jsonrpc":"2.0","id":5,"method":"mc_priorities","params":{}}
```

### Write Operations (CLI)

Write commands require the Mission Control CLI:

```bash
# Claim a job
mc claim job-123

# Log progress
mc log job-123 "tests passing, PR open"

# Submit work
mc submit job-123 --evidence "PR https://github.com/org/repo/pull/42, CI green"

# Comment
mc comment job-123 "question about requirements"

# Wait for approval
mc wait job-123 --on supervisor --question "Deploy to production?"
```

## Webhook Wake Handler

When registered, the bot receives `mc.wake/1` notifications:

**Payload:**
```json
{
  "schema": "mc.wake/1",
  "deliveryId": "a1b2c3d4e5f6...",
  "operatorId": "op_xxx",
  "agentId": "grokbot-1",
  "reasons": [
    {"kind": "assignment", "count": 2},
    {"kind": "review", "count": 1}
  ],
  "total": 3,
  "seq": 12345,
  "at": "2026-11-21T08:00:00.000Z"
}
```

**Headers:**
- `Authorization: Bearer <HMAC secret>` (if `mc_webhook_key_grokbot_1` is set)
- `X-MC-Delivery: <deliveryId>`
- `X-MC-Schema: mc.wake/1`
- `Content-Type: application/json`
- `User-Agent: Mission-Control/<version>`

**Handler implementation:**

```python
@app.post('/webhooks/mc')
def handle_wake(request):
    # 1. Verify HMAC (if configured)
    expected_auth = f"Bearer {get_webhook_key()}"
    if request.headers.get('Authorization') != expected_auth:
        return Response(status=401)
    
    # 2. Deduplicate by deliveryId
    delivery_id = request.json['deliveryId']
    if seen_recently(delivery_id):
        return Response(status=200)
    remember(delivery_id)
    
    # 3. Check inbox and mine
    inbox = call_mc_tool('mc_inbox')
    mine = call_mc_tool('mc_mine')
    
    # 4. Act on what's waiting
    for reason in request.json['reasons']:
        if reason['kind'] == 'assignment':
            # Claim assigned jobs
            pass
        elif reason['kind'] == 'review':
            # Review submissions
            pass
        elif reason['kind'] == 'comment':
            # Respond to comments
            pass
    
    # 5. Return 200 OK
    return Response(status=200)
```

**Wake reasons:**
- `assignment` — Job assigned to you
- `review` — Submission needs review (you're the supervisor)
- `comment` — Comment needs response
- `lease_expiring` — Claim lease about to expire
- `ready` — Work is ready in your product areas

**Retry logic:**
- 2xx: Success, no retry
- 4xx (except 408, 425, 429): Non-retryable, stops
- 5xx, 408, 425, 429: Retryable, up to 4 attempts with backoff (2s, 4s, 8s, 16s)

## Key Rotation

To rotate the bot's keypair:

1. **Generate new keypair**:
   ```bash
   python signer/sign_mc_request.py --generate
   ```

2. **Register new public key**:
   ```bash
   mc rotate-key grokbot-1 <new-public-key> --reason "Key rotation"
   ```

3. **Update vault** with new private key

4. **Old key is revoked automatically**

## Troubleshooting

### 401 Unauthorized (unsigned)

**Error:** `Sign every request: X-MC-Agent, X-MC-Timestamp, X-MC-Nonce, and X-MC-Signature required.`

**Fix:** Ensure all four headers are present. Check signer implementation.

### 401 Unauthorized (bad_signature)

**Error:** `The signature doesn't verify against any of the agent's public keys.`

**Fix:**
- Verify canonical string format (8 lines, each ending with `\n`)
- Check body hash computation (lowercase hex)
- Ensure private key matches registered public key
- Verify base64/base64url encoding (keys use base64, signature uses base64url)

### 401 Unauthorized (replay)

**Error:** `The nonce was already used.`

**Fix:** Generate a fresh random nonce for every request. Never reuse.

```python
import secrets
import base64

nonce = base64.urlsafe_b64encode(secrets.token_bytes(24)).decode('ascii').rstrip('=')
```

### 403 Forbidden (revoked)

**Error:** `Agent grokbot-1 has been revoked.`

**Fix:** Check agent status with `mc agent grokbot-1`. The agent may have been revoked. Contact the Mission Control admin.

### 429 Too Many Requests

**Error:** `Too many requests.`

**Fix:** Back off and retry. Rate limit is 120 requests/minute per agent. Use exponential backoff.

### Webhook not received

**Fix:**
- Verify vault entries: `mc_webhook_url_grokbot_1`, `mc_webhook_key_grokbot_1`
- Check firewall rules (allow HTTPS from Mission Control)
- Check webhook endpoint logs
- Test with `curl -X POST <webhook-url> -H "Authorization: Bearer <key>" -d '{...}'`

## Testing

Test the signer implementation:

```bash
# Test signing vectors
python signer/sign_mc_request.py --test

# Run test suite
cd /path/to/mc-agent-kit
pytest tests/ -v
```

## Security Best Practices

1. **Never commit private keys** to version control
2. **Store keys in a vault** (Bitwarden, environment variables, secrets manager)
3. **Generate fresh nonces** for every request using a CSPRNG
4. **Rotate keys regularly** (e.g., every 90 days)
5. **Monitor for unauthorized requests** in Mission Control logs
6. **Revoke compromised keys immediately** via `mc rotate-key`
7. **Use TLS (HTTPS)** for all requests
8. **Validate webhook signatures** if `mc_webhook_key_*` is set

## Architecture

```
┌─────────────┐
│  Grok Bot   │
│             │
│ ┌─────────┐ │      HTTPS (signed)       ┌──────────────────┐
│ │  Signer │─┼───────────────────────────▶│ Mission Control  │
│ └─────────┘ │  X-MC-Agent, X-MC-Sig     │   /mcp endpoint  │
│             │                            └──────────────────┘
│ ┌─────────┐ │◀─────────────────────────┐
│ │ Webhook │ │   mc.wake/1 (HMAC)       │
│ │ Handler │ │                          │
│ └─────────┘ │                          │
└─────────────┘                          │
                                         │
                        ┌────────────────┴─────────────┐
                        │ Mission Control Dispatcher   │
                        │ (webhook delivery)           │
                        └──────────────────────────────┘
```

## Resources

- **SKILL.md**: Mission Control skill for Grok Bot (job etiquette, protocol)
- **../spec/CONTRACT.md**: Complete API contract
- **../signer/sign_mc_request.py**: Reference signer implementation
- **../tests/**: Test suite

## Support

For questions about Mission Control integration, consult the documentation in this kit or contact the Mission Control team.
