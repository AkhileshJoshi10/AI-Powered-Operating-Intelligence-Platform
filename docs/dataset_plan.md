# Dataset Plan

## 1. Purpose

This document defines the datasets used in the **AI-Powered Operating Intelligence Platform** for SmartMart Retail Pvt. Ltd.

The datasets support:

- Business monitoring
- KPI calculation
- Issue detection
- Priority ranking
- Root-cause analysis
- AI recommendations
- Task tracking
- Workflow automation

---

## 2. Data Period and Date Format

### Data Period

01-01-2026 to 30-06-2026

### Date Format

All full date columns use:

`%d-%m-%y`

Example:

`30-06-26`

The `month` column in `finance_data.csv` uses:

`YYYY-MM`

Example:

`2026-06`

---

## 3. Datasets Used

| Dataset | Type | Main Purpose |
|---|---|---|
| `products_data.csv` | Master Data | Stores product, price, cost, shelf-life, reorder-level, and vendor information. |
| `stores_data.csv` | Master Data | Stores store location, manager, sales target, and operational details. |
| `vendors_data.csv` | Master Data | Stores vendor details, delivery expectations, rating, payment terms, and supply status. |
| `employees_data.csv` | Master Data | Stores employee roles, departments, store assignment, targets, and performance status. |
| `sales_data.csv` | Transaction Data | Stores product-level sales transactions across stores. |
| `inventory_data.csv` | Operational Data | Stores current stock, reorder status, expiry information, and inventory risks. |
| `complaints_data.csv` | Customer Support Data | Stores customer complaints, severity, status, assignment, and resolution details. |
| `finance_data.csv` | Financial Summary Data | Stores monthly revenue, cost, profit, operating expense, target achievement, and risk. |
| `vendor_deliveries_data.csv` | Procurement Data | Stores purchase orders, delivery delays, partial deliveries, and quality ratings. |

---

## 4. Dataset Details

### 4.1 Products Dataset

**File:** `products_data.csv`  
**Primary Key:** `product_id`

Important columns:

- `product_id`
- `product_name`
- `category`
- `sub_category`
- `brand`
- `unit_price`
- `cost_price`
- `margin_percent`
- `reorder_level`
- `shelf_life_days`
- `vendor_id`

Purpose:

- Connect products with vendors.
- Calculate product-level revenue, cost, and profitability.
- Support sales analysis, inventory analysis, complaint analysis, and vendor analysis.
- Identify low-selling, low-stock, overstocked, or high-complaint products.

---

### 4.2 Stores Dataset

**File:** `stores_data.csv`  
**Primary Key:** `store_id`

Columns:

- `store_id`
- `store_name`
- `city`
- `state`
- `region`
- `store_type`
- `manager_id`
- `opening_date`
- `monthly_sales_target`
- `operational_status`

Purpose:

- Track store-level performance.
- Compare revenue with monthly sales targets.
- Identify underperforming stores.
- Connect each store with its assigned manager.

---

### 4.3 Vendors Dataset

**File:** `vendors_data.csv`  
**Primary Key:** `vendor_id`

Columns:

- `vendor_id`
- `vendor_name`
- `vendor_category`
- `contact_person`
- `city`
- `state`
- `region`
- `average_delivery_days`
- `rating`
- `payment_terms`
- `supply_status`

Purpose:

- Maintain vendor master information.
- Support procurement and vendor-performance analysis.
- Connect vendors with products, inventory, and delivery records.

---

### 4.4 Employees Dataset

**File:** `employees_data.csv`  
**Primary Key:** `employee_id`

Columns:

- `employee_id`
- `employee_name`
- `role`
- `department`
- `store_id`
- `region`
- `email`
- `monthly_target`
- `performance_status`
- `employment_status`

Purpose:

- Identify store managers and department owners.
- Assign recommendations and tasks to responsible employees.
- Track employee roles and business responsibility.

Note:

Sales-related roles have monthly targets.

Non-sales roles can have `monthly_target = 0` because they are evaluated using different KPIs such as inventory accuracy, complaint resolution, vendor performance, or financial reporting.

---

### 4.5 Sales Dataset

**File:** `sales_data.csv`  
**Primary Key:** `sale_id`

Columns:

- `sale_id`
- `date`
- `store_id`
- `store_name`
- `region`
- `product_id`
- `product_name`
- `category`
- `employee_id`
- `quantity_sold`
- `unit_price`
- `discount_percent`
- `total_sales`
- `total_cost`
- `profit`
- `payment_status`

Purpose:

- Calculate total sales, revenue, cost, profit, and sales trends.
- Detect sales decline by store, product, category, or region.
- Identify store and product underperformance.
- Measure employee-related sales contribution where applicable.

---

### 4.6 Inventory Dataset

**File:** `inventory_data.csv`  
**Primary Key:** `inventory_id`

Columns:

- `inventory_id`
- `date`
- `store_id`
- `store_name`
- `product_id`
- `product_name`
- `category`
- `vendor_id`
- `current_stock`
- `reorder_level`
- `stock_status`
- `reorder_required`
- `expiry_date`
- `days_to_expiry`

Purpose:

- Detect low-stock products.
- Identify reorder-soon products.
- Detect overstock conditions.
- Identify stockout risk.
- Detect near-expiry and expired products.

---

### 4.7 Complaints Dataset

**File:** `complaints_data.csv`  
**Primary Key:** `complaint_id`

Important columns:

