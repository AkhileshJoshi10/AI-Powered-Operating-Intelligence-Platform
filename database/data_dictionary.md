# Data Dictionary

## AI-Powered Operating Intelligence Platform

**Database:** `ai_operating_intelligence`
**Database System:** PostgreSQL
**Demo Company:** SmartMart Retail Pvt. Ltd.
**Data Period:** January 2026 to June 2026

This document describes the structure, purpose, and important business rules of the PostgreSQL database used in the AI-Powered Operating Intelligence Platform.

---

# 1. Database Overview

The database stores cleaned and validated business data for SmartMart Retail Pvt. Ltd. It supports sales analysis, inventory monitoring, complaint analysis, finance-risk tracking, vendor-performance analysis, and later AI-based issue detection and recommendation workflows.

The database currently contains the following tables:

| Category                         | Tables                                                             |
| -------------------------------- | ------------------------------------------------------------------ |
| Master Data                      | `vendors`, `employees`, `stores`, `products`                       |
| Transactional / Operational Data | `sales`, `inventory`, `complaints`, `finance`, `vendor_deliveries` |
| System / Audit Data              | `data_import_logs`                                                 |

---

# 2. Data Conventions

| Item                 | Convention                             |
| -------------------- | -------------------------------------- |
| Date format          | PostgreSQL `DATE` format: `YYYY-MM-DD` |
| Month format         | `YYYY-MM`                              |
| Store ID             | Format such as `S001`                  |
| Product ID           | Format such as `P001`                  |
| Vendor ID            | Format such as `V001`                  |
| Employee ID          | Format such as `E001`                  |
| Perishable indicator | `Yes` or `No`                          |
| Reorder required     | `Yes` or `No`                          |
| Monetary values      | PostgreSQL `NUMERIC(14,2)`             |
| Ratings              | PostgreSQL `NUMERIC(3,1)`              |
| Missing values       | Stored as `NULL` where applicable      |

---

# 3. Table: vendors

Stores vendor and supplier information.

| Column                  | Data Type    | Description                                  |
| ----------------------- | ------------ | -------------------------------------------- |
| `vendor_id`             | VARCHAR(10)  | Unique vendor identifier. Primary key.       |
| `vendor_name`           | VARCHAR(150) | Name of the vendor or supplier.              |
| `vendor_category`       | VARCHAR(100) | Category of products supplied by the vendor. |
| `contact_person`        | VARCHAR(150) | Vendor contact person.                       |
| `city`                  | VARCHAR(100) | Vendor city.                                 |
| `state`                 | VARCHAR(100) | Vendor state.                                |
| `region`                | VARCHAR(50)  | Vendor operating region.                     |
| `average_delivery_days` | INTEGER      | Average number of days taken for delivery.   |
| `rating`                | NUMERIC(3,1) | Vendor rating between 0 and 5.               |
| `payment_terms`         | VARCHAR(100) | Vendor payment terms.                        |
| `supply_status`         | VARCHAR(50)  | Current vendor supply status.                |

**Primary Key:** `vendor_id`

---

# 4. Table: employees

Stores employee and performance information.

| Column               | Data Type     | Description                                                                       |
| -------------------- | ------------- | --------------------------------------------------------------------------------- |
| `employee_id`        | VARCHAR(10)   | Unique employee identifier. Primary key.                                          |
| `employee_name`      | VARCHAR(150)  | Name of the employee.                                                             |
| `role`               | VARCHAR(100)  | Job role of the employee.                                                         |
| `department`         | VARCHAR(100)  | Department to which the employee belongs.                                         |
| `store_id`           | VARCHAR(10)   | Store assigned to the employee. Can contain `ALL` for department-level employees. |
| `region`             | VARCHAR(50)   | Employee operating region.                                                        |
| `email`              | VARCHAR(150)  | Employee email address.                                                           |
| `monthly_target`     | NUMERIC(14,2) | Monthly performance or sales target.                                              |
| `performance_status` | VARCHAR(50)   | Employee performance category.                                                    |
| `employment_status`  | VARCHAR(50)   | Current employment status.                                                        |

**Primary Key:** `employee_id`

---

# 5. Table: stores

Stores SmartMart branch and operational information.

