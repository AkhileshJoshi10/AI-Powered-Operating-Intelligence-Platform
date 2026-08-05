# PROJECT CONTEXT — AI-Powered Operating Intelligence Platform

## Current Project Stage

Current day: **Day 29**

Current active work:

**Week 5 — Multi-Agent AI, RAG and Controlled Tool Use**
**Day 29 — Agent architecture, LLM foundation and guardrails**

Day 1 to Day 28 are treated as completed.

The next task is to create the AI agent architecture foundation under:

```text
backend/app/agents/
```

Do not start Day 30, Day 31, RAG, MCP, n8n, or React until Day 29 is completed.

---

# 1. Final Project Identity

Project name:

**AI-Powered Operating Intelligence Platform**

Product name:

**AI Chief of Staff**

Academic title:

**Multi-Agent AI System for Business Monitoring, Decision Support, and Workflow Automation**

Demo company:

**SmartMart Retail Pvt. Ltd.**

---

# 2. Project Goal

Build an AI Chief of Staff system that monitors business datasets, calculates KPIs, detects operational issues, prioritizes them, explains root causes, recommends actions, supports manager review, converts accepted recommendations into tasks, and later enhances the system using multi-agent AI, RAG, controlled tools, n8n workflows, and a React SaaS dashboard.

---

# 3. Final End-to-End System Flow

```text
Business datasets or uploaded CSV files
        ↓
Raw-data validation
        ↓
Data cleaning
        ↓
Processed-data validation
        ↓
PostgreSQL database
        ↓
KPI calculation and deterministic domain analytics
        ↓
Analytical findings
        ↓
Issue consolidation with linked evidence
        ↓
Priority scoring
        ↓
Executive Top 10 and Manager Priority List
        ↓
Deterministic root-cause analysis
        ↓
Deterministic recommendations
        ↓
Human review: Accept / Edit / Reject
        ↓
Accepted recommendation converted into task
        ↓
Task assignment and Kanban workflow
        ↓
FastAPI service and control layer
        ↓
Multi-agent AI enhancement layer
        ↓
n8n alerts, reminders and scheduled workflows
        ↓
Daily Executive Brief
        ↓
React SaaS dashboard
        ↓
Testing, deployment, reporting and demonstration
```

Logs maintained throughout the system:

```text
data_import_logs
audit_logs
agent_runs
automation_logs
```

Daily Executive Brief final contents:

```text
KPI snapshot
Top business issues
High-priority issues
Evidence summaries
Root-cause summaries
Recommendations awaiting review
Task progress
Blocked tasks
Overdue tasks
Automation activity
Management attention points
```

---

# 4. Final Architecture Principles

These rules apply to the entire project:

```text
1. PostgreSQL is the application’s source of truth.
2. Raw CSV files are never overwritten.
3. Cleaned files are generated under data/processed/.
4. Analytics remain under backend/analytics/.
5. FastAPI application code remains under backend/app/.
6. Deterministic analytics remain the factual foundation.
7. AI agents enhance deterministic results; they do not replace them.
8. Every important issue must have supporting evidence.
9. Recommendations require human review.
10. Tasks are not created automatically by an LLM.
11. An accepted recommendation must be explicitly converted into a task.
12. Every important write action must be audited.
13. Every agent run and automation execution must be logged.
14. No duplicate active files such as _new, _v2 or _final.
15. Existing canonical files are updated in place.
16. New datasets are added only when they support a real KPI, decision, recommendation, model, or automation.
17. Payment-delay analytics remain excluded until a proper receivables dataset is added.
18. React is the final frontend. Streamlit remains optional for internal testing.
19. Sensitive data must be masked before being sent to an external LLM.
20. Secrets must never be committed to GitHub.
```

---

# 5. Completed Work Summary

## Week 1 — Project Foundation and Dataset Development

Completed:

```text
Day 1 — Project definition
Day 2 — Repository and project structure
Day 3 — Dataset planning
Day 4 — Master dataset generation
Day 5 — Transaction dataset generation
Day 6 — Raw-data validation
Day 7 — Dataset milestone review
```

Datasets:

```text
products
stores
vendors
employees
sales
inventory
complaints
finance
vendor_deliveries
```

