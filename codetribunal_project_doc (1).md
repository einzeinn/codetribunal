# CodeTribunal — Project Documentation
> Multi-agent adversarial code review system · Qwen Cloud Global AI Hackathon · Track 3: Agent Society

---

## 1. Concept Overview

**Tagline:** *"Where every line of code faces justice"*

CodeTribunal adalah sistem review code berbasis multi-agent yang menggunakan metafora **courtroom/pengadilan medieval**. Alih-alih satu AI yang review code secara linear, CodeTribunal mensimulasikan proses persidangan dimana setiap agent memiliki peran dan perspektif yang berbeda, saling berargumen, dan reach consensus melalui structured debate.

### Core Idea
- Code yang disubmit = **Terdakwa**
- Agent-agent = **Officers of the court** dengan role berbeda
- Output = **Verdict** berupa structured review report

### Why This Wins Track 3
Track 3 (Agent Society) requires:
- ✅ Multiple agents dengan distinct capabilities
- ✅ Task division & role assignment
- ✅ Dialogue, disagreement & negotiation antar agent
- ✅ Measurable efficiency gain vs single-agent baseline
- ✅ Conflict resolution mechanism

---

## 2. Agent Architecture

### The Five Officers of the Court

| Agent | Role | Responsibility | Personality |
|-------|------|----------------|-------------|
| **AEGIS** | Prosecutor | Hunt security vulnerabilities, attack code weaknesses | Aggressive, adversarial |
| **ARBITER** | Judge / Orchestrator | Manage debate flow, resolve conflicts, issue final verdict | Neutral, authoritative |
| **AXIOM** | Defense | Defend valid code choices, provide context & counter-arguments | Analytical, protective |
| **METRIC** | Expert Witness | Provide performance data, complexity analysis, benchmarks | Data-driven, objective |
| **LEDGER** | Clerk | Record all proceedings, compile final report | Systematic, comprehensive |

### Agent Interaction Protocol

```
[User uploads code]
        ↓
LEDGER: Parse & index code → create case file
        ↓
AEGIS: Opening statement → identify vulnerabilities
        ↓
AXIOM: Counter-arguments → defend code decisions
        ↓
METRIC: Present evidence → performance & complexity data
        ↓
ARBITER: Facilitate debate rounds (max 3 rounds)
   ├── Sustain / Overrule objections
   ├── Request clarification from agents
   └── Convergence check
        ↓
ARBITER: Deliberate → issue Final Verdict
        ↓
LEDGER: Compile structured report
```

### Debate Protocol Rules
1. **Opening Round** — AEGIS presents all findings, AXIOM responds
2. **Evidence Round** — METRIC presents data, agents cross-examine
3. **Closing Round** — Both sides summarize, ARBITER deliberates
4. **Verdict** — ARBITER issues ruling with confidence scores
5. **Max rounds:** 3 (prevent infinite loops)
6. **Consensus mechanism:** Majority confidence score > 0.7 triggers early verdict

---

## 3. User Experience Flow

### Onboarding Flow (4 Steps)

```
Step 1: HERO
  └── Courthouse gate visual (vector SVG)
  └── Tagline + "Approach the Gates" CTA

Step 2: GUARD DIALOGUE
  └── Guard character blocks entrance
  └── Dialogue: "Present your case scroll"
  └── Narrative onboarding — feels like entering a real courthouse

Step 3: CASE FILING SCROLL
  └── Medieval scroll aesthetic form
  └── Fields:
      - Case Title (e.g. "The People vs. auth_middleware.py")
      - Source Code Upload (drag & drop, any language)
      - Concern / Focus Area (optional)
  └── CTA: "Bring this case to trial"

Step 4: COURT IS IN SESSION
  └── Transition screen
  └── "The tribunal has received your case. Agents convening..."
  └── Redirect to Main Courtroom UI
```

### Main Courtroom UI

