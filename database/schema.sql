-- ==========================================================
-- AI-Powered Operating Intelligence Platform
-- PostgreSQL Schema for Cleaned Business Datasets
-- Database: ai_operating_intelligence
-- ==========================================================

-- This schema creates only the current business-data tables.
-- AI system tables such as issues, recommendations, tasks,
-- automation_logs, and agent_runs will be added later.

-- ==========================================================
-- 1. MASTER DATA TABLES
-- ==========================================================

CREATE TABLE IF NOT EXISTS vendors (
    vendor_id VARCHAR(10) PRIMARY KEY,
    vendor_name VARCHAR(150) NOT NULL,
    vendor_category VARCHAR(100),
    contact_person VARCHAR(150),
    city VARCHAR(100),
    state VARCHAR(100),
    region VARCHAR(50),
    average_delivery_days INTEGER
        CHECK (average_delivery_days >= 0),
    rating NUMERIC(3, 1)
        CHECK (rating >= 0 AND rating <= 5),
    payment_terms VARCHAR(100),
    supply_status VARCHAR(50)
);

-- Employees are created before stores because stores.manager_id
-- references employees.employee_id.
-- employees.store_id is intentionally not a foreign key because
-- some department-level employees can have store_id = 'ALL'.

CREATE TABLE IF NOT EXISTS employees (
    employee_id VARCHAR(10) PRIMARY KEY,
    employee_name VARCHAR(150) NOT NULL,
    role VARCHAR(100),
    department VARCHAR(100),
    store_id VARCHAR(10),
    region VARCHAR(50),
    email VARCHAR(150),
    monthly_target NUMERIC(14, 2)
        CHECK (monthly_target >= 0),
    performance_status VARCHAR(50),
    employment_status VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR(10) PRIMARY KEY,
    store_name VARCHAR(150) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100),
    region VARCHAR(50),
    store_type VARCHAR(100),
    manager_id VARCHAR(10) NOT NULL,
    opening_date DATE NOT NULL,
    monthly_sales_target NUMERIC(14, 2)
        CHECK (monthly_sales_target >= 0),
    operational_status VARCHAR(50),

    CONSTRAINT fk_stores_manager
        FOREIGN KEY (manager_id)
        REFERENCES employees(employee_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(10) PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(100),
    sub_category VARCHAR(100),
    brand VARCHAR(100),
    unit_price NUMERIC(12, 2)
        CHECK (unit_price >= 0),
    cost_price NUMERIC(12, 2)
        CHECK (cost_price >= 0),
    margin_percent NUMERIC(6, 2)
        CHECK (margin_percent >= 0 AND margin_percent <= 100),
    reorder_level INTEGER
        CHECK (reorder_level >= 0),
    shelf_life_days INTEGER,
    is_perishable VARCHAR(3) NOT NULL
        CHECK (is_perishable IN ('Yes', 'No')),
    vendor_id VARCHAR(10) NOT NULL,

    CONSTRAINT chk_product_shelf_life
        CHECK (
            (is_perishable = 'Yes' AND shelf_life_days > 0)
            OR
            (is_perishable = 'No' AND shelf_life_days IS NULL)
        ),

    CONSTRAINT fk_products_vendor
        FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- ==========================================================
-- 2. TRANSACTIONAL AND OPERATIONAL TABLES
-- ==========================================================

CREATE TABLE IF NOT EXISTS sales (
    sale_id VARCHAR(20) PRIMARY KEY,
    date DATE NOT NULL,
    store_id VARCHAR(10) NOT NULL,
    store_name VARCHAR(150),
    region VARCHAR(50),
    product_id VARCHAR(10) NOT NULL,
    product_name VARCHAR(200),
    category VARCHAR(100),
    employee_id VARCHAR(10),
    quantity_sold INTEGER NOT NULL
        CHECK (quantity_sold >= 0),
    unit_price NUMERIC(12, 2) NOT NULL
        CHECK (unit_price >= 0),
    discount_percent NUMERIC(6, 2) NOT NULL DEFAULT 0
        CHECK (discount_percent >= 0 AND discount_percent <= 100),
    total_sales NUMERIC(14, 2) NOT NULL
        CHECK (total_sales >= 0),
    total_cost NUMERIC(14, 2) NOT NULL
        CHECK (total_cost >= 0),
    profit NUMERIC(14, 2),
    payment_status VARCHAR(50),

    CONSTRAINT fk_sales_store
        FOREIGN KEY (store_id)
        REFERENCES stores(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_sales_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_sales_employee
        FOREIGN KEY (employee_id)
        REFERENCES employees(employee_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- is_perishable is intentionally absent here.
-- Perishability is derived through inventory.product_id -> products.product_id.

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id VARCHAR(20) PRIMARY KEY,
    date DATE NOT NULL,
    store_id VARCHAR(10) NOT NULL,
    store_name VARCHAR(150),
    product_id VARCHAR(10) NOT NULL,
    product_name VARCHAR(200),
    category VARCHAR(100),
    vendor_id VARCHAR(10) NOT NULL,
    current_stock INTEGER NOT NULL
        CHECK (current_stock >= 0),
    reorder_level INTEGER NOT NULL
        CHECK (reorder_level >= 0),
    stock_status VARCHAR(50) NOT NULL
        CHECK (
            stock_status IN (
                'Low Stock',
                'Reorder Soon',
                'Overstock',
                'Normal'
            )
        ),
    reorder_required VARCHAR(3) NOT NULL
        CHECK (reorder_required IN ('Yes', 'No')),
    expiry_date DATE,

    CONSTRAINT chk_inventory_expiry_date
        CHECK (
            expiry_date IS NULL
            OR expiry_date >= date
        ),

    CONSTRAINT fk_inventory_store
        FOREIGN KEY (store_id)
        REFERENCES stores(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_inventory_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_inventory_vendor
        FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS complaints (
    complaint_id VARCHAR(20) PRIMARY KEY,
    date DATE NOT NULL,
    customer_id VARCHAR(20),
    store_id VARCHAR(10) NOT NULL,
    store_name VARCHAR(150),
    region VARCHAR(50),
    product_id VARCHAR(10) NOT NULL,
    product_name VARCHAR(200),
    category VARCHAR(100),
    complaint_type VARCHAR(150),
    complaint_description TEXT,
    severity VARCHAR(20) NOT NULL
        CHECK (severity IN ('High', 'Medium', 'Low')),
    status VARCHAR(50) NOT NULL
        CHECK (
            status IN (
                'Open',
                'In Progress',
                'Resolved',
                'Closed'
            )
        ),
    assigned_employee_id VARCHAR(10),
    resolution_time_days INTEGER
        CHECK (
            resolution_time_days IS NULL
            OR resolution_time_days >= 0
        ),

    CONSTRAINT fk_complaints_store
        FOREIGN KEY (store_id)
        REFERENCES stores(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_complaints_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_complaints_employee
        FOREIGN KEY (assigned_employee_id)
        REFERENCES employees(employee_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS finance (
    finance_id VARCHAR(20) PRIMARY KEY,
    month VARCHAR(7) NOT NULL
        CHECK (
            month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'
        ),
    store_id VARCHAR(10) NOT NULL,
    store_name VARCHAR(150),
    region VARCHAR(50),
    monthly_sales_target NUMERIC(14, 2)
        CHECK (monthly_sales_target >= 0),
    total_revenue NUMERIC(14, 2)
        CHECK (total_revenue >= 0),
    total_cost NUMERIC(14, 2)
        CHECK (total_cost >= 0),
    gross_profit NUMERIC(14, 2),
    operating_expense NUMERIC(14, 2)
        CHECK (operating_expense >= 0),
    operating_profit NUMERIC(14, 2),
    target_achievement_percent NUMERIC(8, 2)
        CHECK (
            target_achievement_percent >= 0
            AND target_achievement_percent <= 1000
        ),
    risk_status VARCHAR(50) NOT NULL
        CHECK (
            risk_status IN (
                'High Risk',
                'Medium Risk',
                'Low Risk'
            )
        ),

    CONSTRAINT fk_finance_store
        FOREIGN KEY (store_id)
        REFERENCES stores(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS vendor_deliveries (
    purchase_order_id VARCHAR(20) PRIMARY KEY,
    order_date DATE NOT NULL,
    expected_delivery_date DATE NOT NULL,
    actual_delivery_date DATE NOT NULL,
    store_id VARCHAR(10) NOT NULL,
    store_name VARCHAR(150),
    vendor_id VARCHAR(10) NOT NULL,
    vendor_name VARCHAR(150),
    product_id VARCHAR(10) NOT NULL,
    product_name VARCHAR(200),
    ordered_quantity INTEGER NOT NULL
        CHECK (ordered_quantity >= 0),
    received_quantity INTEGER NOT NULL
        CHECK (
            received_quantity >= 0
            AND received_quantity <= ordered_quantity
        ),
    unit_cost NUMERIC(12, 2) NOT NULL
        CHECK (unit_cost >= 0),
    purchase_value NUMERIC(14, 2) NOT NULL
        CHECK (purchase_value >= 0),
    delay_days INTEGER NOT NULL
        CHECK (delay_days >= 0),
    delivery_status VARCHAR(100) NOT NULL
        CHECK (
            delivery_status IN (
                'Delivered On Time',
                'Delayed',
                'Partial Delivery',
                'Delayed and Partial'
            )
        ),
    quality_rating NUMERIC(3, 1)
        CHECK (
            quality_rating >= 0
            AND quality_rating <= 5
        ),
    assigned_employee_id VARCHAR(10),

    CONSTRAINT chk_vendor_delivery_dates
        CHECK (
            expected_delivery_date >= order_date
            AND actual_delivery_date >= expected_delivery_date
        ),

    CONSTRAINT fk_vendor_deliveries_store
        FOREIGN KEY (store_id)
        REFERENCES stores(store_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_vendor_deliveries_vendor
        FOREIGN KEY (vendor_id)
        REFERENCES vendors(vendor_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_vendor_deliveries_product
        FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_vendor_deliveries_employee
        FOREIGN KEY (assigned_employee_id)
        REFERENCES employees(employee_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

-- ==========================================================
-- 3. DATA IMPORT LOG
-- ==========================================================

CREATE TABLE IF NOT EXISTS data_import_logs (
    import_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_name VARCHAR(150) NOT NULL,
    source_file_name VARCHAR(250) NOT NULL,
    total_rows INTEGER NOT NULL
        CHECK (total_rows >= 0),
    successful_rows INTEGER NOT NULL
        CHECK (successful_rows >= 0),
    failed_rows INTEGER NOT NULL
        CHECK (failed_rows >= 0),
    import_status VARCHAR(50) NOT NULL,
    error_message TEXT,
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_import_row_counts
        CHECK (
            successful_rows + failed_rows = total_rows
        )
);

-- ==========================================================
-- 4. INDEXES FOR ANALYTICS AND API QUERIES
-- ==========================================================

CREATE INDEX IF NOT EXISTS idx_sales_date
ON sales(date);

CREATE INDEX IF NOT EXISTS idx_sales_store_id
ON sales(store_id);

CREATE INDEX IF NOT EXISTS idx_sales_product_id
ON sales(product_id);

CREATE INDEX IF NOT EXISTS idx_inventory_store_product
ON inventory(store_id, product_id);

CREATE INDEX IF NOT EXISTS idx_inventory_stock_status
ON inventory(stock_status);

CREATE INDEX IF NOT EXISTS idx_complaints_store_id
ON complaints(store_id);

CREATE INDEX IF NOT EXISTS idx_complaints_product_id
ON complaints(product_id);

CREATE INDEX IF NOT EXISTS idx_complaints_status
ON complaints(status);

CREATE INDEX IF NOT EXISTS idx_finance_store_month
ON finance(store_id, month);

CREATE INDEX IF NOT EXISTS idx_finance_risk_status
ON finance(risk_status);

CREATE INDEX IF NOT EXISTS idx_vendor_deliveries_vendor_id
ON vendor_deliveries(vendor_id);

CREATE INDEX IF NOT EXISTS idx_vendor_deliveries_actual_date
ON vendor_deliveries(actual_delivery_date);

CREATE INDEX IF NOT EXISTS idx_data_import_logs_imported_at
ON data_import_logs(imported_at);