# AI-Powered Operating Intelligence Platform

## Project Title

**AI-Powered Operating Intelligence Platform**
A Project On
**Multi-Agent AI System for Business Monitoring, Decision Support, and Workflow Automation**

---

## Project Overview

This project develops an AI-powered operating intelligence platform that acts as a digital Chief of Staff for business managers.

The platform uses business data from sales, inventory, finance, customer complaints, vendors, employees, and store operations to detect important problems, prioritize them, explain likely root causes, recommend actions, support manager review, and automate follow-up workflows.

The demo company is **SmartMart Retail Pvt. Ltd.**, a fictional retail/FMCG superstore business.

---

## Business Problem

Modern businesses generate large volumes of data across sales systems, inventory records, finance reports, customer-support logs, vendor deliveries, spreadsheets, and dashboards.

Traditional dashboards can show what happened, but they often do not clearly answer:

* Why did the problem occur?
* Which issue should be handled first?
* Which store, product, or vendor is affected?
* What action should be taken?
* Who should own the action?
* How should follow-up work be tracked and automated?

This project addresses these gaps through a structured operating-intelligence workflow.

---

## Project Objectives

The platform is designed to help managers:

* Monitor business performance through KPIs and alerts.
* Detect sales, inventory, complaint, vendor, and finance risks.
* Rank issues as High, Medium, or Low priority.
* Generate evidence-based root-cause explanations.
* Recommend actions, owners, deadlines, and expected impact.
* Allow managers to accept, edit, reject, and assign recommendations.
* Track approved work through a Kanban board.
* Trigger notifications, reminders, and escalations through n8n workflows.
* Generate Daily Executive Briefs for managers and executives.

---

## Current Development Status

### Completed

* Project repository, virtual environment, dependencies, and folder structure created.
* Synthetic SmartMart Retail datasets generated for January–June 2026.
* Raw datasets preserved in `data/raw/`.
* Cleaned datasets generated in `data/processed/`.
* Raw-data and processed-data validation completed successfully.
* PostgreSQL database `ai_operating_intelligence` created and connected locally.
* PostgreSQL business-data schema created and executed.
* ERD, data dictionary, SQL query file, and database documentation created.
* All nine cleaned datasets loaded successfully into PostgreSQL.
* Table row counts, foreign-key relationships, and database constraints verified.
* Exploratory Data Analysis completed.
* Rule-based issue-detection engine created.
* Priority scoring created for High, Medium, and Low business issues.
* Evidence-based root-cause analysis engine created.

### Latest Analytics Output

The latest issue-detection run identified:

| Priority | Number of Issues |
| -------- | ---------------: |
| High     |                7 |
| Medium   |               14 |
| Low      |               14 |

A total of **21 High and Medium priority issues** were analysed through the root-cause analysis engine.

Key findings include:

* SmartMart Clock Tower (`S003`) has a major June sales decline.
* SmartMart Clock Tower has high complaint volume and low-stock risks.
* SmartMart Clock Tower has serious financial-risk indicators.
* Vendors `V004` and `V009` show major delivery-performance risk.
* Products such as Instant Noodles Pack, Biscuits 300g, and Chips 150g show low-stock risk in selected stores.

### Current Stage

**Cycle 2: Analytics and Issue Detection Engine**

The project has completed the initial issue-detection and root-cause-analysis workflow. The remaining Cycle 2 work includes a dedicated KPI module, expanded analytics rules, reusable analytics utilities, and storing detected issues/evidence in PostgreSQL.

---

## Current Data Flow

```text
Raw CSV Data
    ↓
Raw Data Validation
    ↓
Data Cleaning
    ↓
Processed Data Validation
    ↓
PostgreSQL Database
    ↓
Rule-Based Issue Detection
    ↓
Priority Scoring
    ↓
Evidence-Based Root-Cause Analysis
    ↓
Manager-Ready Reports
```

---

## Target End-to-End System Flow

```text
Business Data
    ↓
Data Validation and Cleaning
    ↓
PostgreSQL Database
    ↓
Analytics and Issue Detection Engine
    ↓
Priority Ranking Engine
    ↓
Root-Cause Analysis
    ↓
AI Recommendation Agent
    ↓
Manager Review and Approval
    ↓
Task Creation and Kanban Tracking
    ↓
n8n Workflow Automation
    ↓
Automation Logs and Daily Executive Brief
    ↓
React Dashboard
```

---

## Demo Company

**SmartMart Retail Pvt. Ltd.**