```
┌─────────────────────────────────────────────────────┐
│                  ⚖ CODE TRIBUNAL                    │
│         Case File: auth_middleware.py · 247 lines    │
├──────────────────────────────────────────────────────┤
│  [AEGIS]    [ARBITER]   [AXIOM]   [METRIC]  [LEDGER] │
│  Speaking   Presiding  Objecting  Standby  Recording │
├────────────────────────────┬─────────────────────────┤
│   LIVE PROCEEDINGS         │   QUEST LOG             │
│   ─────────────────        │   ✓ Security scan       │
│   AEGIS [Opening]          │   ✓ Performance check   │
│   "line 89 stores JWT..."  │   ○ Maintainability     │
│                            │   ○ Recommendations     │
│   AXIOM [Objection]        │   ─────────────────     │
│   "CSP headers mitigate.." │   CURRENT OBJECTIVE     │
│                            │   Uncover security      │
│   METRIC [Evidence]        │   risks in auth flow    │
│   "O(n) loop, ~840ms..."   ├─────────────────────────┤
│                            │   REWARD                │
│   ARBITER [Sustained]      │   A fair & just verdict │
│   "Document the CSP dep.." │                         │
├────────────────────────────┴─────────────────────────┤
│  TRIBUNAL ASSESSMENT                                  │
│  Security [████░░] 6.2  Performance [███░░] 4.5      │
│  Maintainability [█████░] 7.8                        │
│                          [Request Final Verdict ⚖]   │
└──────────────────────────────────────────────────────┘
```

### UI Aesthetic
- **Theme:** Dark medieval / parchment RPG courtroom
- **Fonts:** Cinzel (headers/titles) + IM Fell English (body)
- **Color palette:** Deep black `#0f0c05`, gold `#d4a843`, parchment `#e8d9b0`, muted `#9a7f4a`
- **Icons/Characters:** Vector SVG (no external images)
- **Animations:** Streaming debate feed, live score bars, status badges

---

## 4. Tech Stack

### Backend
```
Language:     Python 3.11+
Framework:    FastAPI
Agent SDK:    Qwen Cloud API (qwen-max / qwen-plus / qwen-turbo)
Orchestration: Custom debate loop (no heavy framework needed)
WebSocket:    FastAPI WebSocket (real-time debate streaming)
Deployment:   Alibaba Cloud ECS (ecs.t6 burstable, Docker + Uvicorn)
```

### Frontend
```
Framework:    Next.js 14 (App Router)
Styling:      Tailwind CSS
Fonts:        Google Fonts (Cinzel, IM Fell English)
Icons:        Custom SVG vectors
Real-time:    WebSocket client (native browser API)
Deployment:   Vercel
```

### Storage
```
Database:     Supabase (PostgreSQL)
Tables:
  - cases (id, title, code_content, language, concern, status, created_at)
  - proceedings (id, case_id, agent, tag, message, round, timestamp)
  - verdicts (id, case_id, security_score, performance_score, maintainability_score, summary, recommendations, created_at)
```

### AI / Models
```
ARBITER:  qwen-max   — complex orchestration & final verdict
AEGIS:    qwen-max   — adversarial reasoning, sharp attack
AXIOM:    qwen-plus  — counter-argument, lighter reasoning
METRIC:   qwen-plus  — data analysis & complexity
LEDGER:   qwen-turbo — parsing & recording only
```

### Architecture Diagram

```
[User Browser]
     │
     ├── HTTP → [Next.js Frontend / Vercel]
     │              │
     │              └── WebSocket ──────────────────────┐
     │                                                  │
     └── REST API → [FastAPI Backend / Alibaba Cloud]   │
                         │                              │
                         ├── [LEDGER Agent]             │
                         │    └── qwen-turbo            │
                         │                              │
                         ├── [AEGIS Agent]              │
                         │    └── qwen-max              │
                         │                              │
                         ├── [AXIOM Agent]              │
                         │    └── qwen-plus             │
                         │                              │
                         ├── [METRIC Agent]             │
                         │    └── qwen-plus             │
                         │                              │
                         ├── [ARBITER Agent]            │
                         │    └── qwen-max              │
                         │    └── Orchestrates debate   │
                         │    └── Streams via WS ───────┘
                         │
                         └── [Supabase]
                              └── Store cases, proceedings, verdicts
```

