# Mission Control Integration for Claude

Setup guide for connecting Claude Code and Claude Desktop to Mission Control.

## Overview

This integration allows Claude agents to:
- Authenticate with Ed25519 signed requests
- Read job assignments via Mission Control MCP tools
- Follow job etiquette (claim, log, submit)
- Use the bundled signer script for request signing

## Installation

### For Claude Code

Claude Code reads skills from:
- **User skills**: `~/.claude/skills/`
- **Project skills**: `.claude/skills/` in your project

Install the Mission Control skill:

```bash
# User-level (available in all projects)
mkdir -p ~/.claude/skills/
cp -r claude/skills/mission-control ~/.claude/skills/

# Project-level (only in this project)
mkdir -p .claude/skills/
cp -r claude/skills/mission-control .claude/skills/
```

### For Claude Desktop

Claude Desktop uses the same skill format. Install to `~/.claude/skills/`:

```bash
mkdir -p ~/.claude/skills/
cp -r claude/skills/mission-control ~/.claude/skills/
```

### For Other Claude Agents

Copy `claude/skills/mission-control/SKILL.md` to your agent's skill directory. The skill includes a bundled signer script.

## Configuration

### 1. Generate Keypair

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

### 2. Register Agent

Register the agent with Mission Control (requires enroller role):

```bash
mc register claude-1 --name "Claude Agent 1" --kind thread --wip 1 --as enroller
mc rotate-key claude-1 <base64-public-key> --reason "Initial keypair"
```

### 3. Store Private Key

**Store securely** (not in git):

```bash
mkdir -p ~/.config/mc
echo "<base64-private-key>" > ~/.config/mc/private-key.txt
chmod 600 ~/.config/mc/private-key.txt
```

### 4. Set Environment Variables

Add to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):

```bash
export MC_AGENT="claude-1"
export MC_PRIVATE_KEY="$HOME/.config/mc/private-key.txt"
```

Reload:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

### 5. Install Dependencies

The signer requires the `cryptography` package:

```bash
pip install cryptography
```

## Usage

### In Claude Code

Once installed, Claude Code agents can reference the Mission Control skill in their instructions. The skill provides:

- **Authentication protocol**: mc-req-v2 Ed25519 signing
- **Available tools**: `mc_whoami`, `mc_inbox`, `mc_mine`, `mc_brief`, etc.
- **Job etiquette**: Claim before starting, log progress, submit with evidence
- **Bundled signer**: Reference implementation for request signing

The agent will use the environment variables (`MC_AGENT`, `MC_PRIVATE_KEY`) to authenticate.

### In Claude Desktop

Same as Claude Code. The skill is available to all conversations once installed in `~/.claude/skills/`.

### Manual Integration

If you need to integrate manually:

1. **Copy the bundled signer** from the skill:

```bash
# Extract the signer from SKILL.md
sed -n '/^```python$/,/^```$/p' ~/.claude/skills/mission-control/SKILL.md | sed '1d;$d' > sign_mc_request.py
chmod +x sign_mc_request.py
```

2. **Sign a request**:

```bash
AGENT_ID=$MC_AGENT
PRIVATE_KEY=$(cat $MC_PRIVATE_KEY)
BODY='{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'

python sign_mc_request.py "$AGENT_ID" "$PRIVATE_KEY" "$BODY"
```

3. **Make the request**:

```bash
curl -X POST https://api.mc.hugeai.co/mcp \
  -H "X-MC-Agent: $MC_AGENT" \
  -H "X-MC-Timestamp: ..." \
  -H "X-MC-Nonce: ..." \
  -H "X-MC-Signature: ..." \
  -H "Content-Type: application/json" \
  -d "$BODY"
```

## Testing

Test the Mission Control connection:

```bash
cd /path/to/mc-agent-kit

# Test the signer
python signer/sign_mc_request.py --test

# Test a real request (requires MC_AGENT and MC_PRIVATE_KEY set)
python signer/sign_mc_request.py \
  --agent $MC_AGENT \
  --private-key $(cat $MC_PRIVATE_KEY) \
  --body '{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
```

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `MC_AGENT` | Agent ID registered in Mission Control | `claude-1` |
| `MC_PRIVATE_KEY` | Path to file containing base64-encoded private key | `~/.config/mc/private-key.txt` |

Alternatively, store the private key directly in the environment (less secure):

```bash
export MC_AGENT="claude-1"
export MC_PRIVATE_KEY_DIRECT="<base64-private-key>"
```