| Column                 | Data Type     | Description                                          |
| ---------------------- | ------------- | ---------------------------------------------------- |
| `store_id`             | VARCHAR(10)   | Unique store identifier. Primary key.                |
| `store_name`           | VARCHAR(150)  | Name of the SmartMart store.                         |
| `city`                 | VARCHAR(100)  | City in which the store operates.                    |
| `state`                | VARCHAR(100)  | State in which the store operates.                   |
| `region`               | VARCHAR(50)   | Store region.                                        |
| `store_type`           | VARCHAR(100)  | Type of store, such as supermarket or express store. |
| `manager_id`           | VARCHAR(10)   | Employee ID of the store manager.                    |
| `opening_date`         | DATE          | Date on which the store started operations.          |
| `monthly_sales_target` | NUMERIC(14,2) | Monthly sales target for the store.                  |
| `operational_status`   | VARCHAR(50)   | Current operational status of the store.             |

**Primary Key:** `store_id`
**Foreign Key:** `manager_id` → `employees.employee_id`

---

# 6. Table: products

Stores product master data.

| Column            | Data Type     | Description                                                 |
| ----------------- | ------------- | ----------------------------------------------------------- |
| `product_id`      | VARCHAR(10)   | Unique product identifier. Primary key.                     |
| `product_name`    | VARCHAR(200)  | Name of the product.                                        |
| `category`        | VARCHAR(100)  | Main product category.                                      |
| `sub_category`    | VARCHAR(100)  | Product sub-category.                                       |
| `brand`           | VARCHAR(100)  | Product brand.                                              |
| `unit_price`      | NUMERIC(12,2) | Selling price per unit.                                     |
| `cost_price`      | NUMERIC(12,2) | Product purchase or cost price per unit.                    |
| `margin_percent`  | NUMERIC(6,2)  | Profit margin percentage.                                   |
| `reorder_level`   | INTEGER       | Stock level at which reorder monitoring is required.        |
| `shelf_life_days` | INTEGER       | Shelf life in days for perishable products.                 |
| `is_perishable`   | VARCHAR(3)    | Indicates whether the product is perishable: `Yes` or `No`. |
| `vendor_id`       | VARCHAR(10)   | Vendor supplying the product.                               |

**Primary Key:** `product_id`
**Foreign Key:** `vendor_id` → `vendors.vendor_id`

**Business Rule:**

* If `is_perishable = 'Yes'`, `shelf_life_days` must be greater than zero.
* If `is_perishable = 'No'`, `shelf_life_days` must be `NULL`.

---

# 7. Table: sales

Stores transaction-level sales data.

| Column             | Data Type     | Description                                          |
| ------------------ | ------------- | ---------------------------------------------------- |
| `sale_id`          | VARCHAR(20)   | Unique sales transaction identifier. Primary key.    |
| `date`             | DATE          | Date of the sales transaction.                       |
| `store_id`         | VARCHAR(10)   | Store where the sale occurred.                       |
| `store_name`       | VARCHAR(150)  | Name of the store.                                   |
| `region`           | VARCHAR(50)   | Region of the store.                                 |
| `product_id`       | VARCHAR(10)   | Product sold.                                        |
| `product_name`     | VARCHAR(200)  | Name of the product sold.                            |
| `category`         | VARCHAR(100)  | Product category.                                    |
| `employee_id`      | VARCHAR(10)   | Employee associated with the sale, where applicable. |
| `quantity_sold`    | INTEGER       | Quantity sold in the transaction.                    |
| `unit_price`       | NUMERIC(12,2) | Selling price per unit.                              |
| `discount_percent` | NUMERIC(6,2)  | Discount percentage applied to the transaction.      |
| `total_sales`      | NUMERIC(14,2) | Total revenue from the transaction.                  |
| `total_cost`       | NUMERIC(14,2) | Total cost associated with the transaction.          |
| `profit`           | NUMERIC(14,2) | Profit earned from the transaction.                  |
| `payment_status`   | VARCHAR(50)   | Payment completion status.                           |

**Primary Key:** `sale_id`
**Foreign Keys:**

* `store_id` → `stores.store_id`
* `product_id` → `products.product_id`
* `employee_id` → `employees.employee_id`

---

# 8. Table: inventory

Stores inventory snapshots for products across SmartMart stores.

