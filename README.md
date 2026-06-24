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
- **Deployment**: Render (Docker + Uvicorn)

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Fonts**: Cinzel (headers/titles) + IM Fell English (body)
- **Real-time**: WebSocket client (native browser API)
- **Deployment**: Vercel

### Storage
- **Database**: Neon PostgreSQL (Serverless, session store + case persistence)

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
LEDGER: Parse & index code via AST → create structural case file
        ↓
PARALLEL INVESTIGATION:
  AEGIS: Bandit security scan + LLM reasoning → security findings
  AXIOM: Validation pattern detection + LLM reasoning → defense evidence
  METRIC: Radon complexity analysis + LLM reasoning → performance data
        ↓
CONFLICT DETECTION (deterministic, no LLM):
  Line-range overlap analysis → cluster conflicting findings
        ↓
CROSS-EXAMINATION (conditional — only if conflicts exist):
  Only conflicting agents debate their specific clusters
  ARBITER issues procedural rulings: continue / conclude / extend
        ↓
VERDICT:
  Rubric-based deterministic scoring (security, performance, maintainability)
  ARBITER per-item ruling with reasoning trails
        ↓
Final Ruling: APPROVED / APPROVED WITH CONDITIONS / REJECTED
```

## 📊 Debate Protocol Rules

1. **Filing** — LEDGER parses code via AST, creates structural index
2. **Parallel Investigation** — AEGIS, AXIOM, METRIC run concurrently with their own tools
3. **Conflict Detection** — Deterministic line-range overlap (no LLM call)
4. **Cross-Examination** — Only conflicting agents debate their specific clusters
5. **ARBITER Procedural Ruling** — Dynamic decision: continue / conclude / extend debate
6. **Verdict** — Rubric-based deterministic scoring + per-item LLM ruling
7. **Max rounds:** 3 + 1 possible ARBITER extension (prevent infinite loops)
8. **Early termination:** Agent withdrawal (confidence < 0.3) resolves cluster immediately

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
- Multiple agents with **distinct capabilities** and **agent-specific tools** (Bandit, Radon, AST, ValidationDetector)
- **Task decomposition**: parallel investigation with role-based specialization
- **Dialogue and negotiation**: cross-examination debate with confidence revision and withdrawal
- **Conflict resolution**: deterministic line-range overlap detection + per-cluster targeted debate
- **Dynamic orchestration**: ARBITER decides whether to continue, conclude, or extend debate rounds
- **Measurable efficiency gain**: `/benchmark/` endpoint compares single-agent vs multi-agent side by side
- **Transparent scoring**: deterministic rubric-based scores from structured findings, not LLM guessing

## 📈 Benchmark: Single-Agent vs Multi-Agent

Run the comparison:
```bash
curl -X POST http://localhost:8000/benchmark/ \
  -H "Content-Type: application/json" \
  -d '{"code_content": "your code here", "language": "python"}'
```

| Metric | Single-Agent Baseline | Multi-Agent Tribunal |
|--------|----------------------|---------------------|
| Findings coverage | Shallow, 1 perspective | Deep: security + performance + maintainability |
| False positive filtering | None | Cross-examination withdraws weak claims |
| Tool evidence | None | Bandit, Radon, AST, ValidationDetector |
| Scoring transparency | LLM guesses from text | Deterministic rubric from structured data |
| Debate rounds | N/A | Dynamic (ARBITER decides continue/conclude/extend) |

## 🤖 AI / Models

- **ARBITER**: qwen-max — complex orchestration & final verdict
- **AEGIS**: qwen-max — adversarial reasoning, sharp attack
- **AXIOM**: qwen-plus — counter-argument, lighter reasoning
- **METRIC**: qwen-plus — data analysis & complexity
- **LEDGER**: qwen-turbo — parsing & recording only

## 🏗️ Architecture Diagram

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system architecture, protocol flow, and data flow diagrams.

### Proof of Alibaba Cloud Service Usage

- **Backend Hosting**: Render (Docker + Uvicorn)
- **LLM API**: Qwen Cloud (Alibaba Cloud) via `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **Models**: qwen-max, qwen-plus, qwen-turbo from Alibaba's Qwen family
- **Evidence**: See `backend/config.py` line 15 for `QWEN_BASE_URL` configuration

## 📄 License

MIT License - see the [LICENSE](LICENSE) file for details.