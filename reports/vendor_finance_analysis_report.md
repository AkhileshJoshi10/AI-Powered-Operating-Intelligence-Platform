# Vendor and Finance Analysis Report

## AI-Powered Operating Intelligence Platform

**Generated At:** 2026-07-02 21:16:51

This report contains procurement and finance findings calculated from validated PostgreSQL vendor-delivery and finance data.

## Detection Rules

- Repeated vendor delay: average delay of 5 days or more, or 3 or more delayed deliveries.
- Low vendor quality: below 3.5 out of 5.
- Low on-time delivery rate: below 70%.
- Partial delivery risk: 2 or more partial deliveries.
- Low operating profit margin: below 10%.
- Low target achievement: below 70%.

## Finding Summary

| Area | Analysis Type | Severity | Findings |
|---|---|---|---:|
| Finance | High Financial Risk | High | 2 |
| Finance | Low Target Achievement | High | 1 |
| Finance | Low Target Achievement | Medium | 1 |
| Procurement | Low On-Time Delivery Rate | High | 2 |
| Procurement | Low On-Time Delivery Rate | Medium | 6 |
| Procurement | Partial Vendor Deliveries | Medium | 3 |
| Procurement | Repeated Vendor Delays | High | 2 |
| Procurement | Repeated Vendor Delays | Medium | 6 |

## Vendor and Finance Findings

| Severity | Area | Analysis Type | Entity | Main Metric |
|---|---|---|---|---|
| High | Finance | High Financial Risk | SmartMart Clock Tower | Target Achievement: 28.87% |
| High | Finance | High Financial Risk | SmartMart Rajpur Road | Target Achievement: 69.36% |
| High | Finance | Low Target Achievement | SmartMart Clock Tower | Target Achievement: 28.87% |
| High | Procurement | Low On-Time Delivery Rate | TechEase Accessories | On-Time Rate: 25.00% |
| High | Procurement | Low On-Time Delivery Rate | CoolSip Distributors | On-Time Rate: 25.00% |
| High | Procurement | Repeated Vendor Delays | TechEase Accessories | On-Time Rate: 25.00% |
| High | Procurement | Repeated Vendor Delays | CoolSip Distributors | On-Time Rate: 25.00% |
| Medium | Finance | Low Target Achievement | SmartMart Rajpur Road | Target Achievement: 69.36% |
| Medium | Procurement | Low On-Time Delivery Rate | GlowCare Personal Products | On-Time Rate: 55.56% |
| Medium | Procurement | Low On-Time Delivery Rate | FreshDrop Oils | On-Time Rate: 63.64% |
| Medium | Procurement | Low On-Time Delivery Rate | GrainPro Suppliers | On-Time Rate: 55.56% |
| Medium | Procurement | Low On-Time Delivery Rate | BrewLeaf Beverages | On-Time Rate: 50.00% |
| Medium | Procurement | Low On-Time Delivery Rate | QuickBite Foods | On-Time Rate: 50.00% |
| Medium | Procurement | Low On-Time Delivery Rate | WriteWell Stationery | On-Time Rate: 66.67% |
| Medium | Procurement | Partial Vendor Deliveries | FreshDrop Oils | On-Time Rate: 63.64% |
| Medium | Procurement | Partial Vendor Deliveries | BrightLite Electricals | On-Time Rate: 75.00% |
| Medium | Procurement | Partial Vendor Deliveries | QuickBite Foods | On-Time Rate: 50.00% |
| Medium | Procurement | Repeated Vendor Delays | GlowCare Personal Products | On-Time Rate: 55.56% |
| Medium | Procurement | Repeated Vendor Delays | FreshDrop Oils | On-Time Rate: 63.64% |
| Medium | Procurement | Repeated Vendor Delays | GrainPro Suppliers | On-Time Rate: 55.56% |
| Medium | Procurement | Repeated Vendor Delays | BrewLeaf Beverages | On-Time Rate: 50.00% |
| Medium | Procurement | Repeated Vendor Delays | QuickBite Foods | On-Time Rate: 50.00% |
| Medium | Procurement | Repeated Vendor Delays | WriteWell Stationery | On-Time Rate: 66.67% |

## Detailed Findings

### HIGH-FINANCIAL-RISK-S003-2026-06

**Severity:** High

**Business Area:** Finance

**Analysis Type:** High Financial Risk

**Entity:** SmartMart Clock Tower (Store)

**Summary:** SmartMart Clock Tower is classified as High Risk in the finance report for 2026-06.

**Evidence:** Revenue: ₹259,798.35; Operating Profit: ₹25,996.63; Operating Profit Margin: 10.01%; Target Achievement: 28.87%; Risk Status: High Risk

