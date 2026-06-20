import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

np.random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[2]

products_path = BASE_DIR / "data" / "raw" / "products_data.csv"
stores_path = BASE_DIR / "data" / "raw" / "stores_data.csv"
employees_path = BASE_DIR / "data" / "raw" / "employees_data.csv"
output_path = BASE_DIR / "data" / "raw" / "complaints_data.csv"

products = pd.read_csv(products_path)
stores = pd.read_csv(stores_path)
employees = pd.read_csv(employees_path)

start_date = datetime(2026, 1, 1)
end_date = datetime(2026, 6, 30)
dates = pd.date_range(start_date, end_date)

complaint_types = [
    "Product Quality Issue",
    "Late Delivery",
    "Wrong Billing",
    "Damaged Packaging",
    "Out of Stock",
    "Staff Behavior",
    "Return or Refund Issue"
]

complaint_descriptions = {
    "Product Quality Issue": [
        "Customer reported that the product quality was below expectation.",
        "Customer complained that the product appeared damaged or defective.",
        "Customer said the product did not meet the promised quality standard."
    ],
    "Late Delivery": [
        "Customer reported that the order was delivered later than the expected time.",
        "Customer complained about delay in delivery despite confirmed order timing.",
        "Customer said the delayed delivery affected their purchase experience."
    ],
    "Wrong Billing": [
        "Customer reported that the bill amount was incorrect.",
        "Customer complained that discount was not applied in the final bill.",
        "Customer reported duplicate or incorrect charges in the invoice."
    ],
    "Damaged Packaging": [
        "Customer received the product with torn or damaged packaging.",
        "Customer complained that the packaging was leaking or not properly sealed.",
        "Customer reported that the outer packaging was damaged at the time of purchase."
    ],
    "Out of Stock": [
        "Customer could not purchase the required product because it was unavailable.",
        "Customer reported repeated stock unavailability for the same product.",
        "Customer complained that the product was shown available but was not present in store."
    ],
    "Staff Behavior": [
        "Customer reported slow response from store staff.",
        "Customer complained about rude or unhelpful staff behavior.",
        "Customer said staff assistance was delayed during the purchase."
    ],
    "Return or Refund Issue": [
        "Customer faced delay in return or replacement process.",
        "Customer complained that refund was not processed on time.",
        "Customer reported difficulty in getting support for return or refund."
    ]
}

support_employees = employees[employees["department"] == "Customer Support"]

complaint_records = []
complaint_id = 1

for date in dates:
    for _, store in stores.iterrows():

        # Normal complaint pattern
        daily_complaints = np.random.choice(
            [0, 1, 2, 3],
            p=[0.45, 0.35, 0.15, 0.05]
        )

        # Intentional business issue:
        # Store S003 gets higher complaints in June
        if store["store_id"] == "S003" and date.month == 6:
            daily_complaints += np.random.randint(3, 7)

        for _ in range(daily_complaints):

            # Intentional product-level complaint issue in S003 during June
            if store["store_id"] == "S003" and date.month == 6:
                product = products[
                    products["product_id"].isin(["P017", "P018", "P019"])
                ].sample(1).iloc[0]

                complaint_type = np.random.choice(
                    ["Product Quality Issue", "Out of Stock", "Late Delivery"],
                    p=[0.45, 0.35, 0.20]
                )

                severity = np.random.choice(
                    ["Medium", "High"],
                    p=[0.45, 0.55]
                )

            else:
                product = products.sample(1).iloc[0]

                complaint_type = np.random.choice(complaint_types)

                severity = np.random.choice(
                    ["Low", "Medium", "High"],
                    p=[0.50, 0.35, 0.15]
                )

            # Realistic status logic based on complaint age
            days_old = (end_date - date).days

            if days_old > 60:
                status = np.random.choice(
                    ["Resolved", "In Progress", "Open"],
                    p=[0.90, 0.07, 0.03]
                )
            elif days_old > 30:
                status = np.random.choice(
                    ["Resolved", "In Progress", "Open"],
                    p=[0.80, 0.15, 0.05]
                )
            elif days_old > 7:
                status = np.random.choice(
                    ["Resolved", "In Progress", "Open"],
                    p=[0.60, 0.25, 0.15]
                )
            else:
                status = np.random.choice(
                    ["Resolved", "In Progress", "Open"],
                    p=[0.30, 0.35, 0.35]
                )

            if status == "Resolved":
                max_resolution_days = min(10, max(1, days_old))
                resolution_time_days = np.random.randint(1, max_resolution_days + 1)
            else:
                resolution_time_days = "NA"

            assigned_employee = support_employees.sample(1).iloc[0]

            complaint_records.append({
                "complaint_id": f"COMP{complaint_id:05d}",
                "date": date.strftime("%Y-%m-%d"),
                "customer_id": f"CUST{np.random.randint(1, 801):04d}",
                "store_id": store["store_id"],
                "store_name": store["store_name"],
                "region": store["region"],
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "category": product["category"],
                "complaint_type": complaint_type,
                "complaint_description": np.random.choice(
                    complaint_descriptions[complaint_type]
                ),
                "severity": severity,
                "status": status,
                "assigned_employee_id": assigned_employee["employee_id"],
                "resolution_time_days": resolution_time_days
            })

            complaint_id += 1

complaints_data = pd.DataFrame(complaint_records)

complaints_data.to_csv(output_path, index=False)

print(f"complaints_data.csv created successfully at: {output_path}")
print(f"Total rows created: {len(complaints_data)}")