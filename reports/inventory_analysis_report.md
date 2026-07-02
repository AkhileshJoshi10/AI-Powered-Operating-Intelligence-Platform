# Inventory Analysis Report

## AI-Powered Operating Intelligence Platform

**Generated At:** 2026-07-02 18:54:16

This report contains inventory findings calculated from validated PostgreSQL inventory, product, vendor, and complaint data.

## Detection Rules

- Low Stock: inventory records marked as `Low Stock`.
- Reorder Soon: inventory records marked as `Reorder Soon`.
- Overstock: inventory records marked as `Overstock`.
- Stockout Risk: stock at or below 50% of reorder level, or significant related complaint volume.
- Near Expiry: perishable stock expiring within 30 days from the inventory snapshot date.
- Expired Inventory: perishable stock already expired on the inventory snapshot date.

## Finding Summary

| Analysis Type | Severity | Findings |
|---|---|---:|
| Low Stock | High | 8 |
| Low Stock | Medium | 29 |
| Overstock | Low | 28 |
| Reorder Soon | Low | 34 |
| Stockout Risk | High | 10 |
| Stockout Risk | Medium | 13 |

## Inventory Findings

| Severity | Analysis Type | Store | Product | Stock Ratio | Expiry Status |
|---|---|---|---|---:|---|
| High | Low Stock | SmartMart Clock Tower | Instant Noodles Pack | 5.00% | 157 days |
| High | Low Stock | SmartMart Mussoorie | Packaged Juice 1L | 14.00% | 155 days |
| High | Low Stock | SmartMart Mussoorie | Earphones | 16.00% | Not applicable |
| High | Low Stock | SmartMart Haridwar Central | Dishwash Liquid 500ml | 18.00% | 708 days |
| High | Low Stock | SmartMart Mussoorie | Chips 150g | 19.00% | 146 days |
| High | Low Stock | SmartMart Roorkee | Packaged Juice 1L | 22.00% | 137 days |
| High | Low Stock | SmartMart Clock Tower | Sunflower Oil 1L | 23.00% | 333 days |
| High | Low Stock | SmartMart Mussoorie | Shampoo 180ml | 25.00% | 688 days |
| High | Stockout Risk | SmartMart Clock Tower | Instant Noodles Pack | 5.00% | 157 days |
| High | Stockout Risk | SmartMart Mussoorie | Packaged Juice 1L | 14.00% | 155 days |
| High | Stockout Risk | SmartMart Mussoorie | Earphones | 16.00% | Not applicable |
| High | Stockout Risk | SmartMart Haridwar Central | Dishwash Liquid 500ml | 18.00% | 708 days |
| High | Stockout Risk | SmartMart Mussoorie | Chips 150g | 19.00% | 146 days |
| High | Stockout Risk | SmartMart Roorkee | Packaged Juice 1L | 22.00% | 137 days |
| High | Stockout Risk | SmartMart Clock Tower | Sunflower Oil 1L | 23.00% | 333 days |
| High | Stockout Risk | SmartMart Mussoorie | Shampoo 180ml | 25.00% | 688 days |
| High | Stockout Risk | SmartMart Clock Tower | Biscuits 300g | 40.00% | 170 days |
| High | Stockout Risk | SmartMart Clock Tower | Chips 150g | 59.00% | 165 days |
| Medium | Low Stock | SmartMart Rajpur Road | Detergent Powder 1kg | 25.00% | 705 days |
| Medium | Low Stock | SmartMart Haridwar Central | Pen Pack of 10 | 26.00% | Not applicable |
| Medium | Low Stock | SmartMart Haldwani | USB Cable | 27.00% | Not applicable |
| Medium | Low Stock | SmartMart Rudrapur | Earphones | 28.00% | Not applicable |
| Medium | Low Stock | SmartMart Ballupur | Dishwash Liquid 500ml | 29.00% | 714 days |
| Medium | Low Stock | SmartMart Kashipur | Notebook | 30.00% | Not applicable |
| Medium | Low Stock | SmartMart Clock Tower | Coffee 200g | 31.00% | 328 days |
| Medium | Low Stock | SmartMart Kashipur | Tea 500g | 31.00% | 354 days |
| Medium | Low Stock | SmartMart Clock Tower | Earphones | 32.00% | Not applicable |
| Medium | Low Stock | SmartMart Haridwar Central | Shampoo 180ml | 35.00% | 689 days |
| Medium | Low Stock | SmartMart Clock Tower | Tea 500g | 36.00% | 306 days |
| Medium | Low Stock | SmartMart Kashipur | Dishwash Liquid 500ml | 36.00% | 715 days |
| Medium | Low Stock | SmartMart Ballupur | Earphones | 36.00% | Not applicable |
| Medium | Low Stock | SmartMart Clock Tower | Biscuits 300g | 40.00% | 170 days |
| Medium | Low Stock | SmartMart Mussoorie | Toothpaste 150g | 52.00% | 689 days |
| Medium | Low Stock | SmartMart Rishikesh | Floor Cleaner 1L | 55.00% | 718 days |
| Medium | Low Stock | SmartMart Clock Tower | Chips 150g | 59.00% | 165 days |
| Medium | Low Stock | SmartMart Mussoorie | Chocolate Bar | 62.00% | 159 days |
| Medium | Low Stock | SmartMart Haridwar Central | LED Bulb 9W | 62.00% | Not applicable |
| Medium | Low Stock | SmartMart Clock Tower | USB Cable | 63.00% | Not applicable |
| Medium | Low Stock | SmartMart Haridwar Central | Earphones | 64.00% | Not applicable |
| Medium | Low Stock | SmartMart Rudrapur | Shampoo 180ml | 68.00% | 705 days |
| Medium | Low Stock | SmartMart Clock Tower | Sugar 1kg | 69.00% | 341 days |
| Medium | Low Stock | SmartMart Ballupur | Sugar 1kg | 70.00% | 343 days |
| Medium | Low Stock | SmartMart Rishikesh | Detergent Powder 1kg | 73.00% | 702 days |
| Medium | Low Stock | SmartMart Haridwar Central | USB Cable | 73.00% | Not applicable |
| Medium | Low Stock | SmartMart Haldwani | Soap Pack of 4 | 74.00% | 689 days |
| Medium | Low Stock | SmartMart Kashipur | Biscuits 300g | 78.00% | 174 days |
| Medium | Low Stock | SmartMart Ballupur | Instant Noodles Pack | 79.00% | 141 days |
| Medium | Stockout Risk | SmartMart Rajpur Road | Detergent Powder 1kg | 25.00% | 705 days |
| Medium | Stockout Risk | SmartMart Haridwar Central | Pen Pack of 10 | 26.00% | Not applicable |
| Medium | Stockout Risk | SmartMart Haldwani | USB Cable | 27.00% | Not applicable |
| Medium | Stockout Risk | SmartMart Rudrapur | Earphones | 28.00% | Not applicable |
| Medium | Stockout Risk | SmartMart Ballupur | Dishwash Liquid 500ml | 29.00% | 714 days |
| Medium | Stockout Risk | SmartMart Kashipur | Notebook | 30.00% | Not applicable |
| Medium | Stockout Risk | SmartMart Clock Tower | Coffee 200g | 31.00% | 328 days |
| Medium | Stockout Risk | SmartMart Kashipur | Tea 500g | 31.00% | 354 days |
| Medium | Stockout Risk | SmartMart Clock Tower | Earphones | 32.00% | Not applicable |
| Medium | Stockout Risk | SmartMart Haridwar Central | Shampoo 180ml | 35.00% | 689 days |
| Medium | Stockout Risk | SmartMart Clock Tower | Tea 500g | 36.00% | 306 days |
| Medium | Stockout Risk | SmartMart Kashipur | Dishwash Liquid 500ml | 36.00% | 715 days |
| Medium | Stockout Risk | SmartMart Ballupur | Earphones | 36.00% | Not applicable |
| Low | Overstock | SmartMart Rishikesh | Tea 500g | 309.00% | 350 days |
| Low | Overstock | SmartMart Rajpur Road | Packaged Juice 1L | 312.00% | 155 days |
| Low | Overstock | SmartMart Kashipur | Pen Pack of 10 | 316.00% | Not applicable |
| Low | Overstock | SmartMart Kashipur | Face Wash 100ml | 320.00% | 691 days |
| Low | Overstock | SmartMart Ballupur | Basmati Rice 5kg | 327.00% | 347 days |
| Low | Overstock | SmartMart Rajpur Road | Soap Pack of 4 | 330.00% | 679 days |
| Low | Overstock | SmartMart Clock Tower | Pen Pack of 10 | 330.00% | Not applicable |
| Low | Overstock | SmartMart Kashipur | Toothpaste 150g | 335.00% | 687 days |
| Low | Overstock | SmartMart Rajpur Road | Toilet Cleaner 500ml | 336.00% | 676 days |
| Low | Overstock | SmartMart Rudrapur | Toilet Cleaner 500ml | 340.00% | 718 days |
| Low | Overstock | SmartMart Haldwani | Atta 5kg | 350.00% | 335 days |
| Low | Overstock | SmartMart Roorkee | Soap Pack of 4 | 351.00% | 707 days |
| Low | Overstock | SmartMart Rishikesh | Sugar 1kg | 359.00% | 322 days |
| Low | Overstock | SmartMart Haldwani | Shampoo 180ml | 367.00% | 714 days |
| Low | Overstock | SmartMart Rudrapur | Toothpaste 150g | 368.00% | 691 days |
| Low | Overstock | SmartMart Rudrapur | Soft Drink 750ml | 370.00% | 129 days |
| Low | Overstock | SmartMart Mussoorie | Sugar 1kg | 370.00% | 350 days |
| Low | Overstock | SmartMart Mussoorie | Coffee 200g | 383.00% | 312 days |
| Low | Overstock | SmartMart Haridwar Central | Toothpaste 150g | 385.00% | 673 days |
| Low | Overstock | SmartMart Rishikesh | Packaged Juice 1L | 392.00% | 141 days |
| Low | Overstock | SmartMart Kashipur | Coffee 200g | 394.00% | 309 days |
| Low | Overstock | SmartMart Haldwani | Basmati Rice 5kg | 415.00% | 325 days |
| Low | Overstock | SmartMart Ballupur | Face Wash 100ml | 423.00% | 698 days |
| Low | Overstock | SmartMart Haldwani | Notebook | 428.00% | Not applicable |
| Low | Overstock | SmartMart Rajpur Road | Dishwash Liquid 500ml | 433.00% | 723 days |
| Low | Overstock | SmartMart Ballupur | Coffee 200g | 434.00% | 320 days |
| Low | Overstock | SmartMart Haldwani | Sugar 1kg | 434.00% | 327 days |
| Low | Overstock | SmartMart Rishikesh | Shampoo 180ml | 438.00% | 677 days |
| Low | Reorder Soon | SmartMart Haridwar Central | Biscuits 300g | 80.00% | 167 days |
| Low | Reorder Soon | SmartMart Ballupur | Soap Pack of 4 | 80.00% | 721 days |
| Low | Reorder Soon | SmartMart Rishikesh | Notebook | 80.00% | Not applicable |
| Low | Reorder Soon | SmartMart Rishikesh | Earphones | 80.00% | Not applicable |
| Low | Reorder Soon | SmartMart Mussoorie | Instant Noodles Pack | 81.00% | 122 days |
| Low | Reorder Soon | SmartMart Rudrapur | Sugar 1kg | 82.00% | 348 days |
| Low | Reorder Soon | SmartMart Haldwani | Dishwash Liquid 500ml | 82.00% | 675 days |
| Low | Reorder Soon | SmartMart Rajpur Road | LED Bulb 9W | 82.00% | Not applicable |
| Low | Reorder Soon | SmartMart Roorkee | Chocolate Bar | 83.00% | 154 days |
| Low | Reorder Soon | SmartMart Rishikesh | Dishwash Liquid 500ml | 84.00% | 706 days |
| Low | Reorder Soon | SmartMart Rudrapur | Detergent Powder 1kg | 84.00% | 710 days |
| Low | Reorder Soon | SmartMart Clock Tower | LED Bulb 9W | 84.00% | Not applicable |
| Low | Reorder Soon | SmartMart Haldwani | LED Bulb 9W | 84.00% | Not applicable |
| Low | Reorder Soon | SmartMart Rudrapur | Floor Cleaner 1L | 85.00% | 714 days |
| Low | Reorder Soon | SmartMart Roorkee | Notebook | 85.00% | Not applicable |
| Low | Reorder Soon | SmartMart Rishikesh | Chocolate Bar | 87.00% | 140 days |
| Low | Reorder Soon | SmartMart Rishikesh | USB Cable | 87.00% | Not applicable |
| Low | Reorder Soon | SmartMart Mussoorie | USB Cable | 87.00% | Not applicable |
| Low | Reorder Soon | SmartMart Roorkee | Biscuits 300g | 88.00% | 131 days |
| Low | Reorder Soon | SmartMart Kashipur | Floor Cleaner 1L | 88.00% | 709 days |
| Low | Reorder Soon | SmartMart Kashipur | Instant Noodles Pack | 89.00% | 167 days |
| Low | Reorder Soon | SmartMart Rajpur Road | Basmati Rice 5kg | 90.00% | 322 days |
| Low | Reorder Soon | SmartMart Rajpur Road | Chips 150g | 91.00% | 168 days |
| Low | Reorder Soon | SmartMart Rudrapur | Soap Pack of 4 | 91.00% | 708 days |
| Low | Reorder Soon | SmartMart Ballupur | Chips 150g | 93.00% | 137 days |
| Low | Reorder Soon | SmartMart Mussoorie | Soap Pack of 4 | 93.00% | 716 days |
| Low | Reorder Soon | SmartMart Haldwani | Packaged Juice 1L | 94.00% | 160 days |
| Low | Reorder Soon | SmartMart Ballupur | Toilet Cleaner 500ml | 94.00% | 704 days |
| Low | Reorder Soon | SmartMart Rishikesh | Toilet Cleaner 500ml | 94.00% | 706 days |
| Low | Reorder Soon | SmartMart Haridwar Central | Chips 150g | 95.00% | 137 days |
| Low | Reorder Soon | SmartMart Mussoorie | Floor Cleaner 1L | 97.00% | 692 days |
| Low | Reorder Soon | SmartMart Roorkee | Face Wash 100ml | 97.00% | 707 days |
| Low | Reorder Soon | SmartMart Rishikesh | Biscuits 300g | 99.00% | 130 days |
| Low | Reorder Soon | SmartMart Mussoorie | Biscuits 300g | 99.00% | 164 days |