### HIGH-FINANCIAL-RISK-S001-2026-06

**Severity:** High

**Business Area:** Finance

**Analysis Type:** High Financial Risk

**Entity:** SmartMart Rajpur Road (Store)

**Summary:** SmartMart Rajpur Road is classified as High Risk in the finance report for 2026-06.

**Evidence:** Revenue: ₹589,602.30; Operating Profit: ₹65,171.00; Operating Profit Margin: 11.05%; Target Achievement: 69.36%; Risk Status: High Risk

### LOW-TARGET-S003-2026-06

**Severity:** High

**Business Area:** Finance

**Analysis Type:** Low Target Achievement

**Entity:** SmartMart Clock Tower (Store)

**Summary:** SmartMart Clock Tower achieved only 28.87% of its target in 2026-06.

**Evidence:** Revenue: ₹259,798.35; Operating Profit: ₹25,996.63; Target Achievement: 28.87%; Risk Status: High Risk

### LOW-ON-TIME-RATE-V009

**Severity:** High

**Business Area:** Procurement

**Analysis Type:** Low On-Time Delivery Rate

**Entity:** TechEase Accessories (Vendor)

**Summary:** TechEase Accessories has a low on-time delivery rate.

**Evidence:** On-Time Delivery Rate: 25.00%; Delayed Deliveries: 6; Delivery Count: 8; Average Delay: 4.38 days

### LOW-ON-TIME-RATE-V004

**Severity:** High

**Business Area:** Procurement

**Analysis Type:** Low On-Time Delivery Rate

**Entity:** CoolSip Distributors (Vendor)

**Summary:** CoolSip Distributors has a low on-time delivery rate.

**Evidence:** On-Time Delivery Rate: 25.00%; Delayed Deliveries: 6; Delivery Count: 8; Average Delay: 4.12 days

### VENDOR-DELAY-V009

**Severity:** High

**Business Area:** Procurement

**Analysis Type:** Repeated Vendor Delays

**Entity:** TechEase Accessories (Vendor)

**Summary:** TechEase Accessories has repeated delivery delays that may disrupt inventory replenishment.

**Evidence:** Delivery Count: 8; Delayed Deliveries: 6; Average Delay: 4.38 days; Maximum Delay: 15 days; On-Time Delivery Rate: 25.00%

### VENDOR-DELAY-V004

**Severity:** High

**Business Area:** Procurement

**Analysis Type:** Repeated Vendor Delays

**Entity:** CoolSip Distributors (Vendor)

**Summary:** CoolSip Distributors has repeated delivery delays that may disrupt inventory replenishment.

**Evidence:** Delivery Count: 8; Delayed Deliveries: 6; Average Delay: 4.12 days; Maximum Delay: 15 days; On-Time Delivery Rate: 25.00%

### LOW-TARGET-S001-2026-06

**Severity:** Medium

**Business Area:** Finance

**Analysis Type:** Low Target Achievement

**Entity:** SmartMart Rajpur Road (Store)

**Summary:** SmartMart Rajpur Road achieved only 69.36% of its target in 2026-06.

**Evidence:** Revenue: ₹589,602.30; Operating Profit: ₹65,171.00; Target Achievement: 69.36%; Risk Status: High Risk

### LOW-ON-TIME-RATE-V005

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Low On-Time Delivery Rate

**Entity:** GlowCare Personal Products (Vendor)

**Summary:** GlowCare Personal Products has a low on-time delivery rate.

**Evidence:** On-Time Delivery Rate: 55.56%; Delayed Deliveries: 4; Delivery Count: 9; Average Delay: 1.56 days

### LOW-ON-TIME-RATE-V002

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Low On-Time Delivery Rate

**Entity:** FreshDrop Oils (Vendor)

**Summary:** FreshDrop Oils has a low on-time delivery rate.

**Evidence:** On-Time Delivery Rate: 63.64%; Delayed Deliveries: 4; Delivery Count: 11; Average Delay: 1.27 days

### LOW-ON-TIME-RATE-V001

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Low On-Time Delivery Rate

**Entity:** GrainPro Suppliers (Vendor)

**Summary:** GrainPro Suppliers has a low on-time delivery rate.

**Evidence:** On-Time Delivery Rate: 55.56%; Delayed Deliveries: 4; Delivery Count: 9; Average Delay: 0.89 days

### LOW-ON-TIME-RATE-V003

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Low On-Time Delivery Rate

**Entity:** BrewLeaf Beverages (Vendor)