Seeded business scenarios:

```text
S003 June sales decline
S003 financial stress
Low-stock products
Stockout-risk products
Complaint hotspots
Vendor delays
Partial deliveries
Poor vendor quality
Store target underachievement
```

---

## Week 2 — Data Engineering and PostgreSQL

Completed:

```text
Day 8 — Python environment and dependencies
Day 9 — Data-cleaning pipeline
Day 10 — Processed-data validation
Day 11 — PostgreSQL setup
Day 12 — Database schema and ERD
Day 13 — Load processed data into PostgreSQL
```

Database:

```text
ai_operating_intelligence
```

Current local database user:

```text
postgres
```

Business tables:

```text
products
stores
vendors
employees
sales
inventory
complaints
finance
vendor_deliveries
data_import_logs
```

System tables:

```text
issues
issue_evidence
root_cause_analyses
recommendations
tasks
automation_logs
executive_briefs
agent_runs
audit_logs
```

---

## Week 3 — Deterministic Analytics and Decision Intelligence

Completed:

```text
Day 14 — Analytics foundation and KPI calculator
Day 15 — Sales analytics
Day 16 — Inventory analytics
Day 17 — Complaint analytics
Day 18 — Vendor and finance analytics
Day 19 — Priority engine and issue database
Day 20 — Root-cause analysis
Day 21 — Recommendations, human review and tasks
```

Important rule:

```text
Analytics modules stay under backend/analytics/.
Do not move them into backend/app/analytics/.
```

Analytics files:

```text
backend/analytics/date_utils.py
backend/analytics/thresholds.py
backend/analytics/evidence_builder.py
backend/analytics/issue_utils.py
backend/analytics/kpi_calculator.py
backend/analytics/sales_analysis.py
backend/analytics/inventory_analysis.py
backend/analytics/complaint_analysis.py
backend/analytics/vendor_finance_analysis.py
backend/analytics/priority_engine.py
backend/analytics/executive_priority_selector.py
backend/analytics/manager_priority_list.py
backend/analytics/root_cause_analysis.py
backend/analytics/recommendation_engine.py
```

Day 19 completed result:

```text
495 analytical findings
129 consolidated issues
495 evidence records

High:   24
Medium: 19
Low:    86
```

Canonical Kanban statuses:

```text
Unassigned
To Do
In Progress
Blocked
Completed
```

Important task rule:

```text
Assigned is not a status.
Assignment is stored through assigned_to and assigned_role.
```

Overdue task rule:

```text
due_date < current date
AND status != Completed
```

---

## Week 4 — FastAPI Backend and Data APIs

Completed:

```text
Day 22 — FastAPI foundation and ORM models
Day 23 — KPI and issue APIs
Day 24 — Recommendation and task APIs
Day 25 — Analytics APIs
Day 26 — Data-management APIs
Day 27 — Daily Executive Brief backend
Day 28 — Automated backend testing and Cycle 3 closure
```

FastAPI structure:

```text
backend/app/
├── main.py
├── core/
├── db/
├── models/
├── schemas/
├── services/
└── routers/
```

Health endpoints:

```text
GET /health
GET /health/database
```

KPI and issue endpoints:

```text
GET /api/kpis
GET /api/issues
GET /api/issues/{issue_id}
```

Recommendation endpoints:

```text
GET   /api/recommendations
GET   /api/recommendations/{recommendation_id}
PATCH /api/recommendations/{recommendation_id}/accept
PATCH /api/recommendations/{recommendation_id}/edit
PATCH /api/recommendations/{recommendation_id}/reject
```

Task endpoints:

```text
POST  /api/tasks/from-recommendation/{recommendation_id}
GET   /api/tasks
GET   /api/tasks/{task_id}
PATCH /api/tasks/{task_id}/status
PATCH /api/tasks/{task_id}/assignment
```

Analytics endpoints:

```text
GET /api/analytics/sales
GET /api/analytics/inventory
GET /api/analytics/complaints
GET /api/analytics/vendors
GET /api/analytics/finance
```

Data-management endpoints:

```text
POST /api/data/validate
POST /api/data/import
GET  /api/data/import-history
```

Executive Brief endpoints:

