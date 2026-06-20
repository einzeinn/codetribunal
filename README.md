# CodeTribunal — Multi-agent Adversarial Code Review System

> Where every line of code faces justice

CodeTribunal is a multi-agent code review system that simulates a medieval courtroom where different AI agents take on roles to review code through adversarial debate. This project was developed for the Qwen Cloud Global AI Hackathon, Track 3: Agent Society.

## 🎯 Core Concept

CodeTribunal uses a unique **courtroom metaphor** where code undergoes adversarial review by five specialized agents:

| Agent | Role | Responsibility | Personality |
|-------|------|----------------|-------------|
| **AEGIS** | Prosecutor | Hunt security vulnerabilities, attack code weaknesses | Aggressive, adversarial |
| **ARBITER** | Judge / Orchestrator | Manage debate flow, resolve conflicts, issue final verdict | Neutral, authoritative |
| **AXIOM** | Defense | Defend valid code choices, provide context & counter-arguments | Analytical, protective |
| **METRIC** | Expert Witness | Provide performance data, complexity analysis, benchmarks | Data-driven, objective |
| **LEDGER** | Clerk | Record all proceedings, compile final report | Systematic, comprehensive |

## 🏗️ Tech Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Agent SDK**: Qwen Cloud API (qwen-max / qwen-plus / qwen-turbo)
- **Orchestration**: Custom debate loop
- **WebSocket**: FastAPI WebSocket (real-time debate streaming)
- **Deployment**: Alibaba Cloud ECS (ecst6 burstable, Docker + Uvicorn)

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Fonts**: Cinzel (headers/titles) + IM Fell English (body)
- **Real-time**: WebSocket client (native browser API)
- **Deployment**: Vercel

### Storage
- **Database**: Supabase (PostgreSQL)

## 🚀 Quick Start

1. Clone the repository:
```bash
git clone https://github.com/einzeinn/codetribunal.git
cd codetribunal
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run the backend:
```bash
cd backend
uvicorn main:app --reload
```

6. Run the frontend:
```bash
cd frontend
npm install
npm run dev
```

## 🏛️ Agent Interaction Protocol

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

## 📊 Debate Protocol Rules

1. **Opening Round** — AEGIS presents all findings, AXIOM responds
2. **Evidence Round** — METRIC presents data, agents cross-examine
3. **Closing Round** — Both sides summarize, ARBITER deliberates
4. **Verdict** — ARBITER issues ruling with confidence scores
5. **Max rounds:** 3 (prevent infinite loops)
6. **Consensus mechanism:** Majority confidence score > 0.7 triggers early verdict

## 🎨 UI Aesthetic

- **Theme**: Dark medieval / parchment RPG courtroom
- **Fonts**: Cinzel (headers/titles) + IM Fell English (body)
- **Color palette**: Deep black `#0f0c05`, gold `#d4a843`, parchment `#e8d9b0`, muted `#9a7f4a`
- **Animations**: Streaming debate feed, live score bars, status badges

## 📁 Project Structure

```
CodeTribunal/
├── backend/           # FastAPI backend with agent orchestration
├── frontend/          # Next.js frontend with courtroom UI
├── requirements.txt   # Python dependencies
├── .gitignore        # Git ignore rules
└── README.md         # This file
```

## 🏆 Why This Wins Track 3

Track 3 (Agent Society) requirements addressed:
- ✅ Multiple agents with distinct capabilities
- ✅ Task division & role assignment
- ✅ Dialogue, disagreement & negotiation between agents
- ✅ Measurable efficiency gain vs single-agent baseline
- ✅ Conflict resolution mechanism

## 📈 Measurable Efficiency Metric

| Metric | Single Agent | CodeTribunal (5 agents) |
|--------|-------------|------------------------|
| Issue categories covered | 1-2 | 3+ (security, perf, maintainability) |
| False positive rate | Higher (no counter-argument) | Lower (defense agent filters) |
| Coverage depth | Shallow | Deep (adversarial pressure) |
| Structured output | Inconsistent | Standardized verdict format |

## 🤖 AI / Models

- **ARBITER**: qwen-max — complex orchestration & final verdict
- **AEGIS**: qwen-max — adversarial reasoning, sharp attack
- **AXIOM**: qwen-plus — counter-argument, lighter reasoning
- **METRIC**: qwen-plus — data analysis & complexity
- **LEDGER**: qwen-turbo — parsing & recording only

## 🏗️ Architecture Diagram

```
[User Browser]
     │
     ├── HTTP → [Next.js Frontend / Vercel]
     │              │
     │              └── WebSocket ──────────────────────┐
     │                                                 │
     └── REST API → [FastAPI Backend / Alibaba Cloud]  │
                         │                             │
                         ├── [LEDGER Agent]            │
                         │    └── qwen-turbo           │
                         │                             │
                         ├── [AEGIS Agent]             │
                         │    └── qwen-max             │
                         │                             │
                         ├── [AXIOM Agent]             │
                         │    └── qwen-plus            │
                         │                             │
                         ├── [METRIC Agent]            │
                         │    └── qwen-plus            │
                         │                             │
                         ├── [ARBITER Agent]           │
                         │    └── qwen-max             │
                         │    └── Orchestrates debate  │
                         │    └── Streams via WS ──────┘
                         │
                         └── [Supabase]
                              └── Store cases, proceedings, verdicts
```

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.