Then read it in code:
```python
private_key = os.environ.get('MC_PRIVATE_KEY_DIRECT') or open(os.environ['MC_PRIVATE_KEY']).read().strip()
```

## Skill Structure

```
claude/
├── README.md                          # This file
└── skills/
    └── mission-control/
        └── SKILL.md                   # Skill with bundled signer
```

The skill file (`SKILL.md`) includes:
- **Frontmatter**: `name` and `description` for Claude to discover
- **Documentation**: What Mission Control is, authentication protocol, available tools
- **Bundled signer**: Complete Python implementation
- **Setup guide**: Keypair generation, registration, configuration
- **Job etiquette**: Rules for working with Mission Control

## Key Rotation

To rotate the agent's keypair:

1. **Generate new keypair**:
   ```bash
   python signer/sign_mc_request.py --generate
   ```

2. **Register new public key**:
   ```bash
   mc rotate-key claude-1 <new-public-key> --reason "Key rotation"
   ```

3. **Update private key file**:
   ```bash
   echo "<new-private-key>" > ~/.config/mc/private-key.txt
   ```

The old key is automatically revoked.

## Troubleshooting

### Skill Not Found

**Problem:** Claude doesn't see the Mission Control skill.

**Fix:**
- Verify the skill is in `~/.claude/skills/mission-control/SKILL.md` or `.claude/skills/mission-control/SKILL.md`
- Restart Claude Code / Claude Desktop
- Check file permissions (should be readable)

### Environment Variables Not Set

**Problem:** `MC_AGENT` or `MC_PRIVATE_KEY` not found.

**Fix:**
- Verify variables are exported: `echo $MC_AGENT`
- Reload shell profile: `source ~/.bashrc`
- Set in Claude Code / Claude Desktop settings if supported

### Private Key File Not Found

**Problem:** `No such file or directory: ~/.config/mc/private-key.txt`

**Fix:**
- Create the file: `mkdir -p ~/.config/mc && echo "<key>" > ~/.config/mc/private-key.txt`
- Verify path matches `MC_PRIVATE_KEY` variable

### 401 Unauthorized

**Problem:** Request rejected with `unauthorized` or `bad_signature`.

**Fix:**
- Verify the agent is registered: `mc agent $MC_AGENT`
- Check the public key: `mc agent $MC_AGENT --show-keys`
- Ensure private key matches registered public key
- Test signer: `python signer/sign_mc_request.py --test`

### 403 Forbidden (revoked)

**Problem:** Agent was revoked.

**Fix:** Contact Mission Control admin. The agent's access was removed.

## Security Best Practices

1. **Never commit private keys** to version control
2. **Store keys outside project directories** (e.g., `~/.config/mc/`)
3. **Set restrictive permissions** on key files (`chmod 600`)
4. **Rotate keys regularly** (every 90 days)
5. **Monitor for unauthorized access** in Mission Control logs
6. **Revoke compromised keys immediately** via `mc rotate-key`

## Integration with Other Claude Tools

The Mission Control skill can work alongside other Claude skills:
- **Slack**: Notify team when jobs are submitted
- **GitHub**: Link PRs in job submissions
- **Linear**: Cross-reference issues
- **Google Docs**: Write job briefs

The skill is self-contained and doesn't conflict with other integrations.

## Architecture

```
┌─────────────────────┐
│   Claude Agent      │
│                     │
│  ┌───────────────┐  │
│  │ Mission       │  │
│  │ Control Skill │  │
│  └───────────────┘  │
│         │           │
│  ┌──────▼────────┐  │
│  │ Bundled       │  │    HTTPS (signed)     ┌──────────────────┐
│  │ Signer        │──┼───────────────────────▶│ Mission Control  │
│  └───────────────┘  │  X-MC-Agent, X-MC-Sig │   /mcp endpoint  │
│                     │                        └──────────────────┘
│  Environment:       │
│  MC_AGENT           │
│  MC_PRIVATE_KEY     │
└─────────────────────┘
```

## Resources

- **Skill file**: `claude/skills/mission-control/SKILL.md`
- **Full contract**: `spec/CONTRACT.md` in mc-agent-kit
- **Reference signer**: `signer/sign_mc_request.py` in mc-agent-kit
- **Test suite**: `tests/` in mc-agent-kit

## Support

For questions about Mission Control integration for Claude, consult the skill documentation or contact the Mission Control team.
