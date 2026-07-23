from fastapi import FastAPI

from backend.app.core.config import settings
from backend.app.routers.analytics import (
    router as analytics_router,
)
from backend.app.routers.data_management import (
    router as data_management_router,
)
from backend.app.routers.health import (
    router as health_router,
)
from backend.app.routers.issues import (
    router as issue_router,
)
from backend.app.routers.kpis import (
    router as kpi_router,
)
from backend.app.routers.recommendations import (
    router as recommendation_router,
)
from backend.app.routers.tasks import (
    router as task_router,
)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for business KPIs, analytics, issues, "
        "root-cause analyses, recommendations, tasks, "
        "data management, executive briefs, and automation workflows."
    ),
)


app.include_router(health_router)
app.include_router(kpi_router)
app.include_router(issue_router)
app.include_router(recommendation_router)
app.include_router(task_router)
app.include_router(analytics_router)
app.include_router(data_management_router)