---

## 4b. Alibaba Cloud Cost Breakdown & Budget Calculation

### Coupon Details
- **Voucher ID:** 501017630130494
- **Face Value:** $40.00 · **Balance:** $40.00
- **Expiry:** 2026-08-09
- **Applicable:** Prepaid general, Pay-as-you-go Bill, Purchase, RENEW, Trial, Upgrade, Exchange, BANDWIDTH_REMEDY, dll

### Order Types yang Akan Dipakai

| Order Type | Dipakai Untuk | Estimasi Cost |
|------------|---------------|---------------|
| **Pay-as-you-go Bill** | ECS instance per jam | ~$10.92 |
| **Pay-as-you-go Bill** | Qwen API calls per token | ~$2.60 |
| **BANDWIDTH_REMEDY** | Network egress / bandwidth | ~$1.00 |
| **Trial** | Dev & testing phase | $0.00 (70M free tokens) |
| **Purchase / RENEW** | ECS setup & perpanjang | $0.00 (dalam periode) |

### Kalkulasi Detail

#### 1. ECS Instance (Pay-as-you-go Bill)
```
Instance type : ecs.t6 burstable (2 vCPU, 4GB RAM)
Rate estimate : ~$0.03/hour (Singapore region)

Estimasi jam aktif:
  Dev phase    : 14 hari × 8 jam   = 112 jam
  Staging      : 7 hari  × 12 jam  = 84 jam
  Demo/judging : 7 hari  × 24 jam  = 168 jam (always on)
  Total        : ~364 jam

ECS cost      : 364 × $0.03 = ~$10.92
Bandwidth     : ~$1.00
──────────────────────────────────────
Subtotal ECS  : ~$11.92
```

#### 2. Qwen API Calls (Pay-as-you-go Bill)

Pricing aktual per Juni 2026:
```
qwen-max   : $1.04/M input · $4.16/M output tokens
qwen-plus  : $0.26/M input · $0.78/M output tokens
qwen-turbo : $0.033/M input · $0.13/M output tokens
```

Estimasi per 1 sesi tribunal (~200 lines code, 3 debate rounds):

| Agent | Model | Input | Output | Cost/sesi |
|-------|-------|-------|--------|-----------|
| LEDGER | qwen-turbo | 1,500 tok | 300 tok | ~$0.00009 |
| AEGIS | qwen-max | 3,000 tok | 1,500 tok | ~$0.0093 |
| AXIOM | qwen-plus | 3,000 tok | 1,500 tok | ~$0.0020 |
| METRIC | qwen-plus | 2,500 tok | 1,000 tok | ~$0.0014 |
| ARBITER | qwen-max | 5,000 tok | 2,000 tok | ~$0.0135 |
| **Total** | | **~15K tok** | **~6.3K tok** | **~$0.026/sesi** |

```
Budget Qwen  : $40 - $11.92 = $28.08 tersedia
Sesi mungkin : $28.08 ÷ $0.026 = ~1,080 sesi ✅

Untuk hackathon (~50-100 sesi demo + judging): SANGAT AMAN
```

#### 3. Free Trial Tokens (Trial order type)
```
New Alibaba Cloud account: 70M token trial (1M/model, valid 90 hari)
Estimasi token dev phase : ~5-10M tokens
→ Seluruh dev & testing phase praktis GRATIS dari trial
→ $40 voucher murni untuk production & ECS
```

### Budget Summary

| Komponen | Order Type | Cost |
|----------|-----------|------|
| ECS instance (364 jam) | Pay-as-you-go | ~$10.92 |
| Network bandwidth | BANDWIDTH_REMEDY | ~$1.00 |
| Qwen API dev/testing | Trial (70M free) | $0.00 |
| Qwen API production (~100 sesi) | Pay-as-you-go | ~$2.60 |
| Buffer / unexpected | Exchange/Other | ~$5.00 |
| **Total estimasi pakai** | | **~$19.52** |
| **Sisa voucher** | | **~$20.48** |

> ✅ **Kesimpulan: $40 lebih dari cukup. Estimasi pakai ~$19.52, sisa ~$20 sebagai buffer.**

