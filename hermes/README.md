# Mission Control Integration for Hermes Agent

Setup guide for connecting Hermes Agent to Mission Control.

## Overview

This integration allows Hermes to:
- Authenticate with Ed25519 signed requests (mc-req-v2)
- Read job assignments via Mission Control MCP tools
- Follow job etiquette (claim, log, submit)
- Use a bundled signer script for request signing

## Installation

Hermes reads skills from `~/.hermes/skills/`. Install the Mission Control skill:

```bash
# Copy the skill to your Hermes skills directory
cp -r hermes/skills/mission-control ~/.hermes/skills/productivity/
```

Or create a symlink if you're developing:

```bash
mkdir -p ~/.hermes/skills/productivity
ln -s $(pwd)/hermes/skills/mission-control ~/.hermes/skills/productivity/mission-control
```

After installation, reload skills:

```bash
hermes
# In the CLI:
/reload-skills
```

## Configuration

### 1. Generate Keypair

Generate an Ed25519 keypair for your Hermes agent:

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
mc register hermes-1 --name "Hermes Agent 1" --kind thread --wip 1 --as enroller
mc rotate-key hermes-1 <base64-public-key> --reason "Initial keypair"
```

### 3. Store Private Key

Store the private key in a file (not in git):

```bash
mkdir -p ~/.hermes
echo "<base64-private-key>" > ~/.hermes/mc-private-key.txt
chmod 600 ~/.hermes/mc-private-key.txt
```

### 4. Set Environment Variables

Add to `~/.hermes/.env`:

```bash
# Mission Control Configuration
MC_AGENT=hermes-1
MC_PRIVATE_KEY=/home/username/.hermes/mc-private-key.txt
MC_BASE=https://api.mc.hugeai.co
```

**Note:** Hermes automatically passes these to the skill's bundled scripts when they run.

### 5. Verify Setup

Test the connection:

```bash
hermes
# In the CLI:
/mission-control

# Then ask:
"Check my Mission Control identity"
```

The agent should call `mc_whoami` and return your agent details.

## Usage

### In Hermes CLI

Start a conversation and invoke the skill:

```bash
hermes

# Load the skill
/mission-control

# Check inbox
"What's in my Mission Control inbox?"

# Claim and start work
"Claim job-123 and show me the brief"

# Log progress
"Log to job-123: tests passing, PR open"

# Submit work
"Submit job-123 with evidence: PR link, tests passed, CI green"
```

### Skill Commands

The Mission Control skill is available as `/mission-control` and provides:

- **Check inbox**: `mc_inbox` — Jobs assigned or ready to claim
- **Check mine**: `mc_mine` — Jobs you currently hold
- **Get brief**: `mc_brief <job>` — Full context for a job
- **Check priorities**: `mc_priorities` — Goal weights and limits
- **Identity**: `mc_whoami` — Your agent identity

**Write operations** require the Mission Control CLI:
- `mc claim <job>` — Claim before starting
- `mc log <job> "message"` — Log progress
- `mc submit <job> --evidence "..."` — Submit work
- `mc comment <job> "message"` — Add comment
- `mc wait <job> --on <decider> --question "..."` — Request approval

## Job Workflow

### 1. Check Inbox

```bash
"Check my Mission Control inbox"
```

The agent runs `mc_inbox` and shows assigned jobs.

### 2. Claim Work

```bash
"Claim job-123"
```

The agent runs `mc claim job-123` via the CLI.

### 3. Read Brief

```bash
"Show me the brief for job-123"
```

The agent runs `mc_brief job-123` and displays requirements.

### 4. Work on Task

Follow the done-when conditions. The agent can help with research, coding, testing, etc.

### 5. Log Progress

```bash
"Log to job-123: implemented feature, tests passing"
```

The agent runs `mc log job-123 "implemented feature, tests passing"`.

### 6. Request Approval (if needed)

For risky operations:

```bash
"Request approval from supervisor to deploy job-123 to production"
```

The agent runs `mc wait job-123 --on supervisor --question "Deploy to production?"`.

### 7. Submit Work

```bash
"Submit job-123 with evidence: PR at https://github.com/org/repo/pull/42, vitest 18 passed, CI green"
```

The agent runs `mc submit job-123 --evidence "..."`.

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `MC_AGENT` | Agent ID registered in Mission Control | `hermes-1` |
| `MC_PRIVATE_KEY` | Path to file containing base64-encoded private key | `~/.hermes/mc-private-key.txt` |
| `MC_BASE` | Mission Control API base URL | `https://api.mc.hugeai.co` |