| Column             | Data Type    | Description                                                              |
| ------------------ | ------------ | ------------------------------------------------------------------------ |
| `inventory_id`     | VARCHAR(20)  | Unique inventory record identifier. Primary key.                         |
| `date`             | DATE         | Date on which the inventory record was captured.                         |
| `store_id`         | VARCHAR(10)  | Store where stock is available.                                          |
| `store_name`       | VARCHAR(150) | Store name.                                                              |
| `product_id`       | VARCHAR(10)  | Product identifier.                                                      |
| `product_name`     | VARCHAR(200) | Product name.                                                            |
| `category`         | VARCHAR(100) | Product category.                                                        |
| `vendor_id`        | VARCHAR(10)  | Vendor supplying the product.                                            |
| `current_stock`    | INTEGER      | Current available quantity in stock.                                     |
| `reorder_level`    | INTEGER      | Minimum reference level used for inventory monitoring.                   |
| `stock_status`     | VARCHAR(50)  | Inventory status: `Low Stock`, `Reorder Soon`, `Overstock`, or `Normal`. |
| `reorder_required` | VARCHAR(3)   | Indicates whether an immediate reorder is required: `Yes` or `No`.       |
| `expiry_date`      | DATE         | Expiry date for perishable products. Null for non-perishable products.   |

**Primary Key:** `inventory_id`
**Foreign Keys:**

* `store_id` → `stores.store_id`
* `product_id` → `products.product_id`
* `vendor_id` → `vendors.vendor_id`

**Business Rules:**

* `is_perishable` is intentionally not stored in this table. It is derived through `inventory.product_id → products.product_id`.
* `days_to_expiry` is not stored physically. It is calculated dynamically as:

```sql
expiry_date - date
```

* `expiry_date` must be on or after the inventory record date.

---

# 9. Table: complaints

Stores customer complaints and service-resolution details.

| Column                  | Data Type    | Description                                                         |
| ----------------------- | ------------ | ------------------------------------------------------------------- |
| `complaint_id`          | VARCHAR(20)  | Unique complaint identifier. Primary key.                           |
| `date`                  | DATE         | Date on which the complaint was registered.                         |
| `customer_id`           | VARCHAR(20)  | Identifier of the customer raising the complaint.                   |
| `store_id`              | VARCHAR(10)  | Store related to the complaint.                                     |
| `store_name`            | VARCHAR(150) | Store name.                                                         |
| `region`                | VARCHAR(50)  | Region of the store.                                                |
| `product_id`            | VARCHAR(10)  | Product related to the complaint.                                   |
| `product_name`          | VARCHAR(200) | Product name.                                                       |
| `category`              | VARCHAR(100) | Product category.                                                   |
| `complaint_type`        | VARCHAR(150) | Type of complaint, such as damaged packaging or out-of-stock issue. |
| `complaint_description` | TEXT         | Detailed complaint description.                                     |
| `severity`              | VARCHAR(20)  | Complaint severity: `High`, `Medium`, or `Low`.                     |
| `status`                | VARCHAR(50)  | Complaint status: `Open`, `In Progress`, `Resolved`, or `Closed`.   |
| `assigned_employee_id`  | VARCHAR(10)  | Employee assigned to resolve the complaint.                         |
| `resolution_time_days`  | INTEGER      | Number of days required to resolve the complaint.                   |

**Primary Key:** `complaint_id`
**Foreign Keys:**

* `store_id` → `stores.store_id`
* `product_id` → `products.product_id`
* `assigned_employee_id` → `employees.employee_id`

---

# 10. Table: finance

Stores store-level monthly financial performance and risk information.

| Column                       | Data Type     | Description                                                         |
| ---------------------------- | ------------- | ------------------------------------------------------------------- |
| `finance_id`                 | VARCHAR(20)   | Unique finance record identifier. Primary key.                      |
| `month`                      | VARCHAR(7)    | Financial month in `YYYY-MM` format.                                |
| `store_id`                   | VARCHAR(10)   | Store associated with the financial record.                         |
| `store_name`                 | VARCHAR(150)  | Store name.                                                         |
| `region`                     | VARCHAR(50)   | Store region.                                                       |
| `monthly_sales_target`       | NUMERIC(14,2) | Monthly sales target of the store.                                  |
| `total_revenue`              | NUMERIC(14,2) | Total revenue generated during the month.                           |
| `total_cost`                 | NUMERIC(14,2) | Total cost incurred during the month.                               |
| `gross_profit`               | NUMERIC(14,2) | Revenue minus total cost.                                           |
| `operating_expense`          | NUMERIC(14,2) | Operational expenses for the month.                                 |
| `operating_profit`           | NUMERIC(14,2) | Gross profit minus operating expense.                               |
| `target_achievement_percent` | NUMERIC(8,2)  | Percentage of monthly sales target achieved.                        |
| `risk_status`                | VARCHAR(50)   | Financial risk category: `High Risk`, `Medium Risk`, or `Low Risk`. |