---

## 5. Feature List (MVP for Hackathon)

### Must Have (P0)
- [ ] Hero / onboarding flow (4 steps)
- [ ] Code file upload (any language)
- [ ] 5-agent debate system (AEGIS, ARBITER, AXIOM, METRIC, LEDGER)
- [ ] Real-time streaming debate feed via WebSocket
- [ ] Structured verdict output (scores + recommendations)
- [ ] Alibaba Cloud deployment (backend)
- [ ] Architecture diagram

### Should Have (P1)
- [ ] Multi-language support (Python, JS, Go, Java, etc.)
- [ ] Debate round indicator (Round 1/2/3)
- [ ] Download verdict as PDF
- [ ] Session history (past cases)
- [ ] Quest Log auto-update during proceedings

### Nice to Have (P2)
- [ ] Paste code directly (no file upload)
- [ ] GitHub repo URL input
- [ ] Single-agent baseline comparison (for measurable efficiency metric)
- [ ] Share verdict URL

---

## 6. Judging Criteria Mapping

| Criteria | Weight | How CodeTribunal Addresses It |
|----------|--------|-------------------------------|
| Technical Depth & Engineering | 30% | Custom multi-agent debate protocol, WebSocket streaming, Qwen Cloud API integration with role-based prompting |
| Innovation & AI Creativity | 30% | Adversarial agent architecture (prosecutor vs defense), courtroom metaphor as UX paradigm, structured conflict resolution |
| Problem Value & Impact | 25% | Real dev pain point (code review is slow & inconsistent), multi-perspective review catches more issues than single reviewer |
| Presentation & Documentation | 15% | Medieval RPG UI makes demo visually compelling, architecture diagram, clear README |

---

## 7. Measurable Efficiency Metric (Track 3 Requirement)

### Baseline vs CodeTribunal Comparison

| Metric | Single Agent | CodeTribunal (5 agents) |
|--------|-------------|------------------------|
| Issue categories covered | 1-2 | 3+ (security, perf, maintainability) |
| False positive rate | Higher (no counter-argument) | Lower (defense agent filters) |
| Coverage depth | Shallow | Deep (adversarial pressure) |
| Structured output | Inconsistent | Standardized verdict format |

> **Demo script:** Run same code through single qwen-max call vs full tribunal. Show side-by-side output diff.

---

## 8. Submission Checklist

- [ ] Public GitHub repo with open source license (MIT)
- [ ] README with setup instructions
- [ ] Architecture diagram (PNG/SVG)
- [ ] Demo video ~3 minutes (YouTube/Vimeo)
- [ ] Alibaba Cloud deployment proof (screen recording of backend running)
- [ ] Link to code file showing Alibaba Cloud API usage
- [ ] Devpost submission with track selection (Track 3: Agent Society)
- [ ] Optional: Blog post / social post for Blog Post Prize ($500)

---

## 9. Timeline (Jun 9 → Jul 9, 2026)

| Week | Focus |
|------|-------|
| Week 1 (Jun 9-15) | Finish RepoWise (Band Hackathon deadline Jun 19) |
| Week 2 (Jun 16-22) | CodeTribunal: FastAPI backend + agent debate loop |
| Week 3 (Jun 23-29) | Frontend: hero flow + courtroom UI + WebSocket integration |
| Week 4 (Jun 30-Jul 5) | Alibaba Cloud deployment + polish + demo video |
| Final (Jul 6-9) | Submission, README, architecture diagram, Devpost |

---

## 10. Project Info

- **Hackathon:** Global AI Hackathon with Qwen Cloud (lablab.ai × Alibaba Cloud)
- **Track:** Track 3 — Agent Society
- **Deadline:** July 9, 2026 @ 9:00pm UTC
- **Prize:** $7,000 cash + $3,000 cloud credits (track winner)
- **Builder:** M. Rifki Haipal (quiiplle / einzeinn)
- **Credits:** $40 Qwen Cloud voucher (active, expires Aug 9, 2026)
- **Repo:** github.com/einzeinn/codetribunal (to be created)