```text
GET  /api/executive-brief/latest
POST /api/executive-brief/generate
```

Day 28 testing files:

```text
tests/conftest.py
tests/test_health.py
tests/test_kpis.py
tests/test_issues.py
tests/test_recommendations.py
tests/test_tasks.py
tests/test_analytics.py
tests/test_data_validation.py
tests/test_data_import.py
tests/test_import_history.py
tests/test_executive_briefs.py
```

Day 28 reports:

```text
reports/backend_test_report.md
reports/synthetic_scenario_evaluation.md
```

---

# 6. Current Active Step — Day 29

## Day 29 — Agent Architecture, LLM Foundation and Guardrails

Create:

```text
backend/app/agents/
```

Suggested structure:

```text
backend/app/agents/
├── __init__.py
├── base.py
├── schemas.py
├── prompts.py
├── monitoring_agent.py
├── priority_agent.py
├── root_cause_agent.py
├── recommendation_agent.py
├── executive_brief_agent.py
└── orchestrator.py
```

Day 29 should define:

```text
Agent responsibilities
Input/output contracts
Pydantic response schemas
LLM provider configuration
Model configuration
Prompt templates
Prompt versions
Agent versions
Timeouts
Retry limits
Token limits
Cost controls
Deterministic fallback rules
Sensitive-data masking
Error handling
Tool permissions
Agent execution logging
```

Agent-run metadata should capture:

```text
agent_name
agent_version
run_type
model_provider
model_name
prompt_version
execution_status
input_summary
output_summary
token_usage
estimated_cost
latency
error_message
tool_calls
run_metadata
started_at
completed_at
```

JSONB can be used for flexible metadata and tool-call details.

Guardrails:

```text
Agents receive validated evidence.
Agents cannot invent business facts.
Structured JSON output is mandatory.
Unsupported statements must be rejected.
External LLM credentials remain in environment variables.
Deterministic outputs remain available when the LLM fails.
Agents must not overwrite deterministic records without a controlled review/versioning process.
Agents must not create tasks automatically.
Write actions require human approval.
```

---

# 7. Day 29 Implementation Rules

For Day 29, do not build full agents yet.

The goal is to create the safe foundation.

Allowed Day 29 work:

```text
Create backend/app/agents/ folder.
Create agent schemas.
Create base agent class.
Create prompt templates.
Create LLM config placeholders.
Create deterministic fallback structure.
Create safe JSON output contracts.
Create logging helper for agent_runs.
Create clear guardrail comments.
```

Not allowed yet:

```text
Do not implement RAG.
Do not implement MCP tools.
Do not trigger n8n.
Do not create React frontend.
Do not let agents create tasks directly.
Do not let agents overwrite accepted recommendations.
Do not let agents replace deterministic priority scores.
Do not hardcode fake business conclusions.
Do not commit API keys.
```

---

# 8. Day 30 to Day 35 Upcoming Plan

## Day 30 — Monitoring and Priority Agents

Monitoring Agent:

```text
Read current KPIs.
Read current issues.
Compare meaningful changes.
Summarize current business health.
Identify business areas requiring attention.
```

Priority Agent:

```text
Explain existing deterministic priority scores.
Explain why priority changed.
Present manager-friendly ranking.
Recommend which issue should be reviewed first.
Never silently replace deterministic priority values.
```

---

## Day 31 — Root-Cause Agent

Tasks:

```text
Read issue data.
Read linked evidence.
Read deterministic root cause.
Produce manager-friendly explanation.
Identify likely contributing factors.
Identify missing evidence.
Include confidence.
Include evidence references.
Reject unsupported causal claims.
Log model and prompt versions.
Preserve deterministic RCA as fallback.
```

---

## Day 32 — Recommendation Agent

Tasks:

```text
Read issue evidence.
Read deterministic RCA.
Read deterministic recommendation.
Improve clarity and action sequencing.
Suggest owner.
Suggest deadline.
Estimate expected impact.
State reasoning and confidence.
Flag insufficient evidence.
Require human approval.
```

Prohibited:

```text
The agent must not create or execute a task automatically.
```

---

## Day 33 — Executive Brief Agent and Orchestrator

Executive Brief Agent:

