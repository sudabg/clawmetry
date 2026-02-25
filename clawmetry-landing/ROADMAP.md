# ClawMetry Roadmap

> Vision: The operating system for AI agents. Not just a dashboard -- full observability, governance, and control.

---

## Now (shipped)
- Real-time dashboard: active sessions, memory browser, cron jobs
- Live packet flow: every tool call, URL fetched, search query
- Token cost tracking with budget alerts
- Sub-agent spawn monitoring
- Narrative view: step-by-step agent log
- PyPI install: `pip install clawmetry`
- Traction page with live metrics

---

## Next (high priority)

### Circuit Breakers
Inspired by: production agent ops research (Salesforce Agentforce, Air Canada case studies)

Pre-defined stop conditions that auto-pause or kill an agent:
- Spend cap: "max $X for this task" -- kills run if exceeded
- Iteration limit: stop after N steps
- Time limit: kill if running longer than X minutes
- User configurable per-session or globally

ClawMetry already has the token data to power this. One feature add, extremely high value.

### Structured Alert Rules Engine
Inspired by: OpenAlerts (steadwing/openalerts)

Replace simple token alerts with a proper configurable rules system:
- `agent-stuck`: agent idle too long (configurable threshold, default 120s)
- `high-error-rate`: failure % over last N calls (default 50% over 20 calls)
- `step-limit-warning`: alert at 80% of max_steps
- `queue-depth`: queued items piling up (default >10)
- `llm-errors`: LLM failures in 1-min window
- `tool-errors`: tool execution failures
- `gateway-down`: no heartbeat received (default 30s)
- `heartbeat-fail`: consecutive heartbeat failures (default 3)

Each rule: configurable threshold, cooldown, enable/disable. Global `max_alerts_per_hour`.

### LLM-Enriched Alerts
Inspired by: OpenAlerts

When an alert fires, use the configured LLM to generate:
- Plain English summary: "Your API key is invalid or expired"
- Actionable fix: "Update your key at platform.openai.com/api-keys"

Raw error codes are useless. This makes alerts actually helpful.

### Exit Criteria (Agent Watchdog)
Inspired by: LinkedIn post on agent ops

Automatic kill conditions:
- Performance floor: kill if success rate drops below X%
- Cost ceiling: kill if spend exceeds threshold
- Incident trigger: kill on N consecutive errors
- Idle timeout: kill if no activity for X minutes

Pairs with Circuit Breakers but fires automatically without user-set caps.

---

## Soon (medium priority)

### Scorecards -- Weekly/Daily Agent Reports
Inspired by: agent ops framework (fixed cadence performance review)

Automated report delivered via Telegram or email:
- "This week: 47 crons ran, $12.40 spent, 2 failures, 3 sub-agents spawned"
- Compare to last week
- Highlight anomalies

Cadence: daily digest + weekly summary. Cron-powered.

### Escalation Protocols (Human-in-the-Loop)
Inspired by: agent ops framework + already on Vivek's roadmap

Confidence-based escalation -- agent pauses and asks before acting when:
- Confidence is low (novelty-based: task outside known patterns)
- Domain-based: external actions (send email, make payment, post publicly)
- User-defined: specific tool calls always require approval

Like Plotcode's approval flow -- agent presents intent, human approves/denies, optionally "approve all future".

### /health Zero-Token Command
Inspired by: OpenAlerts

Telegram command returning live health snapshot without burning LLM tokens:
- Uptime, active sessions, alert history, last cron run
- No LLM involved -- pure gateway response
- `clawmetry /health` in any connected channel

### Debug Tab
Inspired by: OpenAlerts dashboard

State snapshot for troubleshooting:
- Last known agent state
- Last N events
- Current session variables and memory state
- Useful when agent is stuck or behaving unexpectedly

### Persistent Server Mode
Inspired by: OpenAlerts standalone mode

`clawmetry serve` -- persistent dashboard that survives agent restarts:
- Events written to disk (JSONL), dashboard reads from there
- History preserved across restarts
- Useful for long-running agent setups

---

## Later (lower priority / bigger lifts)

### Mac App + iOS/Android
Native apps for mobile monitoring -- see your agent from anywhere.

### Managed Cloud Hosting
Run ClawMetry without self-hosting. Vivek hosts it, users just connect.

### Multi-Gateway Support
Monitor 10 agents from one dashboard. Fleet view with health status per gateway.

### Access Controls + Audit Trails
Inspired by: agent ops framework

- Least-privilege per agent (which tools can each agent use?)
- Unique identity per agent
- Full audit trail: who did what, when
- Critical for enterprise / team deployments

### Slack / Discord / Webhook Delivery
Inspired by: OpenAlerts channels

Alert delivery beyond Telegram:
- Slack webhook
- Discord webhook
- Generic webhook (any URL)
- Configurable via env vars: `CLAWMETRY_SLACK_WEBHOOK_URL=...`

---

## Positioning

**OpenAlerts** went narrow: alerts only, thin layer.
**ClawMetry** goes broad: full observability + governance + control.

Not just a dashboard. An **operating system for AI agents.**

---

## Sources / Inspiration
- [OpenAlerts](https://github.com/steadwing/openalerts) -- alert rules, LLM enrichment, /health command, standalone mode
- [Pranav Pathak LinkedIn](https://www.linkedin.com/posts/pranavmpathak_everyone-deploying-ai-agents-is-about-to-activity-7432303358905888769-Lz_0) -- circuit breakers, scorecards, escalation protocols, exit criteria, access controls
- Vivek's YC demo + product vision -- governance layer, mobile apps, managed cloud
