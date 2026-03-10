# Changelog

## v0.9.21 — 2026-03-10

**CPU + RAM Sparklines in System Health Panel**

- **📊 CPU sparkline**: Real-time line chart (last 60 readings at 10s intervals) embedded in the System Health panel — colour-coded green/amber/red by load threshold
- **🧠 RAM sparkline**: Matching sparkline for memory usage alongside the existing progress bar
- **🌡 CPU temperature**: Badge showing current core temperature (sourced from `coretemp` / `k10temp` / `acpitz`), colour-coded vs. `high` and `critical` thresholds
- **🖥 Per-core pills**: Row of small badges showing per-core CPU %, amber/indigo by load
- **🌐 Network I/O panel**: New section showing real-time receive/transmit rates (B/s → KB/s → MB/s auto-scaling), derived from `net_io_counters()` delta between samples
- **Backend ring buffer**: New `_cpu_ram_poll_loop()` daemon thread samples CPU/RAM/temp/net every 10 s and stores last 60 readings in `_cpu_ram_history` deque — zero cost when nobody is watching
- **New endpoint**: `GET /api/system-health/sparklines` — lightweight payload returning only the ring buffer (for future polling without full health reload)
- **Refresh rate**: System Health panel now refreshes every 10 s (was 30 s) to keep sparklines live
- Closes [#70](https://github.com/vivekchand/clawmetry/issues/70)

## v0.9.20 — 2026-03-10

**Keyboard Shortcuts for Power Users**

- **⌨️ Tab switching via number keys**: Press `1`–`8` to jump to any tab (Overview, Flow, Crons, Tokens, Memory, Main Agent, Sub Agents, Transcripts) — no mouse needed
- **`r` to refresh**: Triggers reload for the current tab (equivalent to clicking the refresh button)
- **`/` to focus search**: Jumps focus to the nearest search or filter input on the current tab
- **`Esc` to close modals**: Closes any open modal, panel, or overlay in priority order (comp modal → task modal → budget modal → cron edit → help overlay → snapshot modal)
- **`?` help overlay**: Shows/hides a quick-reference keyboard shortcuts cheat sheet — also accessible via the `?` button in the header toolbar
- Shortcuts are automatically disabled when the cursor is inside any input, textarea, or contenteditable element
- Refactored `switchTab()` to use `_activateTab()` helper — no longer depends on `event.target`, enabling programmatic tab switching from keyboard handlers
- Closes [#73](https://github.com/vivekchand/clawmetry/issues/73)

## v0.9.17 — 2026-03-03

**Alert Channel Integrations + Agent Condition Checks**

- **📣 Alert Integrations**: New Integrations tab in Alerts/Budget modal — add Slack (Incoming Webhook), Discord (Webhook), PagerDuty (Events API v2), OpsGenie (REST API), or any generic webhook as alert destinations
- **🧪 Test Channels**: Send a test alert to any configured channel directly from the UI
- **🤫 Agent Silent Detection**: New `_check_agent_silent()` — alerts when your agent goes quiet for >10 min
- **📉 Error Rate Spike**: New `_check_error_rate_spike()` — detects when tool call error rate exceeds 30% in a 60-minute window
- **⚡ Token Anomaly Detection**: New `_check_token_anomaly()` — catches runaway loops when current hourly token rate is 3× above 24h average
- **🔌 Alert Dispatch**: All fired alerts now automatically fan out to all configured integration channels (Slack, Discord, PagerDuty, OpsGenie)
- **DB**: Added `alert_channels` and `agent_alert_rules` tables to the budget SQLite store
- **Landing**: Restructured traction.html — moved ClickHouse analytics iframe to top of page, cleaned up PyPI metric cards

## v0.2.8 — 2026-02-12

- UX: removed dashboard login/logout flow and related token-auth UI to avoid confusion
- DX: enabled auto-reload by default for local development
- CLI: added `--no-debug` to run without auto-reload
- Docs: removed token-login instructions and updated security guidance

## v0.2.7 — 2026-02-12

- Security: changed default bind host to `127.0.0.1` (localhost only)
- Security: added optional token auth (`--auth-token` / `OPENCLAW_DASHBOARD_TOKEN`) for UI, API, and OTLP endpoints
- Security: added built-in token login UI for browser access when auth is enabled
- UX/Security: added dashboard Logout button + `/auth/logout` endpoint to clear auth cookie and browser session state
- Security: added startup warnings when binding to non-local hosts without auth
- Reliability: added SSE guardrails (max stream duration and max concurrent stream clients)
- Docs: added security and auth guidance in README

## v0.2.6 — 2026-02-10

**Major Features & Polish Release**

- **🧠 Automation Advisor**: Self-writing skills with pattern detection engine
- **💰 Cost Optimizer**: Real-time cost tracking with local model fallback recommendations  
- **🕰️ Time Travel**: Historical component data scrubbing with visual timeline
- **📚 Skill Templates Library**: Complete automation templates for rapid development
- **🔧 Enhanced Error Handling**: Production-ready error recovery and graceful degradation
- **✅ Startup Validation**: New user onboarding with configuration checks
- **🚀 Performance**: Server-side caching, client prefetch, optimized modal loading
- **📖 Documentation**: Comprehensive skill template library and BUILD_STATUS tracking

**Quality Improvements**

- Enhanced error handling with specific exception types and recovery mechanisms
- Automatic backup of corrupted metrics files before attempting fixes
- Better disk space detection and helpful error messages
- Startup configuration validation for new open-source users
- Modal data cross-contamination fixes with proper cleanup
- Repository sync and version bump maintenance

## v0.2.5 — 2026-02-08

- Fix: Flask threaded mode (Sessions/Memory tabs loading)
- Fix: Log file detection (openclaw-* prefix support)
- Fix: Flow SVG duplicate filter ID conflict
- Fix: Flow Live Activity Feed event patterns
- Fix: Task card → transcript modal wiring
- Improvement: Better log format parsing for new OpenClaw versions

## v0.2.4

- Initial tracked release
