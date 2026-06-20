import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

np.random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[2]

products_path = BASE_DIR / "data" / "raw" / "products_data.csv"
stores_path = BASE_DIR / "data" / "raw" / "stores_data.csv"
output_path = BASE_DIR / "data" / "raw" / "inventory_data.csv"

products = pd.read_csv(products_path)
stores = pd.read_csv(stores_path)

inventory_records = []
inventory_id = 1

inventory_date = datetime(2026, 6, 30)

# Business thresholds
REORDER_TRIGGER_PERCENT = 0.80
OVERSTOCK_MULTIPLIER = 3.00


def randint_inclusive(low, high):
    """
    Generates a random integer including both low and high.
    Also prevents errors if low becomes greater than high.
    """
    low = int(max(1, low))
    high = int(max(low, high))
    return np.random.randint(low, high + 1)


for _, store in stores.iterrows():
    for _, product in products.iterrows():

        reorder_level = int(product["reorder_level"])

        # Reorder trigger level means the actual point below which reorder is required
        reorder_trigger_level = int(reorder_level * REORDER_TRIGGER_PERCENT)

        # General real-life inventory distribution
        # Most products are normal, some are near reorder, few are low stock, few are overstock
        stock_pattern = np.random.choice(
            ["normal", "reorder_soon", "low_stock", "overstock"],
            p=[0.65, 0.15, 0.12, 0.08]
        )

        if stock_pattern == "normal":
            current_stock = randint_inclusive(
                reorder_level,
                int(reorder_level * 2.5)
            )

        elif stock_pattern == "reorder_soon":
            current_stock = randint_inclusive(
                reorder_trigger_level,
                reorder_level - 1
            )

        elif stock_pattern == "low_stock":
            current_stock = randint_inclusive(
                int(reorder_level * 0.15),
                reorder_trigger_level - 1
            )

        else:
            current_stock = randint_inclusive(
                int(reorder_level * 3.1),
                int(reorder_level * 4.5)
            )

        # Intentional low stock problems
        if store["store_id"] == "S003" and product["product_id"] in ["P017", "P018", "P019"]:
            current_stock = randint_inclusive(
                5,
                reorder_trigger_level - 1
            )

        if store["store_id"] == "S005" and product["product_id"] in ["P023", "P024"]:
            current_stock = randint_inclusive(
                3,
                reorder_trigger_level - 1
            )

        # Intentional overstock problem
        if store["store_id"] == "S007" and product["product_id"] in ["P001", "P002"]:
            current_stock = randint_inclusive(
                int(reorder_level * 3.2),
                int(reorder_level * 4.5)
            )

        # Stock status logic
        if current_stock < reorder_trigger_level:
            stock_status = "Low Stock"
            reorder_required = "Yes"

        elif current_stock < reorder_level:
            stock_status = "Reorder Soon"
            reorder_required = "No"

        elif current_stock > reorder_level * OVERSTOCK_MULTIPLIER:
            stock_status = "Overstock"
            reorder_required = "No"

        else:
            stock_status = "Normal"
            reorder_required = "No"

        shelf_life = pd.to_numeric(product["shelf_life_days"], errors="coerce")

        if pd.notna(shelf_life) and shelf_life > 0:
            last_restock_date = inventory_date - timedelta(days=np.random.randint(5, 60))
            expiry_date = last_restock_date + timedelta(days=int(shelf_life))
            expiry_date = expiry_date.strftime("%Y-%m-%d")
        else:
            expiry_date = "NA"

        inventory_records.append({
            "inventory_id": f"INV{inventory_id:05d}",
            "date": inventory_date.strftime("%Y-%m-%d"),
            "store_id": store["store_id"],
            "store_name": store["store_name"],
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category": product["category"],
            "vendor_id": product["vendor_id"],
            "current_stock": current_stock,
            "reorder_level": reorder_level,
            "reorder_trigger_level": reorder_trigger_level,
            "stock_status": stock_status,
            "reorder_required": reorder_required,
            "expiry_date": expiry_date
        })

        inventory_id += 1

inventory_data = pd.DataFrame(inventory_records)

inventory_data.to_csv(output_path, index=False)

print(f"inventory_data.csv created successfully at: {output_path}")
print(f"Total rows created: {len(inventory_data)}")