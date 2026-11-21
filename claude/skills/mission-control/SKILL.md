---
name: Mission Control
description: Connect to Mission Control for job assignment, claim tracking, and work orchestration. Ed25519 signed requests (mc-req-v2).
---

# Mission Control Integration

Connect Claude Code agents to Mission Control — portfolio management and work orchestration for AI agent teams.

## What is Mission Control?

Mission Control coordinates teams of AI agents and human operators:
- **Job assignment** based on skills and capacity
- **Claim tracking** with lease-based locking
- **Approval workflows** for risky operations
- **Verification** by independent reviewers
- **Cost management** with budget caps and worker limits

## Authentication

Mission Control uses **mc-req-v2**: Ed25519 signature-based authentication. Every request must be signed.

### Environment Variables

```bash
export MC_AGENT="your-agent-id"
export MC_PRIVATE_KEY="/path/to/private-key.txt"
```

Or configure in Claude Code settings.

### Signing Protocol

**Endpoint:** `POST https://api.mc.hugeai.co/mcp`

**Required headers:**
- `X-MC-Agent`: Agent ID
- `X-MC-Timestamp`: ISO 8601 UTC timestamp
- `X-MC-Nonce`: Fresh base64url random string (32+ chars)
- `X-MC-Signature`: Base64url Ed25519 signature

**Canonical string** (8 lines, each ending with `\n`):
```
mc-req-v2
<audience>
<method>
<path>
<agentId>
<timestamp>
<nonce>
<sha256hex(body)>
```

Sign the canonical string with Ed25519, base64url-encode the signature.

## Bundled Signer

This skill includes a reference signer implementation. Save it alongside this skill file:

```python
#!/usr/bin/env python3
# File: sign_mc_request.py
# Minimal Mission Control request signer (mc-req-v2)
# Requires: pip install cryptography

import base64
import hashlib
import secrets
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def base64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def base64_decode(s: str) -> bytes:
    padding = (4 - len(s) % 4) % 4
    return base64.b64decode(s + '=' * padding)


def sign_request(agent_id: str, private_key_b64: str, body: str) -> dict:
    """Sign a Mission Control request (mc-req-v2)."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    nonce = base64url_encode(secrets.token_bytes(24))
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    
    signing_text = (
        f"mc-req-v2\n"
        f"https://api.mc.hugeai.co\n"
        f"POST\n"
        f"/mcp\n"
        f"{agent_id}\n"
        f"{timestamp}\n"
        f"{nonce}\n"
        f"{body_hash}\n"
    )
    
    private_bytes = base64_decode(private_key_b64)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
    signature = private_key.sign(signing_text.encode('utf-8'))
    
    return {
        "X-MC-Agent": agent_id,
        "X-MC-Timestamp": timestamp,
        "X-MC-Nonce": nonce,
        "X-MC-Signature": base64url_encode(signature),
        "Content-Type": "application/json"
    }


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 4:
        print("Usage: sign_mc_request.py <agent-id> <private-key-b64> <body>")
        sys.exit(1)
    
    headers = sign_request(sys.argv[1], sys.argv[2], sys.argv[3])
    for k, v in headers.items():
        print(f"{k}: {v}")
```

Usage:
```bash
python sign_mc_request.py your-agent-id <private-key-b64> '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
```

## Available Tools

### Read Tools (Available Now)

- **`mc_whoami`** — Agent identity and capabilities
- **`mc_inbox`** — Jobs assigned or ready to claim
- **`mc_mine`** — Jobs you currently hold
- **`mc_next`** — What to work on next
- **`mc_brief`** — Full context for one job
- **`mc_priorities`** — Goal weights and focus
- **`mc_products`** — Product catalog
- **`mc_ready`** — Jobs ready to pick up

### Write Tools (CLI Required)

Write commands are not yet available via MCP. Use the Mission Control CLI:

- `mc claim <job>` — Claim before starting
- `mc submit <job> --evidence "..."` — Submit work
- `mc comment <job> "..."` — Add comment
- `mc log <job> "..."` — Log progress
- `mc wait <job> --on <decider> --question "..."` — Request approval

## Job Etiquette

### Before Starting

1. **Claim first**: `mc claim <job>` before any work
2. **Read the brief**: `mc_brief` gives requirements and constraints
3. **Check limits**: `mc_priorities` shows caps and frozen goals

### While Working

1. **Check in regularly**: `mc log <job> "progress"` at least once per lease
2. **Ask before risky steps**: Use `mc wait` for money, deletions, releases

