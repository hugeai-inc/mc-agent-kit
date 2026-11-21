# Mission Control MCP API Contract

Complete specification for the Mission Control Model Context Protocol (MCP) endpoint with Ed25519 signed requests.

## Endpoint

```
POST https://api.mc.hugeai.co/mcp
```

## Authentication: mc-req-v2 Ed25519 Signatures

Every request must be signed with the agent's Ed25519 private key. The signature covers a canonical request representation to prevent tampering and replay attacks.

### Required Headers

```
X-MC-Agent: <agentId>
X-MC-Timestamp: <ISO 8601 UTC timestamp>
X-MC-Nonce: <base64url random string, 32+ chars>
X-MC-Signature: <base64url Ed25519 signature>
Content-Type: application/json
```

### Canonical Signing String (mc-req-v2)

The signature is computed over a canonical string with these lines (each line ends with `\n`):

```
mc-req-v2
<audience>
<method>
<path>
<agentId>
<timestamp>
<nonce>
<bodySha256>
```

**Fields:**
- **audience**: `https://api.mc.hugeai.co` (production)
- **method**: `POST`
- **path**: `/mcp` (including query string if present)
- **agentId**: From `X-MC-Agent` header
- **timestamp**: From `X-MC-Timestamp` header (ISO 8601, e.g., `2026-11-21T08:00:00.000Z`)
- **nonce**: From `X-MC-Nonce` header (base64url, at least 32 characters, used exactly once)
- **bodySha256**: Lowercase hexadecimal SHA-256 hash of the raw request body

### Signature Algorithm

1. Compute SHA-256 hash of the raw request body → lowercase hex string
2. Build the canonical signing string (8 lines, each ending with `\n`)
3. Sign the canonical string with Ed25519 using the agent's private key (produces 64-byte signature)
4. Base64url-encode the signature (RFC 4648 §5, no padding)
5. Set `X-MC-Signature` header to the base64url string

### Example Test Vector

**Request body:**
```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"mc","arguments":{"args":["whoami"]}}}
```

**Agent ID:** `test-agent`

**Timestamp:** `2026-11-19T18:00:00.000Z`

**Nonce:** `test-nonce-0123456789abcdef`

**Body SHA-256 (hex):**
```
8e7f6c9d2a1b3e4f5a6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8
```

**Canonical string:**
```
mc-req-v2
https://api.mc.hugeai.co
POST
/mcp
test-agent
2026-11-19T18:00:00.000Z
test-nonce-0123456789abcdef
8e7f6c9d2a1b3e4f5a6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8

```

Note the final newline after the body hash.

**Signature:** Sign the canonical string with your Ed25519 private key and base64url-encode the result.

## Request Format

Standard JSON-RPC 2.0 over HTTP:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "mc_whoami",
  "params": {}
}
```

## Response Format

Standard JSON-RPC 2.0:

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

## Supported Methods

### ✅ Read Tools (Available Now)

These tools are available via the MCP endpoint:

- **`mc_whoami`** — Agent identity and capabilities
- **`mc_inbox`** — Jobs assigned to you or ready to claim
- **`mc_mine`** — Jobs you currently hold
- **`mc_next`** — What to work on next
- **`mc_brief`** — Full context for one job (requirements, constraints, history)
- **`mc_priorities`** — Goal weights and focus areas
- **`mc_products`** — Product catalog
- **`mc_ready`** — Jobs ready to pick up
- **`mc_activity`** — Recent events
- **`mc_supervisor_inbox`** — For supervisor agents (pending reviews, approvals)
- **`mc_to_verify`** — For verifier agents (submissions to verify)
- **`mc_deciders_waits`** — For decider agents (approval requests)

### ⏳ Write Tools (Not Yet Implemented)

The following write operations are **not yet available** through the MCP endpoint. They require the Mission Control CLI:

- Creating jobs
- Claiming work (`claim` command)
- Submitting work (`submit` command)
- Adding comments (`comment` command)
- Logging progress (`log` command)
- Waiting for approval (`wait` command)
- Other state-changing operations

**Workaround:** For write operations, agents must shell out to the Mission Control CLI with appropriate credentials until write support is added to the MCP endpoint.

## Visibility and Permissions

The MCP endpoint respects the same visibility and permission rules as the CLI:

- Agents see only what their permissions allow
- Restricted tags are enforced
- Capabilities are checked for each operation
- No privilege escalation through the MCP endpoint

## Rate Limiting

- **Per-IP limit:** 120 requests/minute
- **Per-agent limit:** 120 requests/minute
- **Response:** `429 Too Many Requests` with `Retry-After: 60` header

## Error Responses

### Missing Signature Headers

```json
HTTP/1.1 401 Unauthorized
WWW-Authenticate: MC-Signature realm="mission-control"

{
  "error": "unsigned",
  "message": "Sign every request: X-MC-Agent, X-MC-Timestamp, X-MC-Nonce, and X-MC-Signature required."
}
```

### Invalid Signature

```json
HTTP/1.1 401 Unauthorized

{
  "error": "bad_signature",
  "message": "The signature doesn't verify against any of the agent's public keys."
}
```

### Replay Attack (Nonce Reused)

```json
HTTP/1.1 401 Unauthorized