```text
Enhance deterministic brief language.
Create concise executive summaries.
Highlight major changes.
Preserve exact factual values.
Include citations to internal evidence.
Fall back to deterministic brief when unavailable.
```

Orchestrator Agent:

```text
Detect newly available issues.
Route issues to the correct agent.
Collect structured responses.
Prevent duplicate processing.
Prevent conflicting actions.
Prepare recommendations.
Prepare Executive Brief enhancement.
Wait for human approval before write actions.
Log every agent and tool interaction.
```

Initial orchestration sequence:

```text
Monitoring Agent
→ Priority Agent
→ Root-Cause Agent
→ Recommendation Agent
→ Executive Brief Agent
→ Human review
```

---

## Day 34 — RAG and Knowledge Layer

Possible knowledge sources:

```text
Business rules
KPI definitions
Company policies
SOP documents
Vendor contracts
Escalation rules
Historical reports
Meeting notes
User guides
```

Possible storage options:

```text
pgvector
ChromaDB
FAISS
```

Preference:

```text
Prefer PostgreSQL/pgvector when practical because PostgreSQL is already the application database.
```

---

## Day 35 — MCP and Controlled Tool Use

Agent tools:

```text
Read KPI tool
Read issue tool
Read evidence tool
Read root-cause tool
Read recommendation tool
Read task tool
Read brief tool
Read-only SQL analytics tool
Report generation tool
Controlled task tool
Controlled workflow trigger tool
```

Controls:

```text
Read tools are preferred.
SQL tools must be read-only.
Parameterized queries are mandatory.
Write tools require explicit permission.
Task creation requires reviewed recommendation context.
Tool calls must be logged.
Tool output must be validated.
Permission checks must happen before execution.
Timeouts and retry limits must be enforced.
```

---

# 9. Later Pending Work

## Week 6 — n8n, React, Integration, Deployment and Release

Pending:

```text
Day 36 — n8n and automation API foundation
Day 37 — Alerts, reminders and escalation workflows
Day 38 — Scheduled Executive Brief automation
Day 39 — React frontend foundation
Day 40 — React dashboard and intelligence screens
Day 41 — End-to-end integration, security, reliability and deployment
Day 42 — Final documentation, evaluation and project release
```

---

# 10. How Codex Should Work in This Project

Codex must follow these rules:

```text
1. First inspect files before editing.
2. Do not create duplicate files with _new, _v2, or _final.
3. Do not modify .env.
4. Do not modify raw CSV files.
5. Do not overwrite reports unless explicitly asked.
6. Do not move backend/analytics into backend/app/.
7. Do not change working analytics unless the user asks.
8. Make small controlled changes.
9. Show which files will be changed before editing.
10. Run tests only after the user approves.
11. Explain errors before fixing them.
12. Preserve the current project workflow.
```

Recommended first Codex prompt:

```text
Read PROJECT_CONTEXT.md and inspect the current project folder structure. Do not edit, create, delete, or run any files. Tell me whether the project is ready for Day 29 and list the exact files needed for backend/app/agents/.
```

Recommended Day 29 Codex prompt:

```text
Use PROJECT_CONTEXT.md as the source of truth. We are on Day 29: Agent architecture, LLM foundation and guardrails.

Inspect backend/app/, backend/app/models/, backend/app/schemas/, backend/app/services/, and database system tables first.

Do not edit files yet.

Tell me the safest file-by-file plan to create backend/app/agents/ without breaking the existing FastAPI backend.
```

Recommended controlled creation prompt:

```text
Create only the Day 29 agent foundation files under backend/app/agents/. Do not modify existing analytics, routers, models, schemas, services, database files, .env, data, or reports.

Create:
backend/app/agents/__init__.py
backend/app/agents/schemas.py
backend/app/agents/prompts.py
backend/app/agents/base.py

Use safe placeholder logic, strict Pydantic schemas, deterministic fallback design, and agent-run logging structure.

Show the changes after creation. Do not run tests yet.
```

---

# 11. Current Rule for This Chat

The current active day is:

```text
Day 29 — Agent architecture, LLM foundation and guardrails
```

Do not move to Day 30 until Day 29 files are created, reviewed, and tested.
