# Root Cause Analysis Report

## AI-Powered Operating Intelligence Platform

**Generated At:** 2026-06-30 16:47:26

This report provides evidence-based probable root causes for High and Medium priority issues. The findings are generated from PostgreSQL business data using deterministic analytics rules.

## Analysis Scope

- Only High and Medium priority issues are analyzed.
- Findings indicate evidence-supported probable causes, not unverified assumptions.
- AI agents will later use these structured findings to prepare recommendations and executive briefs.

## Analysis Summary

| Priority | Analyses |
|---|---:|
| High | 7 |
| Medium | 14 |

## Root Cause Summary

| Priority | Business Area | Issue | Primary Root Cause |
|---|---|---|---|
| High | Procurement | Vendor delivery risk: TechEase Accessories | Repeated delivery-performance exceptions are affecting supplier reliability. |
| High | Procurement | Vendor delivery risk: CoolSip Distributors | Repeated delivery-performance exceptions are affecting supplier reliability. |
| High | Customer Support | Customer complaint hotspot at SmartMart Clock Tower | A concentrated volume of customer complaints has accumulated at the store. |
| High | Sales | Major sales decline at SmartMart Clock Tower | Store revenue declined by 57.86% in 2026-06 compared with 2026-05. |
| High | Finance | High financial risk at SmartMart Clock Tower | Severe underachievement of the sales target: the store achieved only 28.87% of its target in 2026-06. |
| High | Finance | High financial risk at SmartMart Rajpur Road | Severe underachievement of the sales target: the store achieved only 69.36% of its target in 2026-06. |
| High | Operations | Low-stock risk: Instant Noodles Pack at SmartMart Clock Tower | Stock is at 5.00% of its reorder level (5 units available against a reorder level of 100). |
| Medium | Procurement | Vendor delivery risk: GlowCare Personal Products | Repeated delivery-performance exceptions are affecting supplier reliability. |
| Medium | Operations | Low-stock risk: Biscuits 300g at SmartMart Clock Tower | Stock is at 40.00% of its reorder level (36 units available against a reorder level of 90). |
| Medium | Procurement | Vendor delivery risk: FreshDrop Oils | Repeated delivery-performance exceptions are affecting supplier reliability. |
| Medium | Operations | Low-stock risk: Chips 150g at SmartMart Clock Tower | Stock is at 59.00% of its reorder level (59 units available against a reorder level of 100). |
| Medium | Procurement | Vendor delivery risk: QuickBite Foods | Repeated delivery-performance exceptions are affecting supplier reliability. |
| Medium | Procurement | Vendor delivery risk: GrainPro Suppliers | Repeated delivery-performance exceptions are affecting supplier reliability. |
| Medium | Procurement | Vendor delivery risk: BrewLeaf Beverages | Repeated delivery-performance exceptions are affecting supplier reliability. |
| Medium | Operations | Low-stock risk: Packaged Juice 1L at SmartMart Mussoorie | Stock is at 14.00% of its reorder level (7 units available against a reorder level of 50). |
| Medium | Operations | Low-stock risk: Dishwash Liquid 500ml at SmartMart Haridwar Central | Stock is at 17.78% of its reorder level (8 units available against a reorder level of 45). |
| Medium | Operations | Low-stock risk: Chips 150g at SmartMart Mussoorie | Stock is at 19.00% of its reorder level (19 units available against a reorder level of 100). |
| Medium | Procurement | Vendor delivery risk: WriteWell Stationery | Repeated delivery-performance exceptions are affecting supplier reliability. |
| Medium | Operations | Low-stock risk: Earphones at SmartMart Mussoorie | Stock is at 16.00% of its reorder level (4 units available against a reorder level of 25). |
| Medium | Operations | Low-stock risk: Packaged Juice 1L at SmartMart Roorkee | Stock is at 22.00% of its reorder level (11 units available against a reorder level of 50). |
| Medium | Operations | Low-stock risk: Shampoo 180ml at SmartMart Mussoorie | Stock is at 25.00% of its reorder level (10 units available against a reorder level of 40). |

