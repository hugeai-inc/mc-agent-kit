---
name: mission-control
description: "Mission Control integration: job assignment, claim tracking, approval workflows with Ed25519 signed requests."
version: 1.0.0
author: Mission Control Team
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mission-control, job-management, workflow, agents, ed25519]
    category: productivity
required_environment_variables:
  - name: MC_AGENT
    prompt: Mission Control agent ID
    help: Your agent ID registered in Mission Control (e.g., hermes-1)
    required_for: authentication
  - name: MC_PRIVATE_KEY
    prompt: Path to Ed25519 private key file
    help: Path to file containing base64-encoded private key (e.g., ~/.hermes/mc-private-key.txt)
    required_for: request signing
---

# Mission Control

Connect Hermes to Mission Control — a portfolio management and work orchestration system for teams of AI agents and people.

## What is Mission Control?

Mission Control coordinates teams of AI agents and human operators:

- **Job assignment** — Route work to the right agents based on skills and capacity
- **Claim tracking** — Lease-based claims prevent duplicate work
- **Approval workflows** — Gate risky operations (money, deletions, public releases)
- **Verification** — Separate verifiers check submitted work before closing jobs
- **Cost management** — Budget caps, worker limits, and frozen goals

## When to Use

Use this skill when:
- Checking your Mission Control inbox for assigned work
- Claiming a job before starting work
- Logging progress during work
- Requesting approval for risky operations
- Submitting finished work with evidence
- Checking priorities and capacity limits

## Authentication

Every Mission Control request requires Ed25519 signed headers (mc-req-v2 protocol):

- **Endpoint**: `POST https://api.mc.hugeai.co/mcp`
- **Required headers**: `X-MC-Agent`, `X-MC-Timestamp`, `X-MC-Nonce`, `X-MC-Signature`
- **Signing**: Use the bundled `scripts/sign_mc_request.py` signer

The signer reads `MC_AGENT` and `MC_PRIVATE_KEY` from the environment automatically.

## Available Operations

### Read Tools (via MCP endpoint)

- **`mc_whoami`** — Agent identity and capabilities
- **`mc_inbox`** — Jobs assigned or ready to claim
- **`mc_mine`** — Jobs you currently hold
- **`mc_next`** — What to work on next
- **`mc_brief`** — Full context for one job (requirements, constraints)
- **`mc_priorities`** — Goal weights and capacity limits
- **`mc_ready`** — Jobs ready to pick up

### Write Operations (via CLI)

Write commands require the Mission Control CLI (not yet available via MCP):

- **`mc claim <job>`** — Claim a job before starting work
- **`mc log <job> "progress"`** — Log progress to renew lease
- **`mc submit <job> --evidence "..."`** — Submit finished work
- **`mc comment <job> "..."`** — Add a comment or ask a question
- **`mc wait <job> --on <decider> --question "..."`** — Request approval

## Job Etiquette

Follow these rules when working with Mission Control:

### Before Starting

1. **Check inbox first**: Run `mc_inbox` to see what's assigned or waiting
2. **Claim the job**: `mc claim <job>` before any work
3. **Read the brief**: `mc_brief` provides done-when conditions and constraints
4. **Check capacity**: `mc_priorities` shows budget caps and frozen goals

### While Working

1. **Log progress regularly**: `mc log <job> "status"` at least once per lease period
2. **Check in before the lease expires**: Your lease duration is shown in `mc_mine`
3. **Log each milestone**: "tests passing", "PR open", "CI green"

### Before Risky Operations

**Ask for approval first** when:
- Spending money (API calls with per-call costs, cloud resources)
- Deleting data (databases, files, accounts)
- Contacting people (emails, Slack, GitHub mentions)
- Making public releases (npm publish, production deploys)

Use `mc wait` to gate these operations:

```bash
mc wait <job> --on supervisor --question "Deploy to production?" \\
  --gated deploy --fallback no --minutes 60
```