These are read by the bundled signer script (`scripts/sign_mc_request.py`) when making signed requests.

## Bundled Signer

The skill includes `scripts/sign_mc_request.py` for signing requests. It's automatically available to the skill and reads configuration from environment variables.

**Test the signer:**

```bash
cd ~/.hermes/skills/productivity/mission-control
python scripts/sign_mc_request.py --test
```

**Generate a keypair:**

```bash
python scripts/sign_mc_request.py --generate
```

## Key Rotation

To rotate the agent's keypair:

1. **Generate new keypair**:
   ```bash
   python scripts/sign_mc_request.py --generate
   ```

2. **Register new public key**:
   ```bash
   mc rotate-key hermes-1 <new-public-key> --reason "Key rotation"
   ```

3. **Update private key file**:
   ```bash
   echo "<new-private-key>" > ~/.hermes/mc-private-key.txt
   ```

The old key is automatically revoked.

## Troubleshooting

### Skill Not Found

**Problem:** `/mission-control` not recognized.

**Fix:**
- Verify skill is in `~/.hermes/skills/productivity/mission-control/SKILL.md`
- Reload skills: `/reload-skills` in the CLI
- Check file permissions (should be readable)

### Environment Variables Not Set

**Problem:** Signer fails with "MC_AGENT not set".

**Fix:**
- Verify `~/.hermes/.env` contains `MC_AGENT` and `MC_PRIVATE_KEY`
- Restart Hermes to reload environment: `hermes` (fresh session)

### Private Key File Not Found

**Problem:** "No such file or directory: ~/.hermes/mc-private-key.txt"

**Fix:**
- Create the file: `echo "<key>" > ~/.hermes/mc-private-key.txt`
- Verify path matches `MC_PRIVATE_KEY` in `.env`
- Use absolute path, not `~` shorthand, in `.env`

### 401 Unauthorized

**Problem:** Request rejected with `bad_signature` or `unauthorized`.

**Fix:**
- Verify agent is registered: `mc agent hermes-1`
- Check public key: `mc agent hermes-1 --show-keys`
- Ensure private key matches registered public key
- Test signer: `python scripts/sign_mc_request.py --test`

### 403 Forbidden (revoked)

**Problem:** Agent was revoked.

**Fix:** Contact Mission Control admin. The agent's access was removed.

## Security Best Practices

1. **Never commit private keys** to version control
2. **Store keys outside project directories** (e.g., `~/.hermes/`)
3. **Set restrictive permissions** on key files (`chmod 600`)
4. **Rotate keys regularly** (every 90 days)
5. **Monitor for unauthorized access** in Mission Control logs
6. **Revoke compromised keys immediately** via `mc rotate-key`

## Architecture

```
┌─────────────────────┐
│   Hermes Agent      │
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
│  MC_BASE            │
└─────────────────────┘
```

## Resources

- **Skill file**: `~/.hermes/skills/productivity/mission-control/SKILL.md`
- **Bundled signer**: `~/.hermes/skills/productivity/mission-control/scripts/sign_mc_request.py`
- **Full contract**: https://github.com/hugeai-inc/mc-agent-kit/blob/main/spec/CONTRACT.md
- **Test suite**: Run `pytest tests/` in mc-agent-kit to verify the signer

## Support

For questions about Mission Control integration for Hermes, consult the skill documentation or contact the Mission Control team.
