-- ==========================================================
-- AI-Powered Operating Intelligence Platform
-- Sample PostgreSQL Analytics Queries
-- ==========================================================

-- ==========================================================
-- 1. TABLE ROW-COUNT VERIFICATION
-- ==========================================================

SELECT 'vendors' AS table_name, COUNT(*) AS row_count FROM vendors
UNION ALL
SELECT 'employees', COUNT(*) FROM employees
UNION ALL
SELECT 'stores', COUNT(*) FROM stores
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sales', COUNT(*) FROM sales
UNION ALL
SELECT 'inventory', COUNT(*) FROM inventory
UNION ALL
SELECT 'complaints', COUNT(*) FROM complaints
UNION ALL
SELECT 'finance', COUNT(*) FROM finance
UNION ALL
SELECT 'vendor_deliveries', COUNT(*) FROM vendor_deliveries
ORDER BY table_name;

-- Check history of all loaded data
SELECT
    dataset_name,
    source_file_name,
    total_rows,
    successful_rows,
    failed_rows,
    import_status,
    imported_at
FROM data_import_logs
ORDER BY import_id;

-- Check latest import status for each dataset
WITH latest_imports AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY dataset_name
            ORDER BY imported_at DESC
        ) AS row_num
    FROM data_import_logs
)
SELECT
    dataset_name,
    source_file_name,
    total_rows,
    successful_rows,
    failed_rows,
    import_status,
    imported_at
FROM latest_imports
WHERE row_num = 1
ORDER BY dataset_name;

-- ==========================================================
-- 2. MONTHLY SALES AND PROFIT TREND
-- ==========================================================

SELECT
    TO_CHAR(date, 'YYYY-MM') AS month,
    ROUND(SUM(total_sales), 2) AS total_sales,
    ROUND(SUM(profit), 2) AS total_profit,
    COUNT(*) AS transaction_count
FROM sales
GROUP BY TO_CHAR(date, 'YYYY-MM')
ORDER BY month;


-- ==========================================================
-- 3. STORE PERFORMANCE SUMMARY
-- ==========================================================

SELECT
    s.store_id,
    s.store_name,
    ROUND(SUM(s.total_sales), 2) AS total_sales,
    ROUND(SUM(s.profit), 2) AS total_profit,
    COUNT(s.sale_id) AS transaction_count
FROM sales AS s
GROUP BY
    s.store_id,
    s.store_name
ORDER BY total_sales DESC;


-- ==========================================================
-- 4. LOW-STOCK AND REORDER ITEMS
-- ==========================================================

SELECT
    i.inventory_id,
    i.store_id,
    i.store_name,
    i.product_id,
    i.product_name,
    i.current_stock,
    i.reorder_level,
    i.stock_status,
    i.reorder_required,
    p.is_perishable,
    i.expiry_date,
    CASE
        WHEN i.expiry_date IS NOT NULL
        THEN i.expiry_date - i.date
        ELSE NULL
    END AS days_to_expiry
FROM inventory AS i
JOIN products AS p
    ON i.product_id = p.product_id
WHERE i.stock_status IN ('Low Stock', 'Reorder Soon')
ORDER BY
    CASE
        WHEN i.stock_status = 'Low Stock' THEN 1
        ELSE 2
    END,
    i.current_stock ASC;


-- ==========================================================
-- 5. INVENTORY STATUS SUMMARY
-- ==========================================================

SELECT
    stock_status,
    COUNT(*) AS inventory_records,
    SUM(current_stock) AS total_current_stock
FROM inventory
GROUP BY stock_status
ORDER BY inventory_records DESC;


-- ==========================================================
-- 6. COMPLAINTS BY STORE
-- ==========================================================

SELECT
    store_id,
    store_name,
    COUNT(*) AS complaint_count,
    SUM(
        CASE
            WHEN severity = 'High' THEN 1
            ELSE 0
        END
    ) AS high_severity_complaints
FROM complaints
GROUP BY
    store_id,
    store_name
ORDER BY complaint_count DESC;


-- ==========================================================
-- 7. PRODUCTS WITH HIGHEST COMPLAINTS
-- ==========================================================

SELECT
    product_id,
    product_name,
    COUNT(*) AS complaint_count,
    SUM(
        CASE
            WHEN severity = 'High' THEN 1
            ELSE 0
        END
    ) AS high_severity_complaints
FROM complaints
GROUP BY
    product_id,
    product_name
ORDER BY complaint_count DESC
LIMIT 10;


-- ==========================================================
-- 8. VENDOR DELIVERY PERFORMANCE
-- ==========================================================

SELECT
    vendor_id,
    vendor_name,
    COUNT(*) AS delivery_count,
    ROUND(AVG(delay_days), 2) AS average_delay_days,
    MAX(delay_days) AS maximum_delay_days,
    ROUND(AVG(quality_rating), 2) AS average_quality_rating,
    ROUND(SUM(purchase_value), 2) AS total_purchase_value
FROM vendor_deliveries
GROUP BY
    vendor_id,
    vendor_name
ORDER BY average_delay_days DESC;


-- ==========================================================
-- 9. FINANCE RISK SUMMARY
-- ==========================================================

SELECT
    finance_id,
    month,
    store_id,
    store_name,
    monthly_sales_target,
    total_revenue,
    operating_profit,
    target_achievement_percent,
    risk_status
