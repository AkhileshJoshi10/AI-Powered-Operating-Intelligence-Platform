# Entity Relationship Diagram (ERD)

## AI-Powered Operating Intelligence Platform

**Database:** `ai_operating_intelligence`
**Database System:** PostgreSQL
**Demo Company:** SmartMart Retail Pvt. Ltd.
**Data Period:** January 2026 to June 2026

This document explains the current Entity Relationship Diagram for the business-data foundation of the AI-Powered Operating Intelligence Platform.

The visual ERD is available in:

```text
database/erd.png
```

The editable ERD source is available in:

```text
database/erd.dbml
```

---

# 1. ERD Scope

The current ERD contains the nine business-data tables and one audit table used for data imports.

## Master Data Tables

* `vendors`
* `employees`
* `stores`
* `products`

## Transactional and Operational Tables

* `sales`
* `inventory`
* `complaints`
* `finance`
* `vendor_deliveries`

## Audit Table

* `data_import_logs`

The future AI workflow tables, such as `issues`, `recommendations`, `tasks`, and `automation_logs`, are not part of the current ERD. They will be added after recommendation generation and before FastAPI, frontend, and n8n workflow development.

---

# 2. High-Level Relationship Structure

```text
vendors
   ├── products
   ├── inventory
   └── vendor_deliveries

employees
   ├── stores
   ├── sales
   ├── complaints
   └── vendor_deliveries

stores
   ├── sales
   ├── inventory
   ├── complaints
   ├── finance
   └── vendor_deliveries

products
   ├── sales
   ├── inventory
   ├── complaints
   └── vendor_deliveries
```

---

# 3. Table Relationships

| Parent Table | Parent Key    | Child Table         | Foreign Key            | Relationship                                                 |
| ------------ | ------------- | ------------------- | ---------------------- | ------------------------------------------------------------ |
| `employees`  | `employee_id` | `stores`            | `manager_id`           | One employee can manage one or more stores.                  |
| `vendors`    | `vendor_id`   | `products`          | `vendor_id`            | One vendor can supply multiple products.                     |
| `stores`     | `store_id`    | `sales`             | `store_id`             | One store can have many sales transactions.                  |
| `products`   | `product_id`  | `sales`             | `product_id`           | One product can appear in many sales transactions.           |
| `employees`  | `employee_id` | `sales`             | `employee_id`          | One employee can be associated with many sales transactions. |
| `stores`     | `store_id`    | `inventory`         | `store_id`             | One store can have multiple inventory records.               |
| `products`   | `product_id`  | `inventory`         | `product_id`           | One product can appear in inventory records across stores.   |
| `vendors`    | `vendor_id`   | `inventory`         | `vendor_id`            | One vendor can supply products recorded in inventory.        |
| `stores`     | `store_id`    | `complaints`        | `store_id`             | One store can receive multiple customer complaints.          |
| `products`   | `product_id`  | `complaints`        | `product_id`           | One product can be linked with multiple customer complaints. |
| `employees`  | `employee_id` | `complaints`        | `assigned_employee_id` | One employee can be assigned to resolve multiple complaints. |
| `stores`     | `store_id`    | `finance`           | `store_id`             | One store can have multiple monthly finance records.         |
| `stores`     | `store_id`    | `vendor_deliveries` | `store_id`             | One store can receive multiple vendor deliveries.            |
| `vendors`    | `vendor_id`   | `vendor_deliveries` | `vendor_id`            | One vendor can have multiple deliveries.                     |
| `products`   | `product_id`  | `vendor_deliveries` | `product_id`           | One product can appear in multiple purchase orders.          |
| `employees`  | `employee_id` | `vendor_deliveries` | `assigned_employee_id` | One employee can manage multiple vendor deliveries.          |

---

# 4. Important Design Decisions

## 4.1 Employees and Stores

`stores.manager_id` references `employees.employee_id`.

The `employees.store_id` column is not a foreign key because some employees work at department level and can have the value `ALL` instead of a specific store ID.

## 4.2 Products and Inventory

The `inventory` table does not store `is_perishable`.

Perishability is derived through:

```text
inventory.product_id → products.product_id → products.is_perishable
```

This avoids duplicate storage of product-level information.

## 4.3 Inventory Expiry Calculation

`days_to_expiry` is not stored physically in PostgreSQL or in `inventory_cleaned.csv`.

It is calculated dynamically when needed:

```text
days_to_expiry = expiry_date - inventory.date
```

This prevents outdated values when the inventory date changes.

## 4.4 Denormalized Context Fields

Some transactional tables include descriptive fields such as:

* `store_name`
* `product_name`
* `category`
* `region`
* `vendor_name`

These fields are also available through related master tables. They are retained because the source datasets contain them and they make analytics queries, reports, and future dashboard development easier.

The primary relationship keys remain:

* `store_id`
* `product_id`
* `vendor_id`
* `employee_id`

---

# 5. Primary Keys

| Table               | Primary Key         |
| ------------------- | ------------------- |
| `vendors`           | `vendor_id`         |
| `employees`         | `employee_id`       |
| `stores`            | `store_id`          |
| `products`          | `product_id`        |
| `sales`             | `sale_id`           |
| `inventory`         | `inventory_id`      |
| `complaints`        | `complaint_id`      |
| `finance`           | `finance_id`        |
| `vendor_deliveries` | `purchase_order_id` |
| `data_import_logs`  | `import_id`         |

---

# 6. Business Analysis Supported by the ERD

The current table structure supports the following analyses:

* Monthly sales and profit trends
* Store-level sales performance
* Product-level sales performance
* Low-stock, reorder-soon, and overstock monitoring
* Product expiry monitoring for perishable products
* Complaint hotspot detection
* Complaint analysis by product and store
* Finance risk analysis
* Vendor delivery delay and quality analysis
* Cross-functional business issue detection
* Root-cause analysis using sales, inventory, complaints, finance, and vendor evidence
* Future AI recommendations, task assignment, approval workflows, and executive brief generation

---

# 7. Future ERD Expansion

The following system tables will be added in the next database-design phase:

| Future Table       | Purpose                                                             |
| ------------------ | ------------------------------------------------------------------- |
| `issues`           | Stores detected business issues and priority scores.                |
| `issue_evidence`   | Stores data evidence linked to each issue.                          |
| `recommendations`  | Stores recommended actions, owners, deadlines, and expected impact. |
| `tasks`            | Supports Kanban-based task management.                              |
| `automation_logs`  | Stores n8n workflow and notification execution history.             |
| `executive_briefs` | Stores generated Daily Executive Briefs.                            |
| `agent_runs`       | Stores multi-agent execution details.                               |
| `audit_logs`       | Stores user actions, approvals, edits, and status changes.          |

These tables will connect the current business-data foundation with the AI Chief of Staff workflow layer.