SmartMart is a fictional retail/FMCG superstore company with multiple stores, vendors, employees, products, sales transactions, inventory records, customer complaints, finance records, and vendor-delivery data.

---

## Datasets

The project currently uses nine validated datasets.

| Dataset                      | Purpose                                                                                        |
| ---------------------------- | ---------------------------------------------------------------------------------------------- |
| `products_data.csv`          | Product details, prices, costs, reorder levels, shelf life, perishability, and vendor linkage. |
| `stores_data.csv`            | Store location, manager, sales target, and operational details.                                |
| `vendors_data.csv`           | Vendor details, supply status, rating, payment terms, and delivery information.                |
| `employees_data.csv`         | Employee roles, departments, store assignment, and performance details.                        |
| `sales_data.csv`             | Product-level sales transactions across SmartMart stores.                                      |
| `inventory_data.csv`         | Store-wise stock levels, reorder status, expiry dates, and inventory risks.                    |
| `complaints_data.csv`        | Customer complaints, severity, assignment, status, and resolution details.                     |
| `finance_data.csv`           | Monthly revenue, cost, gross profit, operating expense, operating profit, and financial risk.  |
| `vendor_deliveries_data.csv` | Purchase orders, delivery delays, partial deliveries, and vendor quality ratings.              |

### Data Period

```text
01-01-2026 to 30-06-2026
```

---

## Key Business Scenarios Included

The synthetic data intentionally includes realistic business scenarios for testing:

* Store `S003` has a significant sales decline in June 2026.
* Store `S003` has high complaint volume.
* Store `S003` has financial-risk indicators and low target achievement.
* Selected products at Store `S003` and Store `S005` have low-stock risk.
* Store `S007` contains selected overstocked grocery products.
* Vendor `V004` and Vendor `V009` show recurring delivery delays.
* Vendor `V009` has lower quality ratings in selected delivery records.
* Financial risk is calculated using operating profit, revenue, and target-achievement percentage.

---

## Data Validation and Cleaning

### Raw Data Validation

Raw data is validated using:

```text
backend/data_validation.py
```

Validation includes:

* Required-column checks
* Missing-value checks
* Duplicate-ID checks
* Foreign-key validation
* Numeric and negative-value checks
* Date-format validation
* Inventory stock-status validation
* Reorder-rule validation
* Expiry-date validation
* Finance-formula validation
* Vendor delivery-date validation
* Vendor delay-day validation

### Data Cleaning

Data cleaning is performed using:

```text
backend/data_cleaning.py
```

The cleaning process:

* Preserves raw data without overwriting it.
* Removes unnecessary spaces.
* Standardizes IDs and text values.
* Converts dates to ISO format.
* Converts numeric fields to correct data types.
* Removes exact duplicate records.
* Generates cleaned CSV files in `data/processed/`.

### Processed Data Validation

Processed datasets are validated using:

```text
backend/processed_data_validation.py
```

Latest validation result:

```text
No validation errors found.
No warnings found.
```

---

## PostgreSQL Database

**Database Name:** `ai_operating_intelligence`

The database currently contains these business-data tables:

```text
vendors
employees
stores
products
sales
inventory
complaints
finance
vendor_deliveries
data_import_logs
```

Database-related files:

```text
database/schema.sql
database/erd.md
database/erd.dbml
database/erd.png
database/data_dictionary.md
database/sample_queries.sql
```

All nine cleaned datasets have been loaded successfully into PostgreSQL.

---

## Analytics and Issue Detection

The current analytics engine is available in:

```text
backend/analytics/
```

### Issue Detection

```text
backend/analytics/issue_detection.py
```

The engine currently detects:

* Financial-risk stores
* Major store sales decline
* Inventory stock risk
* Customer complaint hotspots
* Vendor delivery-performance risk

It generates:

```text
reports/detected_issues.csv
reports/detected_issues_report.md
```

### Root-Cause Analysis

```text
backend/analytics/root_cause_analysis.py
```

The root-cause engine analyses High and Medium priority issues using PostgreSQL evidence such as:

* Store sales performance
* Sales decline percentage
* Category-level sales trends
* Inventory availability
* Complaint severity and unresolved complaints
* Vendor delays and quality ratings
* Target achievement
* Operating profit
* Financial-risk status

It generates:

```text
reports/root_cause_analysis.csv
reports/root_cause_analysis_report.md
```

---

## Project Structure

