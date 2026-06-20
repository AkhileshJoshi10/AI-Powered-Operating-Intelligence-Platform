import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timedelta

np.random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[2]

products_path = BASE_DIR / "data" / "raw" / "products_data.csv"
stores_path = BASE_DIR / "data" / "raw" / "stores_data.csv"
vendors_path = BASE_DIR / "data" / "raw" / "vendors_data.csv"
output_path = BASE_DIR / "data" / "raw" / "vendor_deliveries_data.csv"

products = pd.read_csv(products_path)
stores = pd.read_csv(stores_path)
vendors = pd.read_csv(vendors_path)

months = pd.period_range("2026-01", "2026-06", freq="M")

delivery_records = []
purchase_order_id = 1

for month in months:
    month_start = month.start_time
    month_end = month.end_time.normalize()

    for _, vendor in vendors.iterrows():
        vendor_products = products[
            products["vendor_id"] == vendor["vendor_id"]
        ]

        deliveries_this_month = np.random.randint(1, 3)

        for _ in range(deliveries_this_month):
            product = vendor_products.sample(1).iloc[0]
            store = stores.sample(1).iloc[0]

            order_day = np.random.randint(0, 15)
            order_date = month_start + timedelta(days=order_day)

            expected_delivery_date = order_date + timedelta(
                days=int(vendor["average_delivery_days"])
            )

            reorder_level = int(product["reorder_level"])

            ordered_quantity = np.random.randint(
                max(20, int(reorder_level * 1.5)),
                max(25, int(reorder_level * 4))
            )

            high_risk_vendor = (
                vendor["vendor_id"] in ["V004", "V009"]
                and month >= pd.Period("2026-04", freq="M")
            )

            if high_risk_vendor:
                delay_days = int(np.random.choice(
                    [0, 2, 5, 7, 10, 15],
                    p=[0.10, 0.10, 0.20, 0.25, 0.20, 0.15]
                ))

                quality_rating = float(np.random.choice(
                    [2.5, 3.0, 3.5, 4.0],
                    p=[0.15, 0.35, 0.35, 0.15]
                ))
            else:
                delay_days = int(np.random.choice(
                    [0, 1, 2, 3, 5],
                    p=[0.55, 0.18, 0.15, 0.08, 0.04]
                ))

                quality_rating = float(np.random.choice(
                    [3.5, 4.0, 4.5, 5.0],
                    p=[0.15, 0.35, 0.35, 0.15]
                ))

            actual_delivery_date = expected_delivery_date + timedelta(
                days=delay_days
            )

            partial_delivery = np.random.choice(
                [True, False],
                p=[0.10, 0.90]
            )

            if partial_delivery:
                received_quantity = int(
                    ordered_quantity * np.random.uniform(0.80, 0.95)
                )
            else:
                received_quantity = ordered_quantity

            if delay_days > 0 and received_quantity < ordered_quantity:
                delivery_status = "Delayed and Partial"
            elif delay_days > 0:
                delivery_status = "Delayed"
            elif received_quantity < ordered_quantity:
                delivery_status = "Partial Delivery"
            else:
                delivery_status = "Delivered On Time"

            purchase_value = round(
                ordered_quantity * float(product["cost_price"]),
                2
            )

            delivery_records.append({
                "purchase_order_id": f"PO{purchase_order_id:05d}",
                "order_date": order_date.strftime("%d-%m-%y"),
                "expected_delivery_date": expected_delivery_date.strftime("%d-%m-%y"),
                "actual_delivery_date": actual_delivery_date.strftime("%d-%m-%y"),
                "store_id": store["store_id"],
                "store_name": store["store_name"],
                "vendor_id": vendor["vendor_id"],
                "vendor_name": vendor["vendor_name"],
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "ordered_quantity": ordered_quantity,
                "received_quantity": received_quantity,
                "unit_cost": product["cost_price"],
                "purchase_value": purchase_value,
                "delay_days": delay_days,
                "delivery_status": delivery_status,
                "quality_rating": quality_rating,
                "assigned_employee_id": "E025"
            })

            purchase_order_id += 1

vendor_deliveries_data = pd.DataFrame(delivery_records)

vendor_deliveries_data.to_csv(output_path, index=False)

print(f"vendor_deliveries_data.csv created successfully at: {output_path}")
print(f"Total rows created: {len(vendor_deliveries_data)}")