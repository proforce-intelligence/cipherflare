from app.api.routes import jobs, alerts, stats, monitoring, models, auth, report
from app.api.routes import files


# Register routers
app.include_router(jobs.router)
app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(monitoring.router)
app.include_router(models.router)
app.include_router(files.router)
app.include_router(auth.router)
app.include_router(report.router)