```text
AI-Powered-Operating-Intelligence-Platform/
│
├── backend/
│   ├── analytics/
│   │   ├── __init__.py
│   │   ├── issue_detection.py
│   │   └── root_cause_analysis.py
│   ├── data_cleaning.py
│   ├── data_validation.py
│   ├── load_processed_data.py
│   ├── processed_data_validation.py
│   └── test_database_connection.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── synthetic/
│
├── database/
│   ├── schema.sql
│   ├── erd.md
│   ├── erd.dbml
│   ├── erd.png
│   ├── data_dictionary.md
│   └── sample_queries.sql
│
├── docs/
│   ├── architecture.md
│   ├── dataset_plan.md
│   ├── demo_company.md
│   ├── mvp_scope.md
│   ├── objectives.md
│   └── problem_statement.md
│
├── notebooks/
│   └── data_exploration.ipynb
│
├── reports/
│   ├── data_validation_report.txt
│   ├── data_cleaning_report.txt
│   ├── processed_data_validation_report.txt
│   ├── eda_insights.md
│   ├── detected_issues_report.md
│   └── root_cause_analysis_report.md
│
├── n8n_workflows/
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

---

## Technology Stack

### Current Technologies

* Python
* PostgreSQL
* pgAdmin
* SQLAlchemy
* Pandas
* NumPy
* python-dotenv
* Jupyter Notebook
* Git and GitHub
* Visual Studio Code

### Planned Backend Technologies

* FastAPI
* Pydantic
* Pytest
* Uvicorn

### Planned Frontend Technologies

* React
* Vite
* React Router
* Axios
* Plotly or Recharts
* Material UI or Tailwind CSS

### Planned AI and Automation Technologies

* LLM API
* n8n
* Vector database / RAG
* MCP tool-use layer

---

## Running the Current Workflow

Activate the virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Validate raw data:

```powershell
python backend/data_validation.py
```

Clean raw data:

```powershell
python backend/data_cleaning.py
```

Validate processed data:

```powershell
python backend/processed_data_validation.py
```

Load processed data into PostgreSQL:

```powershell
python backend/load_processed_data.py
```

Run issue detection:

```powershell
python backend/analytics/issue_detection.py
```

Run root-cause analysis:

```powershell
python backend/analytics/root_cause_analysis.py
```

---

## Next Development Steps

The next planned work is to complete the remaining Cycle 2 analytics components:

1. Create common analytics utilities and reusable database connection logic.
2. Create a dedicated KPI calculator.
3. Expand sales analytics for product, category, regional, and store underperformance.
4. Expand inventory analytics for overstock, reorder-soon, near-expiry, and expired-stock risks.
5. Expand complaint analytics for open high-severity complaints, repeated categories, monthly growth, and unresolved complaint ageing.
6. Expand vendor and finance analytics for partial deliveries, on-time delivery rate, low operating profit, and loss-making months.
7. Create PostgreSQL workflow tables for issues and issue evidence.
8. Store detected issues and evidence in PostgreSQL.
9. Begin FastAPI backend development.

---

## Future Modules

The full platform will later include:

* KPI Calculator
* Business Monitoring Agent
* Root Cause Analysis Agent
* Recommendation Agent
* Executive Brief Agent
* Chief of Staff Orchestrator
* Sales Agent
* Inventory Agent
* Finance Agent
* Vendor and Procurement Agent
* Complaint and Customer Support Agent
* Recommendation approval workflow
* Kanban task board
* Daily Executive Brief
* n8n notifications, reminders, and escalations
* React dashboard
* FastAPI backend APIs
* RAG and document intelligence
* Predictive analytics modules

---

## Security and Privacy

* Database credentials are stored locally in `.env`.
* `.env` is excluded from GitHub through `.gitignore`.
* `.env.example` provides a safe environment-variable template.
* No passwords, API keys, or confidential data should be committed to the repository.
* Future LLM integration will use validated and minimized business evidence rather than unrestricted database access.

---

## MVP Completion Criteria

The MVP will be considered complete when it can:

* Load validated business datasets.
* Store business data in PostgreSQL.
* Calculate business KPIs.
* Detect sales, inventory, complaint, vendor, and finance issues.
* Rank issues by priority.
* Explain root causes using structured evidence.
* Generate actionable recommendations.
* Allow manager approval or rejection.
* Create and track tasks through a Kanban board.
* Trigger automation alerts through n8n.
* Generate a Daily Executive Brief.
* Display all major outputs through a React frontend.