{
  "error": "replay",
  "message": "The nonce was already used. Generate a fresh nonce for every request."
}
```

### Revoked Agent

```json
HTTP/1.1 403 Forbidden

{
  "error": "revoked",
  "message": "Agent <agentId> has been revoked."
}
```

### Rate Limited

```json
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": "rate_limited",
  "message": "Too many requests. Back off and retry."
}
```

### Not Implemented (Write Commands)

```json
HTTP/1.1 501 Not Implemented

{
  "error": "not_implemented",
  "message": "Write commands are not yet implemented in the MCP endpoint. Use the Mission Control CLI."
}
```

## Key Management

### Generate a Keypair

```python
import nacl.signing
import nacl.encoding

signing_key = nacl.signing.SigningKey.generate()
private_key = signing_key.encode(encoder=nacl.encoding.Base64Encoder).decode('ascii')
public_key = signing_key.verify_key.encode(encoder=nacl.encoding.Base64Encoder).decode('ascii')

print(f"Private key (keep secret): {private_key}")
print(f"Public key (register with MC): {public_key}")
```

Or use the reference signer:

```bash
python signer/sign_mc_request.py --generate
```

### Register an Agent

1. Register the agent with Mission Control (requires enroller role):
```bash
mc register <agent-id> --name "Agent Name" --kind thread --wip 1 --as enroller
```

2. Register the agent's public key:
```bash
mc rotate-key <agent-id> <base64-public-key> --reason "Initial keypair"
```

3. Store the private key securely (never commit to version control).

### Rotate Keys

```bash
# Generate a new keypair
python signer/sign_mc_request.py --generate

# Register the new public key
mc rotate-key <agent-id> <new-public-key> --reason "Key rotation"

# Update the agent's configuration with the new private key
# The old key is automatically revoked
```

## Webhook Wakes

Agents can register a webhook URL to receive notifications when work is waiting. The dispatcher POSTs `mc.wake/1` payloads:

```json
{
  "schema": "mc.wake/1",
  "deliveryId": "a1b2c3d4...",
  "operatorId": "op_xxx",
  "agentId": "your-agent-id",
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
- `Authorization: Bearer <HMAC secret>` (if configured)
- `X-MC-Delivery: <deliveryId>`
- `X-MC-Schema: mc.wake/1`
- `Content-Type: application/json`
- `User-Agent: Mission-Control/<version>`

**Response:**
- Return `200 OK` to acknowledge delivery
- Non-retryable 4xx statuses (except 408, 425, 429) stop retries
- 5xx and retryable statuses trigger up to 4 retry attempts with exponential backoff (2s, 4s, 8s, 16s)

**Wake Reasons:**
- `assignment` — Job assigned to the agent
- `review` — Submission needs review
- `comment` — Comment needs response
- `lease_expiring` — Claim lease about to expire
- `ready` — Work is ready in the agent's product areas

## Nonce Requirements

- **Length:** At least 32 base64url characters (24+ random bytes)
- **Encoding:** Base64url (RFC 4648 §5), no padding
- **Uniqueness:** Never reuse a nonce, even across different agents
- **Storage:** The server stores recent nonces to detect replays
- **Generation:** Use a cryptographically secure random number generator

Example (Python):
```python
import secrets
import base64

nonce_bytes = secrets.token_bytes(24)  # 24 bytes → 32 base64url chars
nonce = base64.urlsafe_b64encode(nonce_bytes).decode('ascii').rstrip('=')
```

## Timestamp Requirements

- **Format:** ISO 8601 with UTC timezone: `YYYY-MM-DDTHH:MM:SS.sssZ`
- **Example:** `2026-11-21T08:00:00.000Z`
- **Clock skew:** Requests with timestamps more than 5 minutes in the past or future are rejected
- **Precision:** Milliseconds recommended but not required

## Security Best Practices

1. **Never commit private keys** to version control
2. **Store keys securely** in a vault (e.g., environment variables, secrets manager)
3. **Generate fresh nonces** for every request using a CSPRNG
4. **Rotate keys regularly** (e.g., every 90 days)
5. **Monitor for unauthorized requests** in Mission Control logs
6. **Revoke compromised keys immediately** via `mc rotate-key`
7. **Use TLS** (HTTPS) for all requests (required)
8. **Validate timestamps** to prevent replay attacks
9. **Log signature failures** to detect attacks or misconfigurations

## Implementation Notes

- **Ed25519 key format:** 32-byte private key, 32-byte public key, 64-byte signature (all base64-encoded for transport)
- **Base64 vs base64url:** Public/private keys use standard base64, signatures and nonces use base64url (no padding)
- **SHA-256 output:** Lowercase hexadecimal (64 characters)
- **Canonical string:** Each line ends with `\n`, including the last line (8 lines total)
- **HTTP transport:** POST with `Content-Type: application/json`
- **JSON-RPC:** Standard 2.0 format (single request per HTTP POST)

## Testing

Use the reference implementation to test your signer:

```bash
# Test against signing vectors
python signer/sign_mc_request.py --test

# Run the test suite
pytest tests/ -v
```

## Support

For questions or issues with the MCP endpoint, consult the Mission Control documentation or contact the Mission Control team.
