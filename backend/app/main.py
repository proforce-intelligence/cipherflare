from app.api.routes import jobs, alerts, stats, monitoring, models
from app.api.routes import files


# Register routers
app.include_router(jobs.router)
app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(monitoring.router)
app.include_router(models.router)
app.include_router(files.router)
