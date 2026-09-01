from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from backend.app.schemas.complaint_analytics import (
    ComplaintAnalyticsResponse,
)
from backend.app.schemas.inventory_analytics import (
    InventoryAnalyticsResponse,
)
from backend.app.schemas.kpis import KPIResponse
from backend.app.schemas.sales_analytics import (
    SalesAnalyticsResponse,
)
from backend.app.schemas.vendor_finance_analytics import (
    FinanceAnalyticsResponse,
    VendorAnalyticsResponse,
)
from backend.app.services.complaint_analytics_service import (
    get_complaint_analytics,
)
from backend.app.services.inventory_analytics_service import (
    get_inventory_analytics,
)
from backend.app.services.kpi_service import (
    get_kpi_response,
)
from backend.app.services.sales_analytics_service import (
    get_sales_analytics,
)
from backend.app.services.vendor_finance_analytics_service import (
    get_finance_analytics,
    get_vendor_analytics,
)
from backend.app.tools.tool_models import (
    ToolAccessMode,
    ToolDefinition,
    ToolExecutionContext,
)
from backend.app.tools.tool_registry import (
    ToolRegistry,
)


GET_KPI_SNAPSHOT_TOOL_NAME = "get_kpi_snapshot"
GET_SALES_ANALYTICS_TOOL_NAME = "get_sales_analytics"
GET_INVENTORY_ANALYTICS_TOOL_NAME = "get_inventory_analytics"
GET_COMPLAINT_ANALYTICS_TOOL_NAME = "get_complaint_analytics"
GET_VENDOR_ANALYTICS_TOOL_NAME = "get_vendor_analytics"
GET_FINANCE_ANALYTICS_TOOL_NAME = "get_finance_analytics"


READ_ONLY_ANALYTICS_TOOL_NAMES = (
    GET_KPI_SNAPSHOT_TOOL_NAME,
    GET_SALES_ANALYTICS_TOOL_NAME,
    GET_INVENTORY_ANALYTICS_TOOL_NAME,
    GET_COMPLAINT_ANALYTICS_TOOL_NAME,
    GET_VENDOR_ANALYTICS_TOOL_NAME,
    GET_FINANCE_ANALYTICS_TOOL_NAME,
)


Severity = Literal[
    "High",
    "Medium",
    "Low",
]


class KPIAnalyticsInput(BaseModel):
    """KPI snapshot requires no caller-supplied parameters."""

    model_config = ConfigDict(
        extra="forbid",
    )


