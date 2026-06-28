# Exploratory Data Analysis Insights

## 1. Dataset Overview

The cleaned dataset contains the following records:

| Dataset | Rows | Columns |
|---|---:|---:|
| Products | 25 | 12 |
| Stores | 10 | 10 |
| Vendors | 10 | 11 |
| Employees | 25 | 10 |
| Sales | 44,435 | 16 |
| Inventory | 250 | 13 |
| Complaints | 1,572 | 15 |
| Finance | 60 | 13 |
| Vendor Deliveries | 85 | 18 |

---

## 2. Sales Performance Summary

| KPI | Value |
|---|---:|
| Total Sales | 39,064,024.80 |
| Total Profit | 8,663,194.80 |
| Total Transactions | 44,435 |
| Total Quantity Sold | 262,646 |
| Average Transaction Value | 879.13 |
| Average Discount Percent | 3.51% |

### Monthly Sales Trend

| Month | Total Sales | Total Profit | Transactions |
|---|---:|---:|---:|
| January 2026 | 6,847,294.10 | 1,528,705.10 | 7,849 |
| February 2026 | 6,219,178.50 | 1,374,379.50 | 6,997 |
| March 2026 | 6,577,859.80 | 1,463,605.80 | 7,448 |
| April 2026 | 6,626,111.00 | 1,474,290.00 | 7,407 |
| May 2026 | 6,622,437.80 | 1,459,923.80 | 7,449 |
| June 2026 | 6,171,143.60 | 1,362,290.60 | 7,395 |

### Key Sales Findings

- Sales were highest in January 2026 and lowest in June 2026.
- June shows a visible decline in both sales and profit compared with May.
- The decline supports the main business scenario in which the system must identify business performance problems early.

### Top Products by Sales

1. Basmati Rice 5kg  
2. Earphones  
3. Coffee 200g  
4. Atta 5kg  
5. Tea 500g  

Basmati Rice 5kg generated the highest total sales, while Earphones also performed strongly despite being a non-FMCG product.

---

## 3. Store-Level Performance

### Highest Sales Stores

1. SmartMart Kashipur — 4,076,050.40  
2. SmartMart Haldwani — 4,051,818.70  
3. SmartMart Mussoorie — 3,987,174.10  

### Lowest Sales Store

- SmartMart Clock Tower (S003) — 3,518,994.90

### Key Store Finding

SmartMart Clock Tower has the lowest total sales among all stores. This store should be treated as a priority investigation area because it also has the highest complaint volume and multiple low-stock products.

---

## 4. Inventory Analysis

| Stock Status | Inventory Records | Total Current Stock |
|---|---:|---:|
| Normal | 151 | 15,490 |
| Low Stock | 37 | 919 |
| Reorder Soon | 34 | 1,924 |
| Overstock | 28 | 5,426 |

### Key Inventory Findings

- 37 inventory records are classified as Low Stock.
- 34 inventory records are classified as Reorder Soon.
- A total of 99 inventory records require attention because they are either Low Stock or Reorder Soon.
- 28 records are Overstock, which may indicate inefficient inventory allocation or excess working capital tied in stock.

### Important Low-Stock Examples

- S003 SmartMart Clock Tower — P017 Instant Noodles Pack  
  - Current Stock: 5  
  - Reorder Level: 100  
  - Reorder Required: Yes  

- S010 SmartMart Mussoorie — P024 Earphones  
  - Current Stock: 4  
  - Reorder Level: 25  
  - Reorder Required: Yes  

- S010 SmartMart Mussoorie — P007 Packaged Juice 1L  
  - Current Stock: 7  
  - Reorder Level: 50  
  - Reorder Required: Yes  

---

## 5. Customer Complaint Analysis

### Complaints by Severity

| Severity | Complaint Count |
|---|---:|
| Low | 700 |
| Medium | 560 |
| High | 312 |

### Stores with Highest Complaint Counts