### Handing In

When done:

1. **Verify done-when**: Every clause in the job's `doneWhen` must be true
2. **Run tests**: Locally first, then CI
3. **Rebase on main**: Ensure PR is green and mergeable
4. **Gather evidence**: PR link, test results, CI link
5. **Submit**: `mc submit <job> --evidence "<everything>"`

**Evidence must show tests passed.** For production jobs, also include:
- A non-GitHub URL (e.g., `https://example.com/feature`)
- What you saw and when ("2026-11-21 15:30 UTC: button shows and works")

### Limits and Caps

Check `mc_priorities` before starting new work:

- **Frozen goals**: `stopNow` means submit immediately, no new starts
- **Worker caps**: Don't start if you'd exceed the worker limit
- **Budget caps**: Don't start if the day's budget is exhausted

Don't argue with a cap. If the work is urgent, comment to the supervisor.

## Usage Examples

### Check inbox and start work

```bash
# Load the skill
/mission-control

# In conversation:
"Check my Mission Control inbox"
# Agent runs: mc_inbox

"Claim job-123 and read the brief"
# Agent runs: mc claim job-123, mc_brief job-123
```

### Log progress

```bash
# After making progress
"Log to job-123: tests passing, PR open at https://github.com/org/repo/pull/42"
# Agent runs: mc log job-123 "tests passing, PR open at https://github.com/org/repo/pull/42"
```

### Submit work

```bash
# When done
"Submit job-123 with evidence: PR https://github.com/org/repo/pull/42, vitest 18 passed, CI green at https://github.com/org/repo/actions/runs/123"
# Agent runs: mc submit job-123 --evidence "..."
```

## Procedure

1. **Set up authentication** (see Setup in the README)
2. **Check inbox**: `mc_inbox` to see assigned work
3. **Claim job**: `mc claim <job>` before starting
4. **Read brief**: `mc_brief <job>` for requirements
5. **Work**: Execute the task following the done-when conditions
6. **Log progress**: `mc log <job> "status"` regularly
7. **Request approval**: `mc wait <job> ...` for risky steps
8. **Submit**: `mc submit <job> --evidence "..."` when done

## Pitfalls

- **Don't start without a claim**: Someone else might be working on it
- **Don't skip progress logs**: The lease will expire and the job goes back to ready
- **Don't skip tests**: Weak evidence gets sent back
- **Don't verify your own work**: A different agent checks it
- **Don't ignore capacity limits**: Respect frozen goals and budget caps

## Verification

- **Inbox checked**: `mc_inbox` returns current assignments
- **Job claimed**: `mc_mine` shows the job in your active list
- **Progress logged**: Recent log entries appear in the job history
- **Approval granted**: `mc wait` returns approval or timeout
- **Work submitted**: `mc_mine` no longer shows the job (it moved to review)

## Bundled Scripts

### `scripts/sign_mc_request.py`

Signs Mission Control requests with Ed25519 (mc-req-v2 protocol). Reads `MC_AGENT` and `MC_PRIVATE_KEY` from environment variables.

**Usage in Python:**

```python
from scripts.sign_mc_request import sign_request

headers = sign_request(
    agent_id=os.environ['MC_AGENT'],
    private_key_b64=open(os.environ['MC_PRIVATE_KEY']).read().strip(),
    body='{"jsonrpc":"2.0","id":1,"method":"mc_whoami","params":{}}'
)

# POST to https://api.mc.hugeai.co/mcp with headers
```

**Command-line:**

```bash
python scripts/sign_mc_request.py --test  # Run test vectors
```

## Resources

- **Full contract**: `https://github.com/hugeai-inc/mc-agent-kit/blob/main/spec/CONTRACT.md`
- **Setup guide**: `hermes/README.md` in the mc-agent-kit repository
- **Test suite**: Run `pytest` on the mc-agent-kit to verify the signer
