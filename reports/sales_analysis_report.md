# Sales Analysis Report

## AI-Powered Operating Intelligence Platform

**Generated At:** 2026-07-02 18:39:40

This report contains deterministic sales findings calculated from validated PostgreSQL data. The findings will later provide evidence to the central issue-detection and priority engines.

## Detection Rules

- Store sales decline: 20% or more
- Product sales decline: 30% or more
- Low target achievement: below 70%
- Product underperformance: below 60% of category average
- Category sales decline: 20% or more
- Regional sales decline: 20% or more

## Finding Summary

| Analysis Type | Severity | Findings |
|---|---|---:|
| Low Target Achievement | High | 1 |
| Low Target Achievement | Medium | 1 |
| Product Underperformance | High | 2 |
| Store Sales Decline | High | 1 |

## Sales Findings

| Severity | Analysis Type | Entity | Period | Change / Performance |
|---|---|---|---|---|
| High | Low Target Achievement | SmartMart Clock Tower | 2026-06 | Target Achievement: 28.87% |
| High | Product Underperformance | Sugar 1kg | 2026-06 | Sales: ₹82,857.60; Benchmark: ₹405,394.40 |
| High | Product Underperformance | Soft Drink 750ml | 2026-06 | Sales: ₹64,707.75; Benchmark: ₹276,031.31 |
| High | Store Sales Decline | SmartMart Clock Tower | 2026-05 → 2026-06 | -57.86% |
| Medium | Low Target Achievement | SmartMart Rajpur Road | 2026-06 | Target Achievement: 69.36% |

## Detailed Findings

### LOW-TARGET-S003-2026-06

**Severity:** High

**Analysis Type:** Low Target Achievement

**Entity:** SmartMart Clock Tower (Store)

**Summary:** SmartMart Clock Tower achieved only 28.87% of its sales target in 2026-06.

**Evidence:** Monthly Target: ₹900,000.00; Revenue: ₹259,798.35; Operating Profit: ₹25,996.63; Risk Status: High Risk

### PRODUCT-UNDERPERFORMANCE-P004-2026-06

**Severity:** High

**Analysis Type:** Product Underperformance

**Entity:** Sugar 1kg (Product)

**Summary:** Sugar 1kg achieved only 20.44% of the latest-month average sales for the Groceries category.

**Evidence:** Product Sales: ₹82,857.60; Category Average Sales: ₹405,394.40; Product Count in Category: 4

### PRODUCT-UNDERPERFORMANCE-P008-2026-06

**Severity:** High

**Analysis Type:** Product Underperformance

**Entity:** Soft Drink 750ml (Product)

**Summary:** Soft Drink 750ml achieved only 23.44% of the latest-month average sales for the Beverages category.

**Evidence:** Product Sales: ₹64,707.75; Category Average Sales: ₹276,031.31; Product Count in Category: 4

### STORE-DECLINE-S003-2026-06

**Severity:** High

**Analysis Type:** Store Sales Decline

**Entity:** SmartMart Clock Tower (Store)

**Summary:** SmartMart Clock Tower recorded a 57.86% sales decline in 2026-06 compared with 2026-05.

**Evidence:** Current Month Sales: ₹259,798.35; Previous Month Sales: ₹616,542.20; Sales Decline: 57.86%; Region: North

### LOW-TARGET-S001-2026-06

**Severity:** Medium

**Analysis Type:** Low Target Achievement

**Entity:** SmartMart Rajpur Road (Store)

**Summary:** SmartMart Rajpur Road achieved only 69.36% of its sales target in 2026-06.

**Evidence:** Monthly Target: ₹850,000.00; Revenue: ₹589,602.30; Operating Profit: ₹65,171.00; Risk Status: High Risk
