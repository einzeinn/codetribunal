# CodeTribunal Architecture

## System Architecture Diagram

```mermaid
graph TB
    subgraph Frontend["Frontend (Next.js 14 / Vercel)"]
        UI["Courtroom UI"]
        WS_CLIENT["WebSocket Client"]
    end

    subgraph Backend["Backend (FastAPI / Render)"]
        API["REST + WebSocket API"]
        ORCH["Orchestrator (TribunalCourt)"]
        
        subgraph Agents["Specialized Agents"]
            LEDGER["LEDGER (Clerk)<br/>qwen-turbo<br/>AST Parsing"]
            AEGIS["AEGIS (Prosecutor)<br/>qwen-max<br/>Bandit + LLM"]
            AXIOM["AXIOM (Defense)<br/>qwen-plus<br/>ValidationDetector + LLM"]
            METRIC["METRIC (Expert Witness)<br/>qwen-plus<br/>Radon + LLM"]
            ARBITER["ARBITER (Judge)<br/>qwen-max<br/>Verdict + Orchestration"]
        end
        
        subgraph Tools["Tool Layer (Evidence)"]
            BANDIT["BanditRunner<br/>Security Linting"]
            RADON["RadonRunner<br/>Complexity Metrics"]
            AST["ASTParser<br/>Structural Index"]
            VALDET["ValidationDetector<br/>Sanitization Patterns"]
        end
        
        BENCH["Benchmark Module<br/>Single-agent vs Multi-agent"]
    end

    subgraph Cloud["Alibaba Cloud Services"]
        QWEN["Qwen Cloud API<br/>dashscope.aliyuncs.com"]
    end

    subgraph Database["Database"]
        NEON["Neon PostgreSQL<br/>Session Store"]
    end

    UI -->|"HTTP REST"| API
    WS_CLIENT -->|"WebSocket"| API
    API --> ORCH
    ORCH --> LEDGER
    ORCH --> AEGIS
    ORCH --> AXIOM
    ORCH --> METRIC
    ORCH --> ARBITER
    
    AEGIS --> BANDIT
    AXIOM --> VALDET
    METRIC --> RADON
    LEDGER --> AST
    
    LEDGER -->|"LLM (if needed)"| QWEN
    AEGIS -->|"LLM reasoning"| QWEN
    AXIOM -->|"LLM reasoning"| QWEN
    METRIC -->|"LLM reasoning"| QWEN
    ARBITER -->|"Verdict + Rulings"| QWEN
    
    API --> NEON
```

## Conditional Multi-Agent Protocol

```mermaid
graph LR
    A["1. LEDGER<br/>File the Case"] --> B["2. PARALLEL INVESTIGATION<br/>AEGIS + AXIOM + METRIC"]
    B --> C["3. CONFLICT DETECTION<br/>Deterministic line-range overlap"]
    C --> D{"Conflicts found?"}
    D -->|Yes| E["4. CROSS-EXAMINATION<br/>Only conflicting agents debate"]
    D -->|No| G["5. VERDICT<br/>ARBITER rules per-item"]
    E --> F{"ARBITER ruling"}
    F -->|"Continue"| E
    F -->|"Conclude"| G
    F -->|"Extend"| E
    G --> H["Scores + Final Ruling"]
```

## Data Flow

1. **User uploads code** -> LEDGER parses via AST/regex -> structural index stored in context
2. **Parallel investigation** -> Each agent runs its own tool (Bandit/Radon/ValidationDetector) -> structured AgentFinding objects
3. **Conflict detection** -> Deterministic line-range overlap algorithm (no LLM) -> ConflictCluster objects
4. **Cross-examination** (conditional) -> Only agents with conflicting findings debate -> agents can withdraw or revise confidence
5. **ARBITER procedural ruling** -> Dynamic decision: continue/conclude/extend debate rounds
6. **Verdict** -> Rubric-based deterministic scoring + LLM per-item ruling with reasoning trails

## Benchmark Comparison (Track 3 Requirement)

The `/benchmark/` endpoint runs both approaches on the same code:

| Dimension | Single-Agent Baseline | Multi-Agent Tribunal |
|-----------|----------------------|---------------------|
| LLM Calls | 1 | 5-12 (parallel + debate) |
| Tools Used | None | Bandit, Radon, AST, ValidationDetector |
| False Positives | Not filtered | Cross-examination withdraws weak claims |
| Scoring | LLM guesses from text | Deterministic rubric from structured findings |
| Coverage | Shallow, single perspective | Security + Performance + Maintainability |