FROM finance
WHERE risk_status = 'High Risk'
ORDER BY
    month DESC,
    target_achievement_percent ASC;


-- ==========================================================
-- 10. SMARTMART CLOCK TOWER PRIORITY-ISSUE VIEW
-- ==========================================================

SELECT
    f.month,
    f.store_id,
    f.store_name,
    f.total_revenue,
    f.operating_profit,
    f.target_achievement_percent,
    f.risk_status,
    complaint_summary.complaint_count,
    inventory_summary.low_stock_items,
    inventory_summary.reorder_soon_items
FROM finance AS f
LEFT JOIN (
    SELECT
        store_id,
        COUNT(*) AS complaint_count
    FROM complaints
    GROUP BY store_id
) AS complaint_summary
    ON f.store_id = complaint_summary.store_id
LEFT JOIN (
    SELECT
        store_id,
        SUM(
            CASE
                WHEN stock_status = 'Low Stock' THEN 1
                ELSE 0
            END
        ) AS low_stock_items,
        SUM(
            CASE
                WHEN stock_status = 'Reorder Soon' THEN 1
                ELSE 0
            END
        ) AS reorder_soon_items
    FROM inventory
    GROUP BY store_id
) AS inventory_summary
    ON f.store_id = inventory_summary.store_id
WHERE f.store_id = 'S003'
ORDER BY f.month;


-- ==========================================================
-- 11. INITIAL PRIORITY ISSUE CANDIDATES
-- ==========================================================

SELECT
    i.store_id,
    i.store_name,
    i.product_id,
    i.product_name,
    i.current_stock,
    i.reorder_level,
    i.stock_status,
    COUNT(c.complaint_id) AS related_complaints,
    SUM(
        CASE
            WHEN c.severity = 'High' THEN 1
            ELSE 0
        END
    ) AS related_high_severity_complaints
FROM inventory AS i
LEFT JOIN complaints AS c
    ON i.store_id = c.store_id
    AND i.product_id = c.product_id
WHERE i.stock_status = 'Low Stock'
GROUP BY
    i.store_id,
    i.store_name,
    i.product_id,
    i.product_name,
    i.current_stock,
    i.reorder_level,
    i.stock_status
ORDER BY
    related_high_severity_complaints DESC,
    related_complaints DESC,
    i.current_stock ASC;

	
-- ==========================================================
-- 12. TOP 10 PRODUCTS BY SALES
-- ==========================================================

SELECT
    product_id,
    product_name,
    ROUND(SUM(total_sales), 2) AS total_sales,
    ROUND(SUM(profit), 2) AS total_profit,
    SUM(quantity_sold) AS quantity_sold
FROM sales
GROUP BY
    product_id,
    product_name
ORDER BY total_sales DESC
LIMIT 10;

-- ==========================================================
-- 13. OVERSTOCK ITEMS
-- ==========================================================

SELECT
    inventory_id,
    store_id,
    store_name,
    product_id,
    product_name,
    current_stock,
    reorder_level,
    stock_status
FROM inventory
WHERE stock_status = 'Overstock'
ORDER BY current_stock DESC;

-- ==========================================================
-- 14. CROSS-FUNCTIONAL STORE RISK SUMMARY
-- Combines sales, complaints, inventory, and finance.
-- ==========================================================

WITH store_sales AS (
    SELECT
        store_id,
        ROUND(SUM(total_sales), 2) AS total_sales,
        ROUND(SUM(profit), 2) AS total_profit
    FROM sales
    GROUP BY store_id
),
store_complaints AS (
    SELECT
        store_id,
        COUNT(complaint_id) AS complaint_count,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints
    FROM complaints
    GROUP BY store_id
),
store_inventory AS (
    SELECT
        store_id,
        COUNT(*) FILTER (
            WHERE stock_status = 'Low Stock'
        ) AS low_stock_items,
        COUNT(*) FILTER (
            WHERE stock_status = 'Reorder Soon'
        ) AS reorder_soon_items,
        COUNT(*) FILTER (
            WHERE stock_status = 'Overstock'
        ) AS overstock_items
    FROM inventory
    GROUP BY store_id
),
latest_finance AS (
    SELECT DISTINCT ON (store_id)
        store_id,
        month,
        target_achievement_percent,
        operating_profit,
        risk_status
    FROM finance
    ORDER BY
        store_id,
        month DESC
)
SELECT
    stores.store_id,
    stores.store_name,
    store_sales.total_sales,
    store_sales.total_profit,
    store_complaints.complaint_count,
    store_complaints.high_severity_complaints,
    store_inventory.low_stock_items,
    store_inventory.reorder_soon_items,
    store_inventory.overstock_items,
    latest_finance.month AS latest_finance_month,
    latest_finance.target_achievement_percent,
    latest_finance.operating_profit,
    latest_finance.risk_status
FROM stores
LEFT JOIN store_sales
    ON stores.store_id = store_sales.store_id
LEFT JOIN store_complaints
    ON stores.store_id = store_complaints.store_id
LEFT JOIN store_inventory
    ON stores.store_id = store_inventory.store_id
LEFT JOIN latest_finance
    ON stores.store_id = latest_finance.store_id
ORDER BY
    latest_finance.target_achievement_percent ASC NULLS LAST,
    store_complaints.complaint_count DESC NULLS LAST;