## Detailed Root Cause Analyses

### RCA-VENDOR-V009 — Vendor delivery risk: TechEase Accessories

**Priority:** High (97.50)

**Business Area:** Procurement

**Primary Root Cause:** Repeated delivery-performance exceptions are affecting supplier reliability.

**Contributing Factors:** The maximum observed delivery delay is 15 days. 6 deliveries were delayed. 1 deliveries were partial. The most affected store is SmartMart Haridwar Central, where the average delay is 15.00 days.

**Evidence Summary:** Vendor: TechEase Accessories; Delivery Count: 8; Average Delay: 4.38 days; Maximum Delay: 15 days; Average Quality Rating: 4.00.

**Investigation Focus:** Review vendor service-level agreement compliance, purchase-order planning, supply capacity, product quality checks, and backup supplier availability.

### RCA-VENDOR-V004 — Vendor delivery risk: CoolSip Distributors

**Priority:** High (96.50)

**Business Area:** Procurement

**Primary Root Cause:** Repeated delivery-performance exceptions are affecting supplier reliability.

**Contributing Factors:** The maximum observed delivery delay is 15 days. 6 deliveries were delayed. 1 deliveries were partial. Average quality rating is 3.62 out of 5. The most affected store is SmartMart Kashipur, where the average delay is 15.00 days.

**Evidence Summary:** Vendor: CoolSip Distributors; Delivery Count: 8; Average Delay: 4.12 days; Maximum Delay: 15 days; Average Quality Rating: 3.62.

**Investigation Focus:** Review vendor service-level agreement compliance, purchase-order planning, supply capacity, product quality checks, and backup supplier availability.

### RCA-COMP-S003 — Customer complaint hotspot at SmartMart Clock Tower

**Priority:** High (95.00)

**Business Area:** Customer Support

**Primary Root Cause:** A concentrated volume of customer complaints has accumulated at the store.

**Contributing Factors:** The largest complaint category is Product Quality Issue with 88 cases. The most frequently complained-about product is Instant Noodles Pack with 67 cases. 103 complaints are still Open or In Progress. The store has 9 Low Stock and 1 Reorder Soon inventory records, which may be contributing to service-related complaints.

**Evidence Summary:** Total Complaints: 297; High-Severity Complaints: 121; Open or In-Progress Complaints: 103.

**Investigation Focus:** Review the main complaint categories, product availability, frontline service quality, complaint-resolution workload, and store-manager escalation process.

### RCA-SALES-S003-2026-06 — Major sales decline at SmartMart Clock Tower

**Priority:** High (95.00)

**Business Area:** Sales

**Primary Root Cause:** Store revenue declined by 57.86% in 2026-06 compared with 2026-05.

**Contributing Factors:** Groceries was the largest declining category, falling by 53.55%. The store also has 9 Low Stock and 1 Reorder Soon inventory records. 165 complaints were registered in 2026-06, including 97 High-severity cases.

**Evidence Summary:** Current Month Sales: ₹259,798.35; Previous Month Sales: ₹616,542.20; Sales Decline: 57.86%.

**Investigation Focus:** Review declining categories, stock availability of fast-moving products, customer complaints, and changes in local demand or sales execution.

### RCA-FIN-S003-2026-06 — High financial risk at SmartMart Clock Tower

**Priority:** High (90.00)

**Business Area:** Finance

**Primary Root Cause:** Severe underachievement of the sales target: the store achieved only 28.87% of its target in 2026-06.

**Contributing Factors:** Revenue declined by 57.86% from 2026-05. Operating expenses were ₹30,232.72. Groceries sales declined by 53.55% compared with 2026-05.

**Evidence Summary:** Revenue: ₹259,798.35; Operating Profit: ₹25,996.63; Target Achievement: 28.87%; Financial Risk Status: High Risk.

**Investigation Focus:** Review the largest declining product categories, store-level sales activities, discounting practices, and local operational constraints.