## Detailed Findings

### LOW-STOCK-S003-P017-2026-06-30

**Severity:** High

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** Instant Noodles Pack (P017)

**Summary:** Instant Noodles Pack is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 5; Reorder Level: 100; Stock Ratio: 5.00%; Reorder Required: Yes; Related Complaints: 67

### LOW-STOCK-S010-P007-2026-06-30

**Severity:** High

**Analysis Type:** Low Stock

**Store:** SmartMart Mussoorie (S010)

**Product:** Packaged Juice 1L (P007)

**Summary:** Packaged Juice 1L is marked as Low Stock at SmartMart Mussoorie.

**Evidence:** Current Stock: 7; Reorder Level: 50; Stock Ratio: 14.00%; Reorder Required: Yes; Related Complaints: 10

### LOW-STOCK-S010-P024-2026-06-30

**Severity:** High

**Analysis Type:** Low Stock

**Store:** SmartMart Mussoorie (S010)

**Product:** Earphones (P024)

**Summary:** Earphones is marked as Low Stock at SmartMart Mussoorie.

**Evidence:** Current Stock: 4; Reorder Level: 25; Stock Ratio: 16.00%; Reorder Required: Yes; Related Complaints: 7

### LOW-STOCK-S005-P013-2026-06-30

**Severity:** High