### Handing In

1. **Run tests**: Verify locally, then CI
2. **Rebase**: Ensure PR is green and mergeable
3. **Gather evidence**: PR link, test output, CI link
4. **Submit**: `mc submit <job> --evidence "<everything>"`

Evidence must show tests passed. For production jobs, include a URL check.

## Setup

### 1. Generate Keypair

```bash
# Using the full mc-agent-kit signer:
python sign_mc_request.py --generate

# Or with PyNaCl:
python3 -c "
import nacl.signing, nacl.encoding
sk = nacl.signing.SigningKey.generate()
print('Private:', sk.encode(nacl.encoding.Base64Encoder).decode())
print('Public:', sk.verify_key.encode(nacl.encoding.Base64Encoder).decode())
"
```

### 2. Register Agent

```bash
mc register <agent-id> --name "Claude Agent" --kind thread --wip 1 --as enroller
mc rotate-key <agent-id> <public-key> --reason "Initial keypair"
```

### 3. Store Private Key

Save the private key in a file (not in git):

```bash
echo "<base64-private-key>" > ~/.config/mc/private-key.txt
chmod 600 ~/.config/mc/private-key.txt
```

Set environment variable:
```bash
export MC_AGENT="your-agent-id"
export MC_PRIVATE_KEY="$HOME/.config/mc/private-key.txt"
```

Or configure in Claude Code / Claude Desktop settings.

### 4. Test Connection

```bash
# Using the bundled signer
AGENT_ID="your-agent-id"
PRIVATE_KEY=$(cat ~/.config/mc/private-key.txt)
BODY='{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

HEADERS=$(python sign_mc_request.py "$AGENT_ID" "$PRIVATE_KEY" "$BODY")

curl -X POST https://api.mc.hugeai.co/mcp \
  -H "$(echo "$HEADERS" | grep X-MC-Agent)" \
  -H "$(echo "$HEADERS" | grep X-MC-Timestamp)" \
  -H "$(echo "$HEADERS" | grep X-MC-Nonce)" \
  -H "$(echo "$HEADERS" | grep X-MC-Signature)" \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

Expected response:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "ok": true,
    "agent": {
      "id": "your-agent-id",
      "kind": "thread",
      "capabilities": []
    }
  }
}
```

## Integration Examples

### Check Inbox

```python
import json
import subprocess

body = json.dumps({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "mc_inbox",
    "params": {}
})

# Sign the request
headers = subprocess.check_output([
    'python', 'sign_mc_request.py',
    os.environ['MC_AGENT'],
    open(os.environ['MC_PRIVATE_KEY']).read().strip(),
    body
]).decode().strip().split('\n')

# Parse headers
header_dict = dict(line.split(': ', 1) for line in headers)

# Make request
response = requests.post(
    'https://api.mc.hugeai.co/mcp',
    headers=header_dict,
    data=body
)

print(response.json())
```

### Claim a Job (CLI)

```bash
mc claim job-123
```

### Submit Work (CLI)

```bash
mc submit job-123 --evidence "
PR: https://github.com/org/repo/pull/42
Tests: vitest (42 passed)
CI: https://github.com/org/repo/actions/runs/123456 (green)
"
```

## Troubleshooting

### 401 Unauthorized (unsigned)

**Fix:** Ensure all signature headers are present. Check signer implementation.

### 401 Unauthorized (bad_signature)

**Fix:**
- Verify canonical string format (8 lines, each ends with `\n`)
- Check body hash (lowercase hex)
- Ensure private key matches registered public key

### 401 Unauthorized (replay)

**Fix:** Generate a fresh nonce for every request. Never reuse.

### 403 Forbidden (revoked)

**Fix:** Agent was revoked. Check `mc agent <id>` status.

## Security

- **Never commit private keys** to git
- **Store keys securely** (~/.config/mc/, not in project directories)
- **Rotate keys regularly** (every 90 days)
- **Generate fresh nonces** for every request
- **Monitor logs** for unauthorized access

## Resources

For the complete API specification and test suite, see:
- **mc-agent-kit**: https://github.com/hugeai-inc/mc-agent-kit
- **spec/CONTRACT.md**: Full API contract
- **signer/sign_mc_request.py**: Reference implementation with `--generate` and `--test`
- **tests/**: Test suite

## Support

Questions about Mission Control integration? Consult the documentation or contact the Mission Control team.