**Summary:** BrewLeaf Beverages has a low on-time delivery rate.

**Evidence:** On-Time Delivery Rate: 50.00%; Delayed Deliveries: 3; Delivery Count: 6; Average Delay: 0.83 days

### LOW-ON-TIME-RATE-V007

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Low On-Time Delivery Rate

**Entity:** QuickBite Foods (Vendor)

**Summary:** QuickBite Foods has a low on-time delivery rate.

**Evidence:** On-Time Delivery Rate: 50.00%; Delayed Deliveries: 5; Delivery Count: 10; Average Delay: 0.80 days

### LOW-ON-TIME-RATE-V008

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Low On-Time Delivery Rate

**Entity:** WriteWell Stationery (Vendor)

**Summary:** WriteWell Stationery has a low on-time delivery rate.

**Evidence:** On-Time Delivery Rate: 66.67%; Delayed Deliveries: 3; Delivery Count: 9; Average Delay: 0.56 days

### PARTIAL-DELIVERY-V002

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Partial Vendor Deliveries

**Entity:** FreshDrop Oils (Vendor)

**Summary:** FreshDrop Oils has repeated partial deliveries, which may create inventory availability risk.

**Evidence:** Delivery Count: 11; Partial Deliveries: 2; Delayed Deliveries: 4; Average Delay: 1.27 days

### PARTIAL-DELIVERY-V010

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Partial Vendor Deliveries

**Entity:** BrightLite Electricals (Vendor)

**Summary:** BrightLite Electricals has repeated partial deliveries, which may create inventory availability risk.

**Evidence:** Delivery Count: 8; Partial Deliveries: 2; Delayed Deliveries: 2; Average Delay: 0.88 days

### PARTIAL-DELIVERY-V007

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Partial Vendor Deliveries

**Entity:** QuickBite Foods (Vendor)

**Summary:** QuickBite Foods has repeated partial deliveries, which may create inventory availability risk.

**Evidence:** Delivery Count: 10; Partial Deliveries: 2; Delayed Deliveries: 5; Average Delay: 0.80 days

### VENDOR-DELAY-V005

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Repeated Vendor Delays

**Entity:** GlowCare Personal Products (Vendor)

**Summary:** GlowCare Personal Products has repeated delivery delays that may disrupt inventory replenishment.

**Evidence:** Delivery Count: 9; Delayed Deliveries: 4; Average Delay: 1.56 days; Maximum Delay: 5 days; On-Time Delivery Rate: 55.56%

### VENDOR-DELAY-V002

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Repeated Vendor Delays

**Entity:** FreshDrop Oils (Vendor)

**Summary:** FreshDrop Oils has repeated delivery delays that may disrupt inventory replenishment.

**Evidence:** Delivery Count: 11; Delayed Deliveries: 4; Average Delay: 1.27 days; Maximum Delay: 5 days; On-Time Delivery Rate: 63.64%

### VENDOR-DELAY-V001

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Repeated Vendor Delays

**Entity:** GrainPro Suppliers (Vendor)

**Summary:** GrainPro Suppliers has repeated delivery delays that may disrupt inventory replenishment.

**Evidence:** Delivery Count: 9; Delayed Deliveries: 4; Average Delay: 0.89 days; Maximum Delay: 3 days; On-Time Delivery Rate: 55.56%

### VENDOR-DELAY-V003

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Repeated Vendor Delays

**Entity:** BrewLeaf Beverages (Vendor)

**Summary:** BrewLeaf Beverages has repeated delivery delays that may disrupt inventory replenishment.

**Evidence:** Delivery Count: 6; Delayed Deliveries: 3; Average Delay: 0.83 days; Maximum Delay: 3 days; On-Time Delivery Rate: 50.00%

### VENDOR-DELAY-V007

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Repeated Vendor Delays

**Entity:** QuickBite Foods (Vendor)

**Summary:** QuickBite Foods has repeated delivery delays that may disrupt inventory replenishment.

**Evidence:** Delivery Count: 10; Delayed Deliveries: 5; Average Delay: 0.80 days; Maximum Delay: 2 days; On-Time Delivery Rate: 50.00%

### VENDOR-DELAY-V008

**Severity:** Medium

**Business Area:** Procurement

**Analysis Type:** Repeated Vendor Delays

**Entity:** WriteWell Stationery (Vendor)

**Summary:** WriteWell Stationery has repeated delivery delays that may disrupt inventory replenishment.

**Evidence:** Delivery Count: 9; Delayed Deliveries: 3; Average Delay: 0.56 days; Maximum Delay: 2 days; On-Time Delivery Rate: 66.67%