**Analysis Type:** Low Stock

**Store:** SmartMart Haridwar Central (S005)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml is marked as Low Stock at SmartMart Haridwar Central.

**Evidence:** Current Stock: 8; Reorder Level: 45; Stock Ratio: 17.78%; Reorder Required: Yes; Related Complaints: 7

### LOW-STOCK-S010-P019-2026-06-30

**Severity:** High

**Analysis Type:** Low Stock

**Store:** SmartMart Mussoorie (S010)

**Product:** Chips 150g (P019)

**Summary:** Chips 150g is marked as Low Stock at SmartMart Mussoorie.

**Evidence:** Current Stock: 19; Reorder Level: 100; Stock Ratio: 19.00%; Reorder Required: Yes; Related Complaints: 10

### LOW-STOCK-S006-P007-2026-06-30

**Severity:** High

**Analysis Type:** Low Stock

**Store:** SmartMart Roorkee (S006)

**Product:** Packaged Juice 1L (P007)

**Summary:** Packaged Juice 1L is marked as Low Stock at SmartMart Roorkee.

**Evidence:** Current Stock: 11; Reorder Level: 50; Stock Ratio: 22.00%; Reorder Required: Yes; Related Complaints: 7

### LOW-STOCK-S003-P003-2026-06-30

**Severity:** High

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** Sunflower Oil 1L (P003)

**Summary:** Sunflower Oil 1L is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 14; Reorder Level: 60; Stock Ratio: 23.33%; Reorder Required: Yes; Related Complaints: 3

### LOW-STOCK-S010-P009-2026-06-30

**Severity:** High

**Analysis Type:** Low Stock

**Store:** SmartMart Mussoorie (S010)

**Product:** Shampoo 180ml (P009)

**Summary:** Shampoo 180ml is marked as Low Stock at SmartMart Mussoorie.

**Evidence:** Current Stock: 10; Reorder Level: 40; Stock Ratio: 25.00%; Reorder Required: Yes; Related Complaints: 9

### STOCKOUT-RISK-S003-P017-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Clock Tower (S003)

**Product:** Instant Noodles Pack (P017)

**Summary:** Instant Noodles Pack has a stockout risk at SmartMart Clock Tower because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 5; Reorder Level: 100; Stock Ratio: 5.00%; Related Complaints: 67; High-Severity Complaints: 35; Vendor: QuickBite Foods

### STOCKOUT-RISK-S010-P007-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Mussoorie (S010)

**Product:** Packaged Juice 1L (P007)

**Summary:** Packaged Juice 1L has a stockout risk at SmartMart Mussoorie because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 7; Reorder Level: 50; Stock Ratio: 14.00%; Related Complaints: 10; High-Severity Complaints: 2; Vendor: CoolSip Distributors

### STOCKOUT-RISK-S010-P024-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Mussoorie (S010)

**Product:** Earphones (P024)

**Summary:** Earphones has a stockout risk at SmartMart Mussoorie because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 4; Reorder Level: 25; Stock Ratio: 16.00%; Related Complaints: 7; High-Severity Complaints: 0; Vendor: TechEase Accessories

### STOCKOUT-RISK-S005-P013-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Haridwar Central (S005)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml has a stockout risk at SmartMart Haridwar Central because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 8; Reorder Level: 45; Stock Ratio: 17.78%; Related Complaints: 7; High-Severity Complaints: 2; Vendor: HomeShine Supplies

### STOCKOUT-RISK-S010-P019-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Mussoorie (S010)

**Product:** Chips 150g (P019)

**Summary:** Chips 150g has a stockout risk at SmartMart Mussoorie because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 19; Reorder Level: 100; Stock Ratio: 19.00%; Related Complaints: 10; High-Severity Complaints: 1; Vendor: QuickBite Foods

### STOCKOUT-RISK-S006-P007-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Roorkee (S006)

**Product:** Packaged Juice 1L (P007)

**Summary:** Packaged Juice 1L has a stockout risk at SmartMart Roorkee because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 11; Reorder Level: 50; Stock Ratio: 22.00%; Related Complaints: 7; High-Severity Complaints: 1; Vendor: CoolSip Distributors

### STOCKOUT-RISK-S003-P003-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Clock Tower (S003)

**Product:** Sunflower Oil 1L (P003)

**Summary:** Sunflower Oil 1L has a stockout risk at SmartMart Clock Tower because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 14; Reorder Level: 60; Stock Ratio: 23.33%; Related Complaints: 3; High-Severity Complaints: 1; Vendor: FreshDrop Oils

### STOCKOUT-RISK-S010-P009-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Mussoorie (S010)

**Product:** Shampoo 180ml (P009)

**Summary:** Shampoo 180ml has a stockout risk at SmartMart Mussoorie because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 10; Reorder Level: 40; Stock Ratio: 25.00%; Related Complaints: 9; High-Severity Complaints: 1; Vendor: GlowCare Personal Products

### STOCKOUT-RISK-S003-P018-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Clock Tower (S003)

**Product:** Biscuits 300g (P018)

**Summary:** Biscuits 300g has a stockout risk at SmartMart Clock Tower because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 36; Reorder Level: 90; Stock Ratio: 40.00%; Related Complaints: 55; High-Severity Complaints: 30; Vendor: QuickBite Foods

