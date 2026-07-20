from pydantic import BaseModel, Field


class KPIItem(BaseModel):
    """One business KPI returned by the API."""

    kpi_key: str
    kpi_name: str
    value: float
    display_value: str
    unit: str
    reference_period: str
    description: str
    calculated_at: str


class StoreTargetAchievement(BaseModel):
    """Latest target-achievement information for one store."""

    store_id: str
    store_name: str
    month: str
    monthly_sales_target: float
    total_revenue: float
    operating_profit: float
    target_achievement_percent: float
    risk_status: str


class KPIResponse(BaseModel):
    """Complete response returned by GET /api/kpis."""

    status: str = Field(default="success")
    total_kpis: int
    kpis: list[KPIItem]
    latest_store_target_achievement: list[StoreTargetAchievement]