| Store | Complaint Count |
|---|---:|
| SmartMart Clock Tower (S003) | 297 |
| SmartMart Ballupur (S002) | 153 |
| SmartMart Haridwar Central (S005) | 153 |
| SmartMart Rudrapur (S009) | 149 |
| SmartMart Mussoorie (S010) | 143 |

### Products with Highest Complaint Counts

| Product | Complaint Count |
|---|---:|
| Instant Noodles Pack (P017) | 111 |
| Chips 150g (P019) | 105 |
| Biscuits 300g (P018) | 104 |
| Soap Pack of 4 (P011) | 75 |
| Shampoo 180ml (P009) | 69 |

### Key Complaint Finding

SmartMart Clock Tower has the highest complaint count. P017 Instant Noodles Pack has the highest number of complaints and is also low in stock at the same store. This creates a strong cross-functional issue involving inventory, customer satisfaction, store performance, and possible vendor supply problems.

---

## 6. Vendor Delivery Analysis

### Vendors with Highest Average Delivery Delays

| Vendor | Average Delay Days | Maximum Delay Days | Average Quality Rating |
|---|---:|---:|---:|
| TechEase Accessories (V009) | 4.38 | 15 | 4.00 |
| CoolSip Distributors (V004) | 4.12 | 15 | 3.92 |
| GlowCare Personal Products (V005) | 1.56 | 5 | 4.22 |
| FreshDrop Oils (V002) | 1.27 | 5 | 4.09 |

### Key Vendor Finding

V009 TechEase Accessories and V004 CoolSip Distributors show the highest average delivery delays and maximum delays of 15 days. These vendors should be monitored by the procurement and operations functions.

---

## 7. Finance Analysis

### High-Risk Finance Records

| Month | Store | Target Achievement | Risk Status |
|---|---|---:|---|
| June 2026 | SmartMart Clock Tower (S003) | 28.87% | High Risk |
| June 2026 | SmartMart Rajpur Road (S001) | 69.36% | High Risk |
| June 2026 | SmartMart Clock Tower (S003) | 66.28% | High Risk |
| May 2026 | SmartMart Clock Tower (S003) | 68.50% | High Risk |

### Key Finance Finding

SmartMart Clock Tower has repeated High Risk records and weak target achievement, especially in June 2026. Its June target achievement is only 28.87%, making it the most important financial risk area in the dataset.

---

## 8. Priority Business Issues Identified

### Priority 1: SmartMart Clock Tower Performance Decline

**Evidence:**
- Lowest total sales among all stores.
- Highest complaint count at 297.
- Repeated High Risk finance records.
- June target achievement of only 28.87%.
- Low stock for Instant Noodles Pack, which is also the most complained-about product.

**Potential Root Causes:**
- Stock availability issues.
- High customer dissatisfaction.
- Weak sales performance.
- Possible supply or replenishment problems.

### Priority 2: Instant Noodles Pack Customer and Inventory Issue

**Evidence:**
- Highest complaint count at 111.
- Low stock at SmartMart Clock Tower.
- Product may be contributing to customer dissatisfaction and lost sales.

### Priority 3: Vendor Delivery Delays

**Evidence:**
- V009 TechEase Accessories and V004 CoolSip Distributors show the highest average delivery delays.
- Both vendors have maximum delays of 15 days.

### Priority 4: Inventory Rebalancing Requirement

**Evidence:**
- 37 Low Stock records.
- 34 Reorder Soon records.
- 28 Overstock records.

**Potential Action:**
- Prioritize replenishment for low-stock products.
- Review overstocked products for redistribution, promotions, or purchase reduction.

---

## 9. EDA Conclusion

The exploratory analysis confirms that the dataset contains realistic and connected business problems. The strongest scenario is SmartMart Clock Tower, where low sales, finance risk, high complaints, and low inventory are linked together.

These findings will later be used by the analytics engine, priority-ranking system, root-cause analysis agent, recommendation agent, and Daily Executive Brief module.