**Primary Key:** `finance_id`
**Foreign Key:** `store_id` → `stores.store_id`

**Formula Rules:**

```text
gross_profit = total_revenue - total_cost

operating_profit = gross_profit - operating_expense

target_achievement_percent =
(total_revenue / monthly_sales_target) × 100
```

---

# 11. Table: vendor_deliveries

Stores purchase-order and vendor-delivery information.

| Column                   | Data Type     | Description                                                                                       |
| ------------------------ | ------------- | ------------------------------------------------------------------------------------------------- |
| `purchase_order_id`      | VARCHAR(20)   | Unique purchase-order identifier. Primary key.                                                    |
| `order_date`             | DATE          | Date on which the order was placed.                                                               |
| `expected_delivery_date` | DATE          | Planned delivery date.                                                                            |
| `actual_delivery_date`   | DATE          | Actual date on which delivery was received.                                                       |
| `store_id`               | VARCHAR(10)   | Store receiving the delivery.                                                                     |
| `store_name`             | VARCHAR(150)  | Store name.                                                                                       |
| `vendor_id`              | VARCHAR(10)   | Vendor fulfilling the order.                                                                      |
| `vendor_name`            | VARCHAR(150)  | Vendor name.                                                                                      |
| `product_id`             | VARCHAR(10)   | Product ordered.                                                                                  |
| `product_name`           | VARCHAR(200)  | Product name.                                                                                     |
| `ordered_quantity`       | INTEGER       | Quantity ordered from the vendor.                                                                 |
| `received_quantity`      | INTEGER       | Quantity actually received.                                                                       |
| `unit_cost`              | NUMERIC(12,2) | Cost per product unit.                                                                            |
| `purchase_value`         | NUMERIC(14,2) | Total purchase value of the order.                                                                |
| `delay_days`             | INTEGER       | Number of days by which delivery was delayed.                                                     |
| `delivery_status`        | VARCHAR(100)  | Delivery condition: `Delivered On Time`, `Delayed`, `Partial Delivery`, or `Delayed and Partial`. |
| `quality_rating`         | NUMERIC(3,1)  | Product quality rating from 0 to 5.                                                               |
| `assigned_employee_id`   | VARCHAR(10)   | Employee responsible for managing the delivery.                                                   |

**Primary Key:** `purchase_order_id`
**Foreign Keys:**

* `store_id` → `stores.store_id`
* `vendor_id` → `vendors.vendor_id`
* `product_id` → `products.product_id`
* `assigned_employee_id` → `employees.employee_id`

**Business Rules:**

* `expected_delivery_date` must be on or after `order_date`.
* `actual_delivery_date` must be on or after `expected_delivery_date`.
* `received_quantity` cannot exceed `ordered_quantity`.
* `delay_days` cannot be negative.

---

# 12. Table: data_import_logs

Stores audit information for each processed-data import operation.

| Column             | Data Type    | Description                                             |
| ------------------ | ------------ | ------------------------------------------------------- |
| `import_id`        | BIGINT       | Automatically generated import identifier. Primary key. |
| `dataset_name`     | VARCHAR(150) | Name of the imported dataset.                           |
| `source_file_name` | VARCHAR(250) | Name of the processed CSV file used for import.         |
| `total_rows`       | INTEGER      | Total rows detected in the source file.                 |
| `successful_rows`  | INTEGER      | Rows loaded successfully.                               |
| `failed_rows`      | INTEGER      | Rows that failed during import.                         |
| `import_status`    | VARCHAR(50)  | Import status, such as `Success` or `Failed`.           |
| `error_message`    | TEXT         | Error details if the import fails.                      |
| `imported_at`      | TIMESTAMP    | Date and time at which the import occurred.             |

**Primary Key:** `import_id`

**Business Rule:**

```text
successful_rows + failed_rows = total_rows
```

---

# 13. Key Relationships

```text
vendors
   └── products
          ├── sales
          ├── inventory
          ├── complaints
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
```

---

# 14. Future Database Expansion

The following system tables will be added in later phases of the project:

* `issues`
* `issue_evidence`
* `recommendations`
* `tasks`
* `automation_logs`
* `executive_briefs`
* `agent_runs`
* `audit_logs`

These tables will support AI-based issue detection, root-cause analysis, prioritization, human approval, Kanban task management, workflow automation, and executive reporting.