### STOCKOUT-RISK-S003-P019-2026-06-30

**Severity:** High

**Analysis Type:** Stockout Risk

**Store:** SmartMart Clock Tower (S003)

**Product:** Chips 150g (P019)

**Summary:** Chips 150g has a stockout risk at SmartMart Clock Tower because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 59; Reorder Level: 100; Stock Ratio: 59.00%; Related Complaints: 59; High-Severity Complaints: 35; Vendor: QuickBite Foods

### LOW-STOCK-S001-P014-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Rajpur Road (S001)

**Product:** Detergent Powder 1kg (P014)

**Summary:** Detergent Powder 1kg is marked as Low Stock at SmartMart Rajpur Road.

**Evidence:** Current Stock: 14; Reorder Level: 55; Stock Ratio: 25.45%; Reorder Required: Yes; Related Complaints: 3

### LOW-STOCK-S005-P022-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Haridwar Central (S005)

**Product:** Pen Pack of 10 (P022)

**Summary:** Pen Pack of 10 is marked as Low Stock at SmartMart Haridwar Central.

**Evidence:** Current Stock: 13; Reorder Level: 50; Stock Ratio: 26.00%; Reorder Required: Yes; Related Complaints: 10

### LOW-STOCK-S007-P023-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Haldwani (S007)

**Product:** USB Cable (P023)

**Summary:** USB Cable is marked as Low Stock at SmartMart Haldwani.

**Evidence:** Current Stock: 8; Reorder Level: 30; Stock Ratio: 26.67%; Reorder Required: Yes; Related Complaints: 5

### LOW-STOCK-S009-P024-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Rudrapur (S009)

**Product:** Earphones (P024)

**Summary:** Earphones is marked as Low Stock at SmartMart Rudrapur.

**Evidence:** Current Stock: 7; Reorder Level: 25; Stock Ratio: 28.00%; Reorder Required: Yes; Related Complaints: 9

### LOW-STOCK-S002-P013-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Ballupur (S002)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml is marked as Low Stock at SmartMart Ballupur.

**Evidence:** Current Stock: 13; Reorder Level: 45; Stock Ratio: 28.89%; Reorder Required: Yes; Related Complaints: 8

### LOW-STOCK-S008-P021-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Kashipur (S008)

**Product:** Notebook (P021)

**Summary:** Notebook is marked as Low Stock at SmartMart Kashipur.

**Evidence:** Current Stock: 12; Reorder Level: 40; Stock Ratio: 30.00%; Reorder Required: Yes; Related Complaints: 6

### LOW-STOCK-S003-P006-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** Coffee 200g (P006)

**Summary:** Coffee 200g is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 11; Reorder Level: 35; Stock Ratio: 31.43%; Reorder Required: Yes; Related Complaints: 10

### LOW-STOCK-S008-P005-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Kashipur (S008)

**Product:** Tea 500g (P005)

**Summary:** Tea 500g is marked as Low Stock at SmartMart Kashipur.

**Evidence:** Current Stock: 14; Reorder Level: 45; Stock Ratio: 31.11%; Reorder Required: Yes; Related Complaints: 4

### LOW-STOCK-S003-P024-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** Earphones (P024)

**Summary:** Earphones is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 8; Reorder Level: 25; Stock Ratio: 32.00%; Reorder Required: Yes; Related Complaints: 1

### LOW-STOCK-S005-P009-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Haridwar Central (S005)

**Product:** Shampoo 180ml (P009)

**Summary:** Shampoo 180ml is marked as Low Stock at SmartMart Haridwar Central.

**Evidence:** Current Stock: 14; Reorder Level: 40; Stock Ratio: 35.00%; Reorder Required: Yes; Related Complaints: 4

### LOW-STOCK-S003-P005-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** Tea 500g (P005)

**Summary:** Tea 500g is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 16; Reorder Level: 45; Stock Ratio: 35.56%; Reorder Required: Yes; Related Complaints: 5

### LOW-STOCK-S008-P013-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Kashipur (S008)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml is marked as Low Stock at SmartMart Kashipur.

**Evidence:** Current Stock: 16; Reorder Level: 45; Stock Ratio: 35.56%; Reorder Required: Yes; Related Complaints: 5

### LOW-STOCK-S002-P024-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Ballupur (S002)

**Product:** Earphones (P024)

**Summary:** Earphones is marked as Low Stock at SmartMart Ballupur.

**Evidence:** Current Stock: 9; Reorder Level: 25; Stock Ratio: 36.00%; Reorder Required: Yes; Related Complaints: 7

### LOW-STOCK-S003-P018-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** Biscuits 300g (P018)

**Summary:** Biscuits 300g is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 36; Reorder Level: 90; Stock Ratio: 40.00%; Reorder Required: Yes; Related Complaints: 55

### LOW-STOCK-S010-P010-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Mussoorie (S010)

**Product:** Toothpaste 150g (P010)

**Summary:** Toothpaste 150g is marked as Low Stock at SmartMart Mussoorie.

**Evidence:** Current Stock: 31; Reorder Level: 60; Stock Ratio: 51.67%; Reorder Required: Yes; Related Complaints: 7

### LOW-STOCK-S004-P015-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Rishikesh (S004)

**Product:** Floor Cleaner 1L (P015)

**Summary:** Floor Cleaner 1L is marked as Low Stock at SmartMart Rishikesh.

**Evidence:** Current Stock: 22; Reorder Level: 40; Stock Ratio: 55.00%; Reorder Required: Yes; Related Complaints: 5

### LOW-STOCK-S003-P019-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** Chips 150g (P019)

**Summary:** Chips 150g is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 59; Reorder Level: 100; Stock Ratio: 59.00%; Reorder Required: Yes; Related Complaints: 59

### LOW-STOCK-S010-P020-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Mussoorie (S010)

**Product:** Chocolate Bar (P020)

**Summary:** Chocolate Bar is marked as Low Stock at SmartMart Mussoorie.

**Evidence:** Current Stock: 74; Reorder Level: 120; Stock Ratio: 61.67%; Reorder Required: Yes; Related Complaints: 3

### LOW-STOCK-S005-P025-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Haridwar Central (S005)

**Product:** LED Bulb 9W (P025)

**Summary:** LED Bulb 9W is marked as Low Stock at SmartMart Haridwar Central.

**Evidence:** Current Stock: 28; Reorder Level: 45; Stock Ratio: 62.22%; Reorder Required: Yes; Related Complaints: 4

### LOW-STOCK-S003-P023-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** USB Cable (P023)

**Summary:** USB Cable is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 19; Reorder Level: 30; Stock Ratio: 63.33%; Reorder Required: Yes; Related Complaints: 5

### LOW-STOCK-S005-P024-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Haridwar Central (S005)

**Product:** Earphones (P024)

**Summary:** Earphones is marked as Low Stock at SmartMart Haridwar Central.

**Evidence:** Current Stock: 16; Reorder Level: 25; Stock Ratio: 64.00%; Reorder Required: Yes; Related Complaints: 5

### LOW-STOCK-S009-P009-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Rudrapur (S009)

**Product:** Shampoo 180ml (P009)