### RCA-FIN-S001-2026-06 — High financial risk at SmartMart Rajpur Road

**Priority:** High (90.00)

**Business Area:** Finance

**Primary Root Cause:** Severe underachievement of the sales target: the store achieved only 69.36% of its target in 2026-06.

**Contributing Factors:** Revenue declined by 11.61% from 2026-05. Operating expenses were ₹69,676.30. Groceries sales declined by 25.37% compared with 2026-05.

**Evidence Summary:** Revenue: ₹589,602.30; Operating Profit: ₹65,171.00; Target Achievement: 69.36%; Financial Risk Status: High Risk.

**Investigation Focus:** Review the largest declining product categories, store-level sales activities, discounting practices, and local operational constraints.

### RCA-INV-S003-P017-2026-06-30 — Low-stock risk: Instant Noodles Pack at SmartMart Clock Tower

**Priority:** High (90.00)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 5.00% of its reorder level (5 units available against a reorder level of 100).

**Contributing Factors:** The product is linked with 67 customer complaints, including 35 High-severity cases. 32 related complaints remain Open or In Progress. 21 related complaints are specifically categorized as Out of Stock. Supplier QuickBite Foods has an average delivery delay of 0.80 days and 5 delayed deliveries.

**Evidence Summary:** Store: SmartMart Clock Tower; Product: Instant Noodles Pack; Stock Status: Low Stock; Current Stock: 5; Reorder Level: 100; Related Complaints: 67.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.

### RCA-VENDOR-V005 — Vendor delivery risk: GlowCare Personal Products

**Priority:** Medium (76.72)

**Business Area:** Procurement

**Primary Root Cause:** Repeated delivery-performance exceptions are affecting supplier reliability.

**Contributing Factors:** The maximum observed delivery delay is 5 days. 4 deliveries were delayed. 1 deliveries were partial. The most affected store is SmartMart Rudrapur, where the average delay is 5.00 days.

**Evidence Summary:** Vendor: GlowCare Personal Products; Delivery Count: 9; Average Delay: 1.56 days; Maximum Delay: 5 days; Average Quality Rating: 4.22.

**Investigation Focus:** Review vendor service-level agreement compliance, purchase-order planning, supply capacity, product quality checks, and backup supplier availability.

### RCA-INV-S003-P018-2026-06-30 — Low-stock risk: Biscuits 300g at SmartMart Clock Tower

**Priority:** Medium (76.00)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 40.00% of its reorder level (36 units available against a reorder level of 90).

**Contributing Factors:** The product is linked with 55 customer complaints, including 30 High-severity cases. 24 related complaints remain Open or In Progress. 13 related complaints are specifically categorized as Out of Stock. Supplier QuickBite Foods has an average delivery delay of 0.80 days and 5 delayed deliveries.

**Evidence Summary:** Store: SmartMart Clock Tower; Product: Biscuits 300g; Stock Status: Low Stock; Current Stock: 36; Reorder Level: 90; Related Complaints: 55.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.

### RCA-VENDOR-V002 — Vendor delivery risk: FreshDrop Oils

**Priority:** Medium (75.59)

**Business Area:** Procurement

**Primary Root Cause:** Repeated delivery-performance exceptions are affecting supplier reliability.

**Contributing Factors:** The maximum observed delivery delay is 5 days. 4 deliveries were delayed. 2 deliveries were partial. The most affected store is SmartMart Haridwar Central, where the average delay is 4.00 days.

**Evidence Summary:** Vendor: FreshDrop Oils; Delivery Count: 11; Average Delay: 1.27 days; Maximum Delay: 5 days; Average Quality Rating: 4.09.

**Investigation Focus:** Review vendor service-level agreement compliance, purchase-order planning, supply capacity, product quality checks, and backup supplier availability.

### RCA-INV-S003-P019-2026-06-30 — Low-stock risk: Chips 150g at SmartMart Clock Tower

**Priority:** Medium (73.00)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 59.00% of its reorder level (59 units available against a reorder level of 100).

