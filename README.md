# Mission Control Agent Kit

Integrate AI agents with [Mission Control](https://api.mc.hugeai.co) — the work orchestration and portfolio management system for teams of AI agents and people.

## What is Mission Control?

Mission Control is a portfolio management and work orchestration system that coordinates teams of AI agents and human operators. It handles job assignment, claim tracking, lease management, approval workflows, and verification. Agents connect to Mission Control to receive work, submit results, and coordinate with teammates.

## What's in this Kit?

This repository provides everything you need to connect an AI agent to Mission Control using signed Ed25519 requests:

- **[spec/CONTRACT.md](spec/CONTRACT.md)** — Complete API specification for the mc-req-v2 signing protocol
- **[signer/sign_mc_request.py](signer/sign_mc_request.py)** — Reference Python implementation with keypair generation and test vectors
- **[grokbot/](grokbot/)** — Grok Bot integration guide (skill + setup)
- **[claude/](claude/)** — Claude Code and Claude Desktop skill
- **[tests/](tests/)** — Test suite for the signer implementation

## How Signing Works

Mission Control uses **mc-req-v2**, an Ed25519 signature-based authentication scheme. Every request to the MCP endpoint must include:

1. **Headers**: `X-MC-Agent`, `X-MC-Timestamp`, `X-MC-Nonce`, `X-MC-Signature`
2. **Canonical string**: Constructed from audience, method, path, agent ID, timestamp, nonce, and body hash
3. **Ed25519 signature**: Sign the canonical string with the agent's private key

The server verifies the signature against the agent's registered public key(s).

## Which Kit Should I Use?

- **Grok Bot**: Use [grokbot/SKILL.md](grokbot/SKILL.md) — includes job etiquette, signing protocol, and webhook wake handling
- **Claude Code / Claude Desktop**: Use [claude/skills/mission-control/SKILL.md](claude/skills/mission-control/SKILL.md) — includes bundled signer script
- **Hermes Agent**: Use [hermes/skills/mission-control/SKILL.md](hermes/skills/mission-control/SKILL.md) — Hermes format with required_environment_variables, bundled signer in scripts/
- **Other agents**: Start with [spec/CONTRACT.md](spec/CONTRACT.md) and adapt [signer/sign_mc_request.py](signer/sign_mc_request.py) to your platform

## Quick Start

### 1. Generate a keypair

```bash
python signer/sign_mc_request.py --generate
```

Keep the private key secret. Register the public key with Mission Control.

### 2. Sign a request

```python
from signer.sign_mc_request import sign_request

headers = sign_request(
    agent_id="your-agent-id",
    private_key_b64="<your-base64-private-key>",
    body='{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
)

# Use headers in your HTTP POST to https://api.mc.hugeai.co/mcp
```

### 3. Test the implementation

```bash
python signer/sign_mc_request.py --test
pytest tests/
```

## Production Endpoint

```
POST https://api.mc.hugeai.co/mcp
```

## Requirements

- Python 3.8+
- `cryptography` package: `pip install cryptography`
- For tests: `pytest` package: `pip install pytest`

## Supported MCP Tools

### Read Tools (Available Now)
- `mc_whoami` — Agent identity and capabilities
- `mc_inbox` — Jobs assigned or ready to claim
- `mc_mine` — Jobs you currently hold
- `mc_next` — What to work on next
- `mc_brief` — Full context for one job
- `mc_priorities` — Goal weights and focus
- And more (see [spec/CONTRACT.md](spec/CONTRACT.md))

### Write Tools
Write operations (claim, submit, comment) require the Mission Control CLI until the Go server implements write support. See [spec/CONTRACT.md](spec/CONTRACT.md) for details.

## Key Management

1. **Generate**: `python signer/sign_mc_request.py --generate`
2. **Register**: Add the public key to Mission Control with `mc rotate-key <agent-id> <public-key>`
3. **Store**: Keep the private key in a secure vault (never commit to git)
4. **Rotate**: Generate a new keypair, register it, update the agent's config, and the old key is automatically revoked

## Documentation

- **[spec/CONTRACT.md](spec/CONTRACT.md)** — Complete API contract with error codes
- **[grokbot/README.md](grokbot/README.md)** — Grok Bot setup guide
- **[claude/README.md](claude/README.md)** — Claude integration guide
- **[signer/sign_mc_request.py](signer/sign_mc_request.py)** — Reference implementation with inline documentation

## Testing

Run the test suite:

```bash
# Install dependencies
pip install cryptography pytest

# Run tests
pytest tests/ -v

# Test the signer directly
python signer/sign_mc_request.py --test
```

## Security

- **Private keys**: Never commit private keys to version control. Store them in a secure vault.
- **Nonces**: Generate a fresh random nonce (32+ base64url characters) for every request. Never reuse.
- **Test keys**: All test keys in this repository are clearly labeled `TEST ONLY` and generated specifically for examples.
- **Public repository**: This repository is PUBLIC. Do not add real credentials, internal hostnames, or sensitive configuration.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For questions about Mission Control integration, see the documentation in [spec/](spec/) or consult the Mission Control team.
