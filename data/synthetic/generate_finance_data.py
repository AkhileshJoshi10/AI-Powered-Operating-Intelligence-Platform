import pandas as pd
import numpy as np
from pathlib import Path

np.random.seed(42)

BASE_DIR = Path(__file__).resolve().parents[2]

sales_path = BASE_DIR / "data" / "raw" / "sales_data.csv"
stores_path = BASE_DIR / "data" / "raw" / "stores_data.csv"
output_path = BASE_DIR / "data" / "raw" / "finance_data.csv"

sales = pd.read_csv(sales_path)
stores = pd.read_csv(stores_path)

# Your sales file uses dates such as 01-01-26
sales["date"] = pd.to_datetime(sales["date"], format="%d-%m-%y")
sales["month"] = sales["date"].dt.to_period("M").astype(str)

# Monthly financial performance for each store
monthly_finance = sales.groupby(
    ["month", "store_id", "store_name", "region"]
).agg(
    total_revenue=("total_sales", "sum"),
    total_cost=("total_cost", "sum"),
    gross_profit=("profit", "sum")
).reset_index()

finance_records = []
finance_id = 1

for _, row in monthly_finance.iterrows():

    store_info = stores[
        stores["store_id"] == row["store_id"]
    ].iloc[0]

    monthly_sales_target = store_info["monthly_sales_target"]

    total_revenue = round(row["total_revenue"], 2)
    total_cost = round(row["total_cost"], 2)
    gross_profit = round(row["gross_profit"], 2)

    # Simplified operating expense for retail/FMCG demo
    # Expense is based on actual revenue, not target.
    operating_expense = round(
        total_revenue * np.random.uniform(0.06, 0.12),
        2
    )

    # This is operating profit, not final net profit.
    operating_profit = round(
        gross_profit - operating_expense,
        2
    )

    target_achievement_percent = round(
        (total_revenue / monthly_sales_target) * 100,
        2
    )

    # Financial risk based on store performance and profitability
    if operating_profit < 0 or target_achievement_percent < 70:
        risk_status = "High Risk"
    elif target_achievement_percent < 90:
        risk_status = "Medium Risk"
    else:
        risk_status = "Low Risk"

    finance_records.append({
        "finance_id": f"FIN{finance_id:05d}",
        "month": row["month"],
        "store_id": row["store_id"],
        "store_name": row["store_name"],
        "region": row["region"],
        "monthly_sales_target": monthly_sales_target,
        "total_revenue": total_revenue,
        "total_cost": total_cost,
        "gross_profit": gross_profit,
        "operating_expense": operating_expense,
        "operating_profit": operating_profit,
        "target_achievement_percent": target_achievement_percent,
        "risk_status": risk_status
    })

    finance_id += 1

finance_data = pd.DataFrame(finance_records)

finance_data.to_csv(output_path, index=False)

print(f"finance_data.csv created successfully at: {output_path}")
print(f"Total rows created: {len(finance_data)}")