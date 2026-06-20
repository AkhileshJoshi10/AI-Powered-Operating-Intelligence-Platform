# AI-Powered Operating Intelligence Platform

## Project Title

**AI-Powered Operating Intelligence Platform**  
A Project On  
**Multi-Agent AI System for Business Monitoring, Decision Support, and Workflow Automation**

## Project Overview

This project aims to develop an AI-powered operating intelligence platform that acts as a digital Chief of Staff for business managers.

The system will monitor business data, detect important issues, prioritize problems, explain likely root causes, generate AI-based recommendations, support manager review and task assignment, and automate follow-up workflows.

## Problem Statement

Modern businesses generate large volumes of data from sales, inventory, finance, customer support, vendors, employees, and operations. However, this information is often scattered across spreadsheets, dashboards, emails, and reports.

Traditional dashboards show what has happened, but they do not clearly explain why a problem occurred, which issue should be handled first, what action should be taken, or how follow-up work should be automated.

This project addresses this problem by building a multi-agent AI system that supports business monitoring, decision-making, task management, and workflow automation.

## Objective

The main objective of this project is to design and develop an AI-powered platform that helps managers:

- Monitor business performance
- Identify and prioritize business problems
- Detect sales, inventory, complaint, vendor, and financial risks
- Generate evidence-based root-cause explanations
- Recommend actions, owners, deadlines, and expected impact
- Review, accept, edit, reject, and assign recommendations
- Track tasks through a Kanban board
- Automate notifications and follow-ups through n8n workflows
- Generate a Daily Executive Brief for managers

## Demo Company

The demo company selected for this project is **SmartMart Retail Pvt. Ltd.**, a fictional retail/FMCG superstore business.

## MVP Scope

The MVP will include:

- Validated business datasets
- PostgreSQL database storage
- Data cleaning and processing
- KPI calculation
- Sales, inventory, complaint, vendor, and finance issue detection
- Priority ranking of issues
- Root-cause explanation
- AI-generated recommendations
- Manager review and approval screen
- Kanban board for task tracking
- Daily Executive Brief
- n8n workflow automation
- Automation logs
- React frontend
- FastAPI backend

## Datasets

The project currently uses the following validated datasets:

| Dataset | Purpose |
|---|---|
| `products_data.csv` | Product details, pricing, cost, reorder level, shelf life, and vendor linkage. |
| `stores_data.csv` | Store location, manager, sales target, and operational details. |
| `vendors_data.csv` | Vendor details, rating, supply status, payment terms, and expected delivery time. |
| `employees_data.csv` | Employee roles, departments, store assignment, and performance details. |
| `sales_data.csv` | Product-level sales transactions across stores. |
| `inventory_data.csv` | Store-wise stock levels, reorder status, expiry data, and inventory risks. |
| `complaints_data.csv` | Complaint details, severity, assignment, status, and resolution information. |
| `finance_data.csv` | Monthly revenue, cost, gross profit, operating expense, operating profit, and financial risk. |
| `vendor_deliveries_data.csv` | Purchase orders, delivery delays, partial deliveries, and vendor quality ratings. |

### Data Period

```text
01-01-2026 to 30-06-2026
```

### Key Business Scenarios Included

- Store `S003` has a significant sales decline in June 2026.
- Store `S003` has increased complaints in June.
- Selected products in Store `S003` and Store `S005` have low-stock risk.
- Store `S007` has selected overstocked grocery products.
- Vendor `V004` and Vendor `V009` show recurring delivery delays.
- Vendor `V009` has lower quality ratings in some delivery records.
- Financial risk is identified using operating profit and target-achievement percentage.

## Data Validation

The dataset layer has been validated using:

```text
backend/data_validation.py
```

The validation checks:

- Required columns
- Missing values
- Duplicate IDs
- Foreign-key relationships
- Numeric data types
- Negative values
- Date formats
- Invalid dates
- Inventory stock-status logic
- Reorder logic
- Expiry-date logic
- Finance calculation logic
- Vendor delivery-date logic
- Vendor delay-day logic

Current validation result:

```text
No validation errors found.
No validation warnings found.
```

## Planned System Flow

```text
Raw CSV Data
    ↓
Data Validation and Cleaning
    ↓
PostgreSQL Database
    ↓
Analytics and Issue Detection Engine
    ↓
Priority Ranking Engine
    ↓
AI Agents
    ↓
Manager Review and Approval
    ↓
Task Creation and Kanban Tracking
    ↓
n8n Automation
    ↓
Automation Logs and Daily Executive Brief
    ↓
React Dashboard
```

## Tech Stack

### Backend

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Pandas
- NumPy
- Scikit-learn
- OpenAI / LLM API

### Frontend

- React
- Vite
- Axios
- React Router
- Plotly or Recharts
- Material UI or Tailwind CSS

### Automation and Tools

- n8n
- GitHub
- pgAdmin 4
- PostgreSQL 17.6
- VS Code

## Main Future Modules

The system will later include:

- Business Monitoring Agent
- Root Cause Analysis Agent
- Recommendation Agent
- Executive Brief Agent
- Chief of Staff Orchestrator Agent
- Sales Agent
- Inventory Agent
- Finance Agent
- Vendor and Procurement Agent
- Complaint and Customer Support Agent

## Project Status

**Current Stage:** Dataset Design, Generation, and Validation Completed

**Next Step:** Install PostgreSQL, create the project database, design the database schema, and load the validated datasets into PostgreSQL.