**Summary:** Shampoo 180ml is marked as Low Stock at SmartMart Rudrapur.

**Evidence:** Current Stock: 27; Reorder Level: 40; Stock Ratio: 67.50%; Reorder Required: Yes; Related Complaints: 5

### LOW-STOCK-S003-P004-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Clock Tower (S003)

**Product:** Sugar 1kg (P004)

**Summary:** Sugar 1kg is marked as Low Stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 55; Reorder Level: 80; Stock Ratio: 68.75%; Reorder Required: Yes; Related Complaints: 2

### LOW-STOCK-S002-P004-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Ballupur (S002)

**Product:** Sugar 1kg (P004)

**Summary:** Sugar 1kg is marked as Low Stock at SmartMart Ballupur.

**Evidence:** Current Stock: 56; Reorder Level: 80; Stock Ratio: 70.00%; Reorder Required: Yes; Related Complaints: 8

### LOW-STOCK-S004-P014-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Rishikesh (S004)

**Product:** Detergent Powder 1kg (P014)

**Summary:** Detergent Powder 1kg is marked as Low Stock at SmartMart Rishikesh.

**Evidence:** Current Stock: 40; Reorder Level: 55; Stock Ratio: 72.73%; Reorder Required: Yes; Related Complaints: 10

### LOW-STOCK-S005-P023-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Haridwar Central (S005)

**Product:** USB Cable (P023)

**Summary:** USB Cable is marked as Low Stock at SmartMart Haridwar Central.

**Evidence:** Current Stock: 22; Reorder Level: 30; Stock Ratio: 73.33%; Reorder Required: Yes; Related Complaints: 2

### LOW-STOCK-S007-P011-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Haldwani (S007)

**Product:** Soap Pack of 4 (P011)

**Summary:** Soap Pack of 4 is marked as Low Stock at SmartMart Haldwani.

**Evidence:** Current Stock: 52; Reorder Level: 70; Stock Ratio: 74.29%; Reorder Required: Yes; Related Complaints: 0

### LOW-STOCK-S008-P018-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Kashipur (S008)

**Product:** Biscuits 300g (P018)

**Summary:** Biscuits 300g is marked as Low Stock at SmartMart Kashipur.

**Evidence:** Current Stock: 70; Reorder Level: 90; Stock Ratio: 77.78%; Reorder Required: Yes; Related Complaints: 5

### LOW-STOCK-S002-P017-2026-06-30

**Severity:** Medium

**Analysis Type:** Low Stock

**Store:** SmartMart Ballupur (S002)

**Product:** Instant Noodles Pack (P017)

**Summary:** Instant Noodles Pack is marked as Low Stock at SmartMart Ballupur.

**Evidence:** Current Stock: 79; Reorder Level: 100; Stock Ratio: 79.00%; Reorder Required: Yes; Related Complaints: 8

### STOCKOUT-RISK-S001-P014-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Rajpur Road (S001)

**Product:** Detergent Powder 1kg (P014)

**Summary:** Detergent Powder 1kg has a stockout risk at SmartMart Rajpur Road because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 14; Reorder Level: 55; Stock Ratio: 25.45%; Related Complaints: 3; High-Severity Complaints: 1; Vendor: HomeShine Supplies

### STOCKOUT-RISK-S005-P022-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Haridwar Central (S005)

**Product:** Pen Pack of 10 (P022)

**Summary:** Pen Pack of 10 has a stockout risk at SmartMart Haridwar Central because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 13; Reorder Level: 50; Stock Ratio: 26.00%; Related Complaints: 10; High-Severity Complaints: 0; Vendor: WriteWell Stationery

### STOCKOUT-RISK-S007-P023-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Haldwani (S007)

**Product:** USB Cable (P023)

**Summary:** USB Cable has a stockout risk at SmartMart Haldwani because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 8; Reorder Level: 30; Stock Ratio: 26.67%; Related Complaints: 5; High-Severity Complaints: 0; Vendor: TechEase Accessories

### STOCKOUT-RISK-S009-P024-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Rudrapur (S009)

**Product:** Earphones (P024)

**Summary:** Earphones has a stockout risk at SmartMart Rudrapur because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 7; Reorder Level: 25; Stock Ratio: 28.00%; Related Complaints: 9; High-Severity Complaints: 0; Vendor: TechEase Accessories

### STOCKOUT-RISK-S002-P013-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Ballupur (S002)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml has a stockout risk at SmartMart Ballupur because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 13; Reorder Level: 45; Stock Ratio: 28.89%; Related Complaints: 8; High-Severity Complaints: 1; Vendor: HomeShine Supplies

### STOCKOUT-RISK-S008-P021-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Kashipur (S008)

**Product:** Notebook (P021)

**Summary:** Notebook has a stockout risk at SmartMart Kashipur because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 12; Reorder Level: 40; Stock Ratio: 30.00%; Related Complaints: 6; High-Severity Complaints: 0; Vendor: WriteWell Stationery

### STOCKOUT-RISK-S003-P006-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Clock Tower (S003)

**Product:** Coffee 200g (P006)

**Summary:** Coffee 200g has a stockout risk at SmartMart Clock Tower because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 11; Reorder Level: 35; Stock Ratio: 31.43%; Related Complaints: 10; High-Severity Complaints: 3; Vendor: BrewLeaf Beverages

### STOCKOUT-RISK-S008-P005-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Kashipur (S008)

**Product:** Tea 500g (P005)

**Summary:** Tea 500g has a stockout risk at SmartMart Kashipur because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 14; Reorder Level: 45; Stock Ratio: 31.11%; Related Complaints: 4; High-Severity Complaints: 0; Vendor: BrewLeaf Beverages

### STOCKOUT-RISK-S003-P024-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Clock Tower (S003)

**Product:** Earphones (P024)

**Summary:** Earphones has a stockout risk at SmartMart Clock Tower because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 8; Reorder Level: 25; Stock Ratio: 32.00%; Related Complaints: 1; High-Severity Complaints: 0; Vendor: TechEase Accessories

### STOCKOUT-RISK-S005-P009-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Haridwar Central (S005)

**Product:** Shampoo 180ml (P009)

**Summary:** Shampoo 180ml has a stockout risk at SmartMart Haridwar Central because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 14; Reorder Level: 40; Stock Ratio: 35.00%; Related Complaints: 4; High-Severity Complaints: 1; Vendor: GlowCare Personal Products

### STOCKOUT-RISK-S003-P005-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Clock Tower (S003)

**Product:** Tea 500g (P005)

**Summary:** Tea 500g has a stockout risk at SmartMart Clock Tower because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 16; Reorder Level: 45; Stock Ratio: 35.56%; Related Complaints: 5; High-Severity Complaints: 3; Vendor: BrewLeaf Beverages

### STOCKOUT-RISK-S008-P013-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Kashipur (S008)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml has a stockout risk at SmartMart Kashipur because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 16; Reorder Level: 45; Stock Ratio: 35.56%; Related Complaints: 5; High-Severity Complaints: 0; Vendor: HomeShine Supplies

### STOCKOUT-RISK-S002-P024-2026-06-30

**Severity:** Medium

