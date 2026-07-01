# Database Setup Guide

## AI-Powered Operating Intelligence Platform

This guide explains how to set up and load the PostgreSQL database used by the project.

## 1. Database Details

| Item                         | Value                       |
| ---------------------------- | --------------------------- |
| Database system              | PostgreSQL                  |
| Database name                | `ai_operating_intelligence` |
| Database administration tool | pgAdmin                     |
| Demo company                 | SmartMart Retail Pvt. Ltd.  |

## 2. Required Software

Install the following software before running the database workflow:

* PostgreSQL
* pgAdmin
* Python
* Visual Studio Code

## 3. Environment Configuration

The database credentials are stored in the local `.env` file in the project root directory.

Example format:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_operating_intelligence
DB_USER=postgres
DB_PASSWORD=your_postgresql_password
```

## 4. Create the Database

Open pgAdmin and create the database:

```text
ai_operating_intelligence
```

Connect to this database before executing the schema file.

## 5. Create Database Tables

Open the following file in pgAdmin Query Tool:

```text
database/schema.sql
```

Execute the complete SQL script.

This creates the business-data tables:

* vendors
* employees
* stores
* products
* sales
* inventory
* complaints
* finance
* vendor_deliveries
* data_import_logs

## 6. Validate Processed Data

Activate the Python virtual environment and run:

```powershell
python backend/processed_data_validation.py
```

The processed-data validation must complete without errors before importing data into PostgreSQL.

## 7. Load Data into PostgreSQL

Run the loader script from the project root:

```powershell
python backend/load_processed_data.py
```

The loading sequence is:

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
```

This order is required because the tables use foreign-key relationships.

## 8. Verify Database Loading

Use the queries available in:

```text
database/sample_queries.sql
```

Verify that all nine datasets are loaded and that table row counts match the processed CSV files.

Expected row counts:

| Table             | Expected Rows |
| ----------------- | ------------: |
| vendors           |            10 |
| employees         |            25 |
| stores            |            10 |
| products          |            25 |
| sales             |        44,435 |
| inventory         |           250 |
| complaints        |         1,572 |
| finance           |            60 |
| vendor_deliveries |            85 |