class AnalyticsPaginationInput(BaseModel):
    """Common bounded pagination for analytics tools."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    severity: Severity | None = None
    analysis_type: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=20,
    )
    offset: int = Field(
        default=0,
        ge=0,
        le=10000,
    )


class SalesAnalyticsInput(
    AnalyticsPaginationInput
):
    """Controlled sales-analytics filters."""


class InventoryAnalyticsInput(
    AnalyticsPaginationInput
):
    """Controlled inventory-analytics filters."""

    store_id: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
    )
    product_id: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
    )
    vendor_id: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
    )


class ComplaintAnalyticsInput(
    AnalyticsPaginationInput
):
    """Controlled complaint-analytics filters."""

    store_id: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
    )
    product_id: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
    )
    region: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    complaint_type: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    complaint_status: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )


class VendorAnalyticsInput(
    AnalyticsPaginationInput
):
    """Controlled vendor-analytics filters."""

    vendor_id: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
    )


class FinanceAnalyticsInput(
    AnalyticsPaginationInput
):
    """Controlled finance-analytics filters."""

    store_id: str | None = Field(
        default=None,
        min_length=2,
        max_length=20,
    )
    month: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$",
    )
    risk_status: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
    )


async def get_kpi_snapshot_handler(
    arguments: KPIAnalyticsInput,
    context: ToolExecutionContext,
) -> KPIResponse:
    """Return the current deterministic KPI snapshot."""

    del arguments
    del context

    return KPIResponse.model_validate(
        get_kpi_response()
    )


async def get_sales_analytics_handler(
    arguments: SalesAnalyticsInput,
    context: ToolExecutionContext,
) -> SalesAnalyticsResponse:
    """Run existing deterministic sales analytics with bounded filters."""

    del context

    return SalesAnalyticsResponse.model_validate(
        get_sales_analytics(
            severity=arguments.severity,
            analysis_type=arguments.analysis_type,
            limit=arguments.limit,
            offset=arguments.offset,
        )
    )


async def get_inventory_analytics_handler(
    arguments: InventoryAnalyticsInput,
    context: ToolExecutionContext,
) -> InventoryAnalyticsResponse:
    """Run existing deterministic inventory analytics."""

    del context

    return InventoryAnalyticsResponse.model_validate(
        get_inventory_analytics(
            severity=arguments.severity,
            analysis_type=arguments.analysis_type,
            store_id=arguments.store_id,
            product_id=arguments.product_id,
            vendor_id=arguments.vendor_id,
            limit=arguments.limit,
            offset=arguments.offset,
        )
    )


async def get_complaint_analytics_handler(
    arguments: ComplaintAnalyticsInput,
    context: ToolExecutionContext,
) -> ComplaintAnalyticsResponse:
    """Run existing deterministic complaint analytics."""

    del context

    return ComplaintAnalyticsResponse.model_validate(
        get_complaint_analytics(
            severity=arguments.severity,
            analysis_type=arguments.analysis_type,
            store_id=arguments.store_id,
            product_id=arguments.product_id,
            region=arguments.region,
            complaint_type=arguments.complaint_type,
            complaint_status=arguments.complaint_status,
            limit=arguments.limit,
            offset=arguments.offset,
        )
    )


async def get_vendor_analytics_handler(
    arguments: VendorAnalyticsInput,
    context: ToolExecutionContext,
) -> VendorAnalyticsResponse:
    """Run existing deterministic vendor analytics."""

    del context

    return VendorAnalyticsResponse.model_validate(
        get_vendor_analytics(
            severity=arguments.severity,
            analysis_type=arguments.analysis_type,
            vendor_id=arguments.vendor_id,
            limit=arguments.limit,
            offset=arguments.offset,
        )
    )


async def get_finance_analytics_handler(
    arguments: FinanceAnalyticsInput,
    context: ToolExecutionContext,
) -> FinanceAnalyticsResponse:
    """Run existing deterministic finance analytics."""

    del context

    return FinanceAnalyticsResponse.model_validate(
        get_finance_analytics(
            severity=arguments.severity,
            analysis_type=arguments.analysis_type,
            store_id=arguments.store_id,
            month=arguments.month,
            risk_status=arguments.risk_status,
            limit=arguments.limit,
            offset=arguments.offset,
        )
    )


def build_read_only_analytics_tool_definitions(
) -> list[ToolDefinition]:
    """Build bounded deterministic analytics tools."""

    monitoring_and_root_cause = (
        "Monitoring Agent",
        "Root-Cause Agent",
    )

    return [
        ToolDefinition(
            name=GET_KPI_SNAPSHOT_TOOL_NAME,
            description=(
                "Read the current deterministic KPI snapshot."
            ),
            input_model=KPIAnalyticsInput,
            output_model=KPIResponse,
            handler=get_kpi_snapshot_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=(
                "Monitoring Agent",
                "Priority Agent",
                "Executive Brief Agent",
            ),
        ),
        ToolDefinition(
            name=GET_SALES_ANALYTICS_TOOL_NAME,
            description=(
                "Run existing deterministic sales analytics "
                "using bounded filters."
            ),
            input_model=SalesAnalyticsInput,
            output_model=SalesAnalyticsResponse,
            handler=get_sales_analytics_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=monitoring_and_root_cause,
        ),
        ToolDefinition(
            name=GET_INVENTORY_ANALYTICS_TOOL_NAME,
            description=(
                "Run existing deterministic inventory analytics "
                "using bounded filters."
            ),
            input_model=InventoryAnalyticsInput,
            output_model=InventoryAnalyticsResponse,
            handler=get_inventory_analytics_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=monitoring_and_root_cause,
        ),
        ToolDefinition(
            name=GET_COMPLAINT_ANALYTICS_TOOL_NAME,
            description=(
                "Run existing deterministic complaint analytics "
                "using bounded filters."
            ),
            input_model=ComplaintAnalyticsInput,
            output_model=ComplaintAnalyticsResponse,
            handler=get_complaint_analytics_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=monitoring_and_root_cause,
        ),
        ToolDefinition(
            name=GET_VENDOR_ANALYTICS_TOOL_NAME,
            description=(
                "Run existing deterministic vendor analytics "
                "using bounded filters."
            ),
            input_model=VendorAnalyticsInput,
            output_model=VendorAnalyticsResponse,
            handler=get_vendor_analytics_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=monitoring_and_root_cause,
        ),
        ToolDefinition(
            name=GET_FINANCE_ANALYTICS_TOOL_NAME,
            description=(
                "Run existing deterministic finance analytics "
                "using bounded filters."
            ),
            input_model=FinanceAnalyticsInput,
            output_model=FinanceAnalyticsResponse,
            handler=get_finance_analytics_handler,
            access_mode=ToolAccessMode.READ_ONLY,
            allowed_agents=monitoring_and_root_cause,
        ),
    ]


def register_read_only_analytics_tools(
    registry: ToolRegistry,
) -> None:
    """Register the bounded deterministic analytics tool set."""

    for definition in (
        build_read_only_analytics_tool_definitions()
    ):
        registry.register(
            definition
        )