**Analysis Type:** Stockout Risk

**Store:** SmartMart Ballupur (S002)

**Product:** Earphones (P024)

**Summary:** Earphones has a stockout risk at SmartMart Ballupur because stock is critically low and may affect customer availability.

**Evidence:** Current Stock: 9; Reorder Level: 25; Stock Ratio: 36.00%; Related Complaints: 7; High-Severity Complaints: 0; Vendor: TechEase Accessories

### OVERSTOCK-S004-P005-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rishikesh (S004)

**Product:** Tea 500g (P005)

**Summary:** Tea 500g has excess stock at SmartMart Rishikesh.

**Evidence:** Current Stock: 139; Reorder Level: 45; Stock Ratio: 308.89%; Stock Status: Overstock

### OVERSTOCK-S001-P007-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rajpur Road (S001)

**Product:** Packaged Juice 1L (P007)

**Summary:** Packaged Juice 1L has excess stock at SmartMart Rajpur Road.

**Evidence:** Current Stock: 156; Reorder Level: 50; Stock Ratio: 312.00%; Stock Status: Overstock

### OVERSTOCK-S008-P022-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Kashipur (S008)

**Product:** Pen Pack of 10 (P022)

**Summary:** Pen Pack of 10 has excess stock at SmartMart Kashipur.

**Evidence:** Current Stock: 158; Reorder Level: 50; Stock Ratio: 316.00%; Stock Status: Overstock

### OVERSTOCK-S008-P012-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Kashipur (S008)

**Product:** Face Wash 100ml (P012)

**Summary:** Face Wash 100ml has excess stock at SmartMart Kashipur.

**Evidence:** Current Stock: 112; Reorder Level: 35; Stock Ratio: 320.00%; Stock Status: Overstock

### OVERSTOCK-S002-P002-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Ballupur (S002)

**Product:** Basmati Rice 5kg (P002)

**Summary:** Basmati Rice 5kg has excess stock at SmartMart Ballupur.

**Evidence:** Current Stock: 131; Reorder Level: 40; Stock Ratio: 327.50%; Stock Status: Overstock

### OVERSTOCK-S001-P011-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rajpur Road (S001)

**Product:** Soap Pack of 4 (P011)

**Summary:** Soap Pack of 4 has excess stock at SmartMart Rajpur Road.

**Evidence:** Current Stock: 231; Reorder Level: 70; Stock Ratio: 330.00%; Stock Status: Overstock

### OVERSTOCK-S003-P022-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Clock Tower (S003)

**Product:** Pen Pack of 10 (P022)

**Summary:** Pen Pack of 10 has excess stock at SmartMart Clock Tower.

**Evidence:** Current Stock: 165; Reorder Level: 50; Stock Ratio: 330.00%; Stock Status: Overstock

### OVERSTOCK-S008-P010-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Kashipur (S008)

**Product:** Toothpaste 150g (P010)

**Summary:** Toothpaste 150g has excess stock at SmartMart Kashipur.

**Evidence:** Current Stock: 201; Reorder Level: 60; Stock Ratio: 335.00%; Stock Status: Overstock

### OVERSTOCK-S001-P016-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rajpur Road (S001)

**Product:** Toilet Cleaner 500ml (P016)

**Summary:** Toilet Cleaner 500ml has excess stock at SmartMart Rajpur Road.

**Evidence:** Current Stock: 168; Reorder Level: 50; Stock Ratio: 336.00%; Stock Status: Overstock

### OVERSTOCK-S009-P016-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rudrapur (S009)

**Product:** Toilet Cleaner 500ml (P016)

**Summary:** Toilet Cleaner 500ml has excess stock at SmartMart Rudrapur.

**Evidence:** Current Stock: 170; Reorder Level: 50; Stock Ratio: 340.00%; Stock Status: Overstock

### OVERSTOCK-S007-P001-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Haldwani (S007)

**Product:** Atta 5kg (P001)

**Summary:** Atta 5kg has excess stock at SmartMart Haldwani.

**Evidence:** Current Stock: 175; Reorder Level: 50; Stock Ratio: 350.00%; Stock Status: Overstock

### OVERSTOCK-S006-P011-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Roorkee (S006)

**Product:** Soap Pack of 4 (P011)

**Summary:** Soap Pack of 4 has excess stock at SmartMart Roorkee.

**Evidence:** Current Stock: 246; Reorder Level: 70; Stock Ratio: 351.43%; Stock Status: Overstock

### OVERSTOCK-S004-P004-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rishikesh (S004)

**Product:** Sugar 1kg (P004)

**Summary:** Sugar 1kg has excess stock at SmartMart Rishikesh.

**Evidence:** Current Stock: 287; Reorder Level: 80; Stock Ratio: 358.75%; Stock Status: Overstock

### OVERSTOCK-S007-P009-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Haldwani (S007)

**Product:** Shampoo 180ml (P009)

**Summary:** Shampoo 180ml has excess stock at SmartMart Haldwani.

**Evidence:** Current Stock: 147; Reorder Level: 40; Stock Ratio: 367.50%; Stock Status: Overstock

### OVERSTOCK-S009-P010-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rudrapur (S009)

**Product:** Toothpaste 150g (P010)

**Summary:** Toothpaste 150g has excess stock at SmartMart Rudrapur.

**Evidence:** Current Stock: 221; Reorder Level: 60; Stock Ratio: 368.33%; Stock Status: Overstock

### OVERSTOCK-S009-P008-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rudrapur (S009)

**Product:** Soft Drink 750ml (P008)

**Summary:** Soft Drink 750ml has excess stock at SmartMart Rudrapur.

**Evidence:** Current Stock: 370; Reorder Level: 100; Stock Ratio: 370.00%; Stock Status: Overstock

### OVERSTOCK-S010-P004-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Mussoorie (S010)

**Product:** Sugar 1kg (P004)

**Summary:** Sugar 1kg has excess stock at SmartMart Mussoorie.

**Evidence:** Current Stock: 296; Reorder Level: 80; Stock Ratio: 370.00%; Stock Status: Overstock

### OVERSTOCK-S010-P006-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Mussoorie (S010)

**Product:** Coffee 200g (P006)

**Summary:** Coffee 200g has excess stock at SmartMart Mussoorie.

**Evidence:** Current Stock: 134; Reorder Level: 35; Stock Ratio: 382.86%; Stock Status: Overstock

### OVERSTOCK-S005-P010-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Haridwar Central (S005)

**Product:** Toothpaste 150g (P010)

**Summary:** Toothpaste 150g has excess stock at SmartMart Haridwar Central.

**Evidence:** Current Stock: 231; Reorder Level: 60; Stock Ratio: 385.00%; Stock Status: Overstock

### OVERSTOCK-S004-P007-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rishikesh (S004)

**Product:** Packaged Juice 1L (P007)

**Summary:** Packaged Juice 1L has excess stock at SmartMart Rishikesh.

**Evidence:** Current Stock: 196; Reorder Level: 50; Stock Ratio: 392.00%; Stock Status: Overstock

### OVERSTOCK-S008-P006-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Kashipur (S008)

**Product:** Coffee 200g (P006)