**Contributing Factors:** The product is linked with 59 customer complaints, including 35 High-severity cases. 28 related complaints remain Open or In Progress. 18 related complaints are specifically categorized as Out of Stock. Supplier QuickBite Foods has an average delivery delay of 0.80 days and 5 delayed deliveries.

**Evidence Summary:** Store: SmartMart Clock Tower; Product: Chips 150g; Stock Status: Low Stock; Current Stock: 59; Reorder Level: 100; Related Complaints: 59.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.

### RCA-VENDOR-V007 — Vendor delivery risk: QuickBite Foods

**Priority:** Medium (71.20)

**Business Area:** Procurement

**Primary Root Cause:** Repeated delivery-performance exceptions are affecting supplier reliability.

**Contributing Factors:** The maximum observed delivery delay is 2 days. 5 deliveries were delayed. 2 deliveries were partial. The most affected store is SmartMart Kashipur, where the average delay is 2.00 days.

**Evidence Summary:** Vendor: QuickBite Foods; Delivery Count: 10; Average Delay: 0.80 days; Maximum Delay: 2 days; Average Quality Rating: 4.35.

**Investigation Focus:** Review vendor service-level agreement compliance, purchase-order planning, supply capacity, product quality checks, and backup supplier availability.

### RCA-VENDOR-V001 — Vendor delivery risk: GrainPro Suppliers

**Priority:** Medium (71.06)

**Business Area:** Procurement

**Primary Root Cause:** Repeated delivery-performance exceptions are affecting supplier reliability.

**Contributing Factors:** The maximum observed delivery delay is 3 days. 4 deliveries were delayed. 1 deliveries were partial. The most affected store is SmartMart Haldwani, where the average delay is 3.00 days.

**Evidence Summary:** Vendor: GrainPro Suppliers; Delivery Count: 9; Average Delay: 0.89 days; Maximum Delay: 3 days; Average Quality Rating: 4.17.

**Investigation Focus:** Review vendor service-level agreement compliance, purchase-order planning, supply capacity, product quality checks, and backup supplier availability.

### RCA-VENDOR-V003 — Vendor delivery risk: BrewLeaf Beverages

**Priority:** Medium (68.83)

**Business Area:** Procurement

**Primary Root Cause:** Repeated delivery-performance exceptions are affecting supplier reliability.

**Contributing Factors:** The maximum observed delivery delay is 3 days. 3 deliveries were delayed. 1 deliveries were partial. The most affected store is SmartMart Rudrapur, where the average delay is 1.50 days.

**Evidence Summary:** Vendor: BrewLeaf Beverages; Delivery Count: 6; Average Delay: 0.83 days; Maximum Delay: 3 days; Average Quality Rating: 4.33.

**Investigation Focus:** Review vendor service-level agreement compliance, purchase-order planning, supply capacity, product quality checks, and backup supplier availability.

### RCA-INV-S010-P007-2026-06-30 — Low-stock risk: Packaged Juice 1L at SmartMart Mussoorie

**Priority:** Medium (68.70)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 14.00% of its reorder level (7 units available against a reorder level of 50).

**Contributing Factors:** The product is linked with 10 customer complaints, including 2 High-severity cases. 2 related complaints remain Open or In Progress. Supplier CoolSip Distributors has an average delivery delay of 4.12 days and 6 delayed deliveries. The supplier's maximum observed delay is 15 days.

**Evidence Summary:** Store: SmartMart Mussoorie; Product: Packaged Juice 1L; Stock Status: Low Stock; Current Stock: 7; Reorder Level: 50; Related Complaints: 10.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.

### RCA-INV-S005-P013-2026-06-30 — Low-stock risk: Dishwash Liquid 500ml at SmartMart Haridwar Central

**Priority:** Medium (67.34)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 17.78% of its reorder level (8 units available against a reorder level of 45).

**Contributing Factors:** The product is linked with 7 customer complaints, including 2 High-severity cases. 1 related complaints remain Open or In Progress. Supplier HomeShine Supplies has an average delivery delay of 0.57 days and 2 delayed deliveries.