- `complaint_id`
- `date`
- `store_id`
- `store_name`
- `product_id`
- `product_name`
- `category`
- `complaint_type`
- `complaint_description`
- `severity`
- `status`
- `assigned_employee_id`
- `resolution_time_days`

Purpose:

- Identify high-complaint products and stores.
- Detect high-severity and unresolved complaints.
- Analyze complaint categories.
- Support customer-service and product-quality recommendations.

---

### 4.8 Finance Dataset

**File:** `finance_data.csv`  
**Primary Key:** `finance_id`

Columns:

- `finance_id`
- `month`
- `store_id`
- `store_name`
- `region`
- `monthly_sales_target`
- `total_revenue`
- `total_cost`
- `gross_profit`
- `operating_expense`
- `operating_profit`
- `target_achievement_percent`
- `risk_status`

Purpose:

- Monitor monthly store-level financial performance.
- Detect low target achievement.
- Identify low-profit or loss-making store/month combinations.
- Identify financial-risk stores.

Formulas:

`gross_profit = total_revenue - total_cost`

`operating_profit = gross_profit - operating_expense`

Important Note:

The current finance dataset does not include pending payments, receivables, or payment-delay information.

Those will be added later only through a separate `receivables_data.csv` dataset if the project needs payment collection analysis.

---

### 4.9 Vendor Deliveries Dataset

**File:** `vendor_deliveries_data.csv`  
**Primary Key:** `purchase_order_id`

Columns:

- `purchase_order_id`
- `order_date`
- `expected_delivery_date`
- `actual_delivery_date`
- `store_id`
- `store_name`
- `vendor_id`
- `vendor_name`
- `product_id`
- `product_name`
- `ordered_quantity`
- `received_quantity`
- `unit_cost`
- `purchase_value`
- `delay_days`
- `delivery_status`
- `quality_rating`
- `assigned_employee_id`

Purpose:

- Detect repeated vendor delays.
- Identify partial deliveries.
- Measure vendor quality ratings.
- Identify procurement and supply-chain risks.
- Support recommendations for procurement managers.

---

## 5. Dataset Relationships

### Vendor Relationships

`vendors_data.vendor_id`

connects with:

- `products_data.vendor_id`
- `inventory_data.vendor_id`
- `vendor_deliveries_data.vendor_id`

### Product Relationships

`products_data.product_id`

connects with:

- `sales_data.product_id`
- `inventory_data.product_id`
- `complaints_data.product_id`
- `vendor_deliveries_data.product_id`

### Store Relationships

`stores_data.store_id`

connects with:

- `sales_data.store_id`
- `inventory_data.store_id`
- `complaints_data.store_id`
- `finance_data.store_id`
- `vendor_deliveries_data.store_id`

### Employee Relationships

`employees_data.employee_id`

connects with:

- `stores_data.manager_id`
- `sales_data.employee_id`
- `complaints_data.assigned_employee_id`
- `vendor_deliveries_data.assigned_employee_id`

---

## 6. Main Relationship Summary

| Child Dataset | Linking Column | Parent Dataset | Parent Column |
|---|---|---|---|
| Products | `vendor_id` | Vendors | `vendor_id` |
| Stores | `manager_id` | Employees | `employee_id` |
| Sales | `store_id` | Stores | `store_id` |
| Sales | `product_id` | Products | `product_id` |
| Sales | `employee_id` | Employees | `employee_id` |
| Inventory | `store_id` | Stores | `store_id` |
| Inventory | `product_id` | Products | `product_id` |
| Inventory | `vendor_id` | Vendors | `vendor_id` |
| Complaints | `store_id` | Stores | `store_id` |
| Complaints | `product_id` | Products | `product_id` |
| Finance | `store_id` | Stores | `store_id` |
| Vendor Deliveries | `store_id` | Stores | `store_id` |
| Vendor Deliveries | `vendor_id` | Vendors | `vendor_id` |
| Vendor Deliveries | `product_id` | Products | `product_id` |

---

## 7. Business Scenarios Included

The synthetic data intentionally contains business problems that the platform should identify.

### Sales Decline Scenario

Store `S003` has a major sales decline in June 2026.

### Complaint Scenario

Store `S003` has increased complaints in June, especially for selected packaged-food products.

### Inventory Risk Scenario

Selected products in Store `S003` and Store `S005` have low-stock risk.

### Overstock Scenario

Store `S007` has overstock for selected grocery products.

### Vendor Performance Scenario

Vendor `V004` and Vendor `V009` have recurring delivery delays.

Vendor `V009` also has lower quality ratings in some delivery records.

### Financial Risk Scenario

Financial risk is determined using operating profit and target-achievement percentage.

---

## 8. Dataset Validation Status

The datasets have been validated for:

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

Final validation result:

`No validation errors found.`

`No validation warnings found.`

---

## 9. Future Datasets Only When Required

Additional datasets will be added only when a real feature requires them.

| Future Dataset | Purpose |
|---|---|
| `customers_data.csv` | Customer segmentation, loyalty, repeat purchases, and churn analysis. |
| `receivables_data.csv` | Pending payment, collection, overdue-payment, and delay analysis. |
| `marketing_campaigns.csv` | Campaign performance and marketing ROI analysis. |
| `employee_attendance.csv` | Workforce productivity and HR analysis. |
| `supplier_contracts.csv` | Vendor contract and compliance analysis. |
| `documents/` | RAG-based analysis of policies, SOPs, contracts, and reports. |