**Summary:** Coffee 200g has excess stock at SmartMart Kashipur.

**Evidence:** Current Stock: 138; Reorder Level: 35; Stock Ratio: 394.29%; Stock Status: Overstock

### OVERSTOCK-S007-P002-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Haldwani (S007)

**Product:** Basmati Rice 5kg (P002)

**Summary:** Basmati Rice 5kg has excess stock at SmartMart Haldwani.

**Evidence:** Current Stock: 166; Reorder Level: 40; Stock Ratio: 415.00%; Stock Status: Overstock

### OVERSTOCK-S002-P012-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Ballupur (S002)

**Product:** Face Wash 100ml (P012)

**Summary:** Face Wash 100ml has excess stock at SmartMart Ballupur.

**Evidence:** Current Stock: 148; Reorder Level: 35; Stock Ratio: 422.86%; Stock Status: Overstock

### OVERSTOCK-S007-P021-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Haldwani (S007)

**Product:** Notebook (P021)

**Summary:** Notebook has excess stock at SmartMart Haldwani.

**Evidence:** Current Stock: 171; Reorder Level: 40; Stock Ratio: 427.50%; Stock Status: Overstock

### OVERSTOCK-S001-P013-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rajpur Road (S001)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml has excess stock at SmartMart Rajpur Road.

**Evidence:** Current Stock: 195; Reorder Level: 45; Stock Ratio: 433.33%; Stock Status: Overstock

### OVERSTOCK-S002-P006-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Ballupur (S002)

**Product:** Coffee 200g (P006)

**Summary:** Coffee 200g has excess stock at SmartMart Ballupur.

**Evidence:** Current Stock: 152; Reorder Level: 35; Stock Ratio: 434.29%; Stock Status: Overstock

### OVERSTOCK-S007-P004-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Haldwani (S007)

**Product:** Sugar 1kg (P004)

**Summary:** Sugar 1kg has excess stock at SmartMart Haldwani.

**Evidence:** Current Stock: 347; Reorder Level: 80; Stock Ratio: 433.75%; Stock Status: Overstock

### OVERSTOCK-S004-P009-2026-06-30

**Severity:** Low

**Analysis Type:** Overstock

**Store:** SmartMart Rishikesh (S004)

**Product:** Shampoo 180ml (P009)

**Summary:** Shampoo 180ml has excess stock at SmartMart Rishikesh.

**Evidence:** Current Stock: 175; Reorder Level: 40; Stock Ratio: 437.50%; Stock Status: Overstock

### REORDER-SOON-S005-P018-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Haridwar Central (S005)

**Product:** Biscuits 300g (P018)

**Summary:** Biscuits 300g is approaching its reorder level at SmartMart Haridwar Central.

**Evidence:** Current Stock: 72; Reorder Level: 90; Stock Ratio: 80.00%; Vendor: QuickBite Foods

### REORDER-SOON-S002-P011-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Ballupur (S002)

**Product:** Soap Pack of 4 (P011)

**Summary:** Soap Pack of 4 is approaching its reorder level at SmartMart Ballupur.

**Evidence:** Current Stock: 56; Reorder Level: 70; Stock Ratio: 80.00%; Vendor: GlowCare Personal Products

### REORDER-SOON-S004-P021-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rishikesh (S004)

**Product:** Notebook (P021)

**Summary:** Notebook is approaching its reorder level at SmartMart Rishikesh.

**Evidence:** Current Stock: 32; Reorder Level: 40; Stock Ratio: 80.00%; Vendor: WriteWell Stationery

### REORDER-SOON-S004-P024-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rishikesh (S004)

**Product:** Earphones (P024)

**Summary:** Earphones is approaching its reorder level at SmartMart Rishikesh.

**Evidence:** Current Stock: 20; Reorder Level: 25; Stock Ratio: 80.00%; Vendor: TechEase Accessories

### REORDER-SOON-S010-P017-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Mussoorie (S010)

**Product:** Instant Noodles Pack (P017)

**Summary:** Instant Noodles Pack is approaching its reorder level at SmartMart Mussoorie.

**Evidence:** Current Stock: 81; Reorder Level: 100; Stock Ratio: 81.00%; Vendor: QuickBite Foods

### REORDER-SOON-S009-P004-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rudrapur (S009)

**Product:** Sugar 1kg (P004)

**Summary:** Sugar 1kg is approaching its reorder level at SmartMart Rudrapur.

**Evidence:** Current Stock: 66; Reorder Level: 80; Stock Ratio: 82.50%; Vendor: GrainPro Suppliers

### REORDER-SOON-S007-P013-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Haldwani (S007)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml is approaching its reorder level at SmartMart Haldwani.

**Evidence:** Current Stock: 37; Reorder Level: 45; Stock Ratio: 82.22%; Vendor: HomeShine Supplies

### REORDER-SOON-S001-P025-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rajpur Road (S001)

**Product:** LED Bulb 9W (P025)

**Summary:** LED Bulb 9W is approaching its reorder level at SmartMart Rajpur Road.

**Evidence:** Current Stock: 37; Reorder Level: 45; Stock Ratio: 82.22%; Vendor: BrightLite Electricals

### REORDER-SOON-S006-P020-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Roorkee (S006)

**Product:** Chocolate Bar (P020)

**Summary:** Chocolate Bar is approaching its reorder level at SmartMart Roorkee.

**Evidence:** Current Stock: 100; Reorder Level: 120; Stock Ratio: 83.33%; Vendor: QuickBite Foods

### REORDER-SOON-S004-P013-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rishikesh (S004)

**Product:** Dishwash Liquid 500ml (P013)

**Summary:** Dishwash Liquid 500ml is approaching its reorder level at SmartMart Rishikesh.

**Evidence:** Current Stock: 38; Reorder Level: 45; Stock Ratio: 84.44%; Vendor: HomeShine Supplies

### REORDER-SOON-S009-P014-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rudrapur (S009)

**Product:** Detergent Powder 1kg (P014)

**Summary:** Detergent Powder 1kg is approaching its reorder level at SmartMart Rudrapur.

**Evidence:** Current Stock: 46; Reorder Level: 55; Stock Ratio: 83.64%; Vendor: HomeShine Supplies

### REORDER-SOON-S003-P025-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Clock Tower (S003)

**Product:** LED Bulb 9W (P025)

**Summary:** LED Bulb 9W is approaching its reorder level at SmartMart Clock Tower.

**Evidence:** Current Stock: 38; Reorder Level: 45; Stock Ratio: 84.44%; Vendor: BrightLite Electricals

### REORDER-SOON-S007-P025-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Haldwani (S007)

**Product:** LED Bulb 9W (P025)

**Summary:** LED Bulb 9W is approaching its reorder level at SmartMart Haldwani.

**Evidence:** Current Stock: 38; Reorder Level: 45; Stock Ratio: 84.44%; Vendor: BrightLite Electricals

### REORDER-SOON-S009-P015-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rudrapur (S009)

**Product:** Floor Cleaner 1L (P015)

**Summary:** Floor Cleaner 1L is approaching its reorder level at SmartMart Rudrapur.

**Evidence:** Current Stock: 34; Reorder Level: 40; Stock Ratio: 85.00%; Vendor: HomeShine Supplies

### REORDER-SOON-S006-P021-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Roorkee (S006)

**Product:** Notebook (P021)

**Summary:** Notebook is approaching its reorder level at SmartMart Roorkee.

**Evidence:** Current Stock: 34; Reorder Level: 40; Stock Ratio: 85.00%; Vendor: WriteWell Stationery

### REORDER-SOON-S004-P020-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rishikesh (S004)

**Product:** Chocolate Bar (P020)

**Summary:** Chocolate Bar is approaching its reorder level at SmartMart Rishikesh.

**Evidence:** Current Stock: 104; Reorder Level: 120; Stock Ratio: 86.67%; Vendor: QuickBite Foods

### REORDER-SOON-S004-P023-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rishikesh (S004)

**Product:** USB Cable (P023)

**Summary:** USB Cable is approaching its reorder level at SmartMart Rishikesh.

**Evidence:** Current Stock: 26; Reorder Level: 30; Stock Ratio: 86.67%; Vendor: TechEase Accessories

### REORDER-SOON-S010-P023-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Mussoorie (S010)

**Product:** USB Cable (P023)

**Summary:** USB Cable is approaching its reorder level at SmartMart Mussoorie.

**Evidence:** Current Stock: 26; Reorder Level: 30; Stock Ratio: 86.67%; Vendor: TechEase Accessories

### REORDER-SOON-S006-P018-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Roorkee (S006)

**Product:** Biscuits 300g (P018)

**Summary:** Biscuits 300g is approaching its reorder level at SmartMart Roorkee.

**Evidence:** Current Stock: 79; Reorder Level: 90; Stock Ratio: 87.78%; Vendor: QuickBite Foods

### REORDER-SOON-S008-P015-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Kashipur (S008)

**Product:** Floor Cleaner 1L (P015)

**Summary:** Floor Cleaner 1L is approaching its reorder level at SmartMart Kashipur.

**Evidence:** Current Stock: 35; Reorder Level: 40; Stock Ratio: 87.50%; Vendor: HomeShine Supplies

### REORDER-SOON-S008-P017-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Kashipur (S008)

**Product:** Instant Noodles Pack (P017)

**Summary:** Instant Noodles Pack is approaching its reorder level at SmartMart Kashipur.

**Evidence:** Current Stock: 89; Reorder Level: 100; Stock Ratio: 89.00%; Vendor: QuickBite Foods

### REORDER-SOON-S001-P002-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rajpur Road (S001)

**Product:** Basmati Rice 5kg (P002)

**Summary:** Basmati Rice 5kg is approaching its reorder level at SmartMart Rajpur Road.

**Evidence:** Current Stock: 36; Reorder Level: 40; Stock Ratio: 90.00%; Vendor: GrainPro Suppliers

### REORDER-SOON-S001-P019-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rajpur Road (S001)

**Product:** Chips 150g (P019)

**Summary:** Chips 150g is approaching its reorder level at SmartMart Rajpur Road.

**Evidence:** Current Stock: 91; Reorder Level: 100; Stock Ratio: 91.00%; Vendor: QuickBite Foods

### REORDER-SOON-S009-P011-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rudrapur (S009)

**Product:** Soap Pack of 4 (P011)

**Summary:** Soap Pack of 4 is approaching its reorder level at SmartMart Rudrapur.

**Evidence:** Current Stock: 64; Reorder Level: 70; Stock Ratio: 91.43%; Vendor: GlowCare Personal Products

### REORDER-SOON-S002-P019-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Ballupur (S002)

**Product:** Chips 150g (P019)

**Summary:** Chips 150g is approaching its reorder level at SmartMart Ballupur.

**Evidence:** Current Stock: 93; Reorder Level: 100; Stock Ratio: 93.00%; Vendor: QuickBite Foods

### REORDER-SOON-S010-P011-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Mussoorie (S010)

**Product:** Soap Pack of 4 (P011)

**Summary:** Soap Pack of 4 is approaching its reorder level at SmartMart Mussoorie.

**Evidence:** Current Stock: 65; Reorder Level: 70; Stock Ratio: 92.86%; Vendor: GlowCare Personal Products

### REORDER-SOON-S007-P007-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Haldwani (S007)

**Product:** Packaged Juice 1L (P007)

**Summary:** Packaged Juice 1L is approaching its reorder level at SmartMart Haldwani.

**Evidence:** Current Stock: 47; Reorder Level: 50; Stock Ratio: 94.00%; Vendor: CoolSip Distributors

### REORDER-SOON-S002-P016-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Ballupur (S002)

**Product:** Toilet Cleaner 500ml (P016)

**Summary:** Toilet Cleaner 500ml is approaching its reorder level at SmartMart Ballupur.

**Evidence:** Current Stock: 47; Reorder Level: 50; Stock Ratio: 94.00%; Vendor: HomeShine Supplies

### REORDER-SOON-S004-P016-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rishikesh (S004)

**Product:** Toilet Cleaner 500ml (P016)

**Summary:** Toilet Cleaner 500ml is approaching its reorder level at SmartMart Rishikesh.

**Evidence:** Current Stock: 47; Reorder Level: 50; Stock Ratio: 94.00%; Vendor: HomeShine Supplies

### REORDER-SOON-S005-P019-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Haridwar Central (S005)

**Product:** Chips 150g (P019)

**Summary:** Chips 150g is approaching its reorder level at SmartMart Haridwar Central.

**Evidence:** Current Stock: 95; Reorder Level: 100; Stock Ratio: 95.00%; Vendor: QuickBite Foods

### REORDER-SOON-S010-P015-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Mussoorie (S010)

**Product:** Floor Cleaner 1L (P015)

**Summary:** Floor Cleaner 1L is approaching its reorder level at SmartMart Mussoorie.

**Evidence:** Current Stock: 39; Reorder Level: 40; Stock Ratio: 97.50%; Vendor: HomeShine Supplies

### REORDER-SOON-S006-P012-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Roorkee (S006)

**Product:** Face Wash 100ml (P012)

**Summary:** Face Wash 100ml is approaching its reorder level at SmartMart Roorkee.

**Evidence:** Current Stock: 34; Reorder Level: 35; Stock Ratio: 97.14%; Vendor: GlowCare Personal Products

### REORDER-SOON-S004-P018-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Rishikesh (S004)

**Product:** Biscuits 300g (P018)

**Summary:** Biscuits 300g is approaching its reorder level at SmartMart Rishikesh.

**Evidence:** Current Stock: 89; Reorder Level: 90; Stock Ratio: 98.89%; Vendor: QuickBite Foods

### REORDER-SOON-S010-P018-2026-06-30

**Severity:** Low

**Analysis Type:** Reorder Soon

**Store:** SmartMart Mussoorie (S010)

**Product:** Biscuits 300g (P018)

**Summary:** Biscuits 300g is approaching its reorder level at SmartMart Mussoorie.

**Evidence:** Current Stock: 89; Reorder Level: 90; Stock Ratio: 98.89%; Vendor: QuickBite Foods