**Evidence Summary:** Store: SmartMart Haridwar Central; Product: Dishwash Liquid 500ml; Stock Status: Low Stock; Current Stock: 8; Reorder Level: 45; Related Complaints: 7.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.

### RCA-INV-S010-P019-2026-06-30 — Low-stock risk: Chips 150g at SmartMart Mussoorie

**Priority:** Medium (66.95)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 19.00% of its reorder level (19 units available against a reorder level of 100).

**Contributing Factors:** The product is linked with 10 customer complaints, including 1 High-severity cases. 1 related complaints remain Open or In Progress. 3 related complaints are specifically categorized as Out of Stock. Supplier QuickBite Foods has an average delivery delay of 0.80 days and 5 delayed deliveries.

**Evidence Summary:** Store: SmartMart Mussoorie; Product: Chips 150g; Stock Status: Low Stock; Current Stock: 19; Reorder Level: 100; Related Complaints: 10.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.

### RCA-VENDOR-V008 — Vendor delivery risk: WriteWell Stationery

**Priority:** Medium (66.22)

**Business Area:** Procurement

**Primary Root Cause:** Repeated delivery-performance exceptions are affecting supplier reliability.

**Contributing Factors:** The maximum observed delivery delay is 2 days. 3 deliveries were delayed. 1 deliveries were partial. The most affected store is SmartMart Rudrapur, where the average delay is 2.00 days.

**Evidence Summary:** Vendor: WriteWell Stationery; Delivery Count: 9; Average Delay: 0.56 days; Maximum Delay: 2 days; Average Quality Rating: 4.28.

**Investigation Focus:** Review vendor service-level agreement compliance, purchase-order planning, supply capacity, product quality checks, and backup supplier availability.

### RCA-INV-S010-P024-2026-06-30 — Low-stock risk: Earphones at SmartMart Mussoorie

**Priority:** Medium (66.20)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 16.00% of its reorder level (4 units available against a reorder level of 25).

**Contributing Factors:** The product is linked with 7 customer complaints, including 0 High-severity cases. Supplier TechEase Accessories has an average delivery delay of 4.38 days and 6 delayed deliveries. The supplier's maximum observed delay is 15 days.

**Evidence Summary:** Store: SmartMart Mussoorie; Product: Earphones; Stock Status: Low Stock; Current Stock: 4; Reorder Level: 25; Related Complaints: 7.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.

### RCA-INV-S006-P007-2026-06-30 — Low-stock risk: Packaged Juice 1L at SmartMart Roorkee

**Priority:** Medium (65.75)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 22.00% of its reorder level (11 units available against a reorder level of 50).

**Contributing Factors:** The product is linked with 7 customer complaints, including 1 High-severity cases. 2 related complaints remain Open or In Progress. Supplier CoolSip Distributors has an average delivery delay of 4.12 days and 6 delayed deliveries. The supplier's maximum observed delay is 15 days.

**Evidence Summary:** Store: SmartMart Roorkee; Product: Packaged Juice 1L; Stock Status: Low Stock; Current Stock: 11; Reorder Level: 50; Related Complaints: 7.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.

### RCA-INV-S010-P009-2026-06-30 — Low-stock risk: Shampoo 180ml at SmartMart Mussoorie

**Priority:** Medium (65.55)

**Business Area:** Operations

**Primary Root Cause:** Stock is at 25.00% of its reorder level (10 units available against a reorder level of 40).

**Contributing Factors:** The product is linked with 9 customer complaints, including 1 High-severity cases. 1 related complaints remain Open or In Progress. Supplier GlowCare Personal Products has an average delivery delay of 1.56 days and 4 delayed deliveries.

**Evidence Summary:** Store: SmartMart Mussoorie; Product: Shampoo 180ml; Stock Status: Low Stock; Current Stock: 10; Reorder Level: 40; Related Complaints: 9.

**Investigation Focus:** Review the latest purchase order, vendor delivery status, recent sales velocity, stock-transfer availability, and replenishment approval process.
