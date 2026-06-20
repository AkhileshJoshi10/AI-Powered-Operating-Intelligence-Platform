import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Set random seed for same output every time
np.random.seed(42)

# Paths
BASE_DIR = Path(__file__).resolve().parents[2]
products_path = BASE_DIR / "data" / "raw" / "products_data.csv"
stores_path = BASE_DIR / "data" / "raw" / "stores_data.csv"
output_path = BASE_DIR / "data" / "raw" / "sales_data.csv"

# Load master data
products = pd.read_csv(products_path)
stores = pd.read_csv(stores_path)

# Date range
start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 6, 30)
dates = pd.date_range(start_date, end_date)

sales_records = []
sale_id = 1

for date in dates:
    for _, store in stores.iterrows():
        daily_transactions = np.random.randint(15, 35)

        for _ in range(daily_transactions):
            product = products.sample(1).iloc[0]

            quantity_sold = np.random.randint(1, 12)
            unit_price = product["unit_price"]
            cost_price = product["cost_price"]

            discount_percent = np.random.choice([0, 5, 10, 15], p=[0.55, 0.25, 0.15, 0.05])
            selling_price = unit_price * (1 - discount_percent / 100)

            total_sales = quantity_sold * selling_price
            total_cost = quantity_sold * cost_price
            profit = total_sales - total_cost

            # Intentional business problem:
            # Store S003 sales decline in June
            if store["store_id"] == "S003" and date.month == 6:
                quantity_sold = max(1, int(quantity_sold * 0.45))
                total_sales = quantity_sold * selling_price
                total_cost = quantity_sold * cost_price
                profit = total_sales - total_cost

            payment_status = np.random.choice(
                ["Paid", "Pending", "Delayed"],
                p=[0.78, 0.15, 0.07]
            )

            sales_records.append({
                "sale_id": f"SALE{sale_id:05d}",
                "date": date.strftime("%Y-%m-%d"),
                "store_id": store["store_id"],
                "store_name": store["store_name"],
                "region": store["region"],
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "employee_id": store["manager_id"],
                "quantity_sold": quantity_sold,
                "unit_price": unit_price,
                "discount_percent": discount_percent,
                "total_sales": round(total_sales, 2),
                "total_cost": round(total_cost, 2),
                "profit": round(profit, 2),
                "payment_status": payment_status
            })

            sale_id += 1

sales_data = pd.DataFrame(sales_records)

# Save file
sales_data.to_csv(output_path, index=False)

print(f"sales_data.csv created successfully at: {output_path}")
print(f"Total rows created: {len(sales_data)}")