"""
Main FastAPI Application Entrypoint
Serves static frontend assets, API routes, and handles gateway redirects.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database.session import engine
from app.database.models import Base
from app.database.seed import seed_database
from app.routes.rfq_routes import router as rfq_router
from app.routes.supplier_routes import router as supplier_router
from app.routes.negotiation_routes import router as negotiation_router
from app.routes.order_routes import router as order_router
from app.routes.report_routes import router as report_router

# Initialize SQLite database tables
Base.metadata.create_all(bind=engine)
seed_database()

app = FastAPI(
    title="NegotiAgent AI - Procurement System",
    description="Multi-Agent Tiles & Granite Autonomous Procurement Negotiation Prototype",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(rfq_router)
app.include_router(supplier_router)
app.include_router(negotiation_router)
app.include_router(order_router)
app.include_router(report_router)

# Mount public directory for HTML/CSS/JS frontend
public_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
if os.path.exists(public_path):
    css_dir = os.path.join(public_path, "css")
    js_dir = os.path.join(public_path, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")
    app.mount("/public", StaticFiles(directory=public_path), name="public")


@app.get("/", include_in_schema=False)
def root():
    """Redirect initial visitors directly to the unified login and supplier gateway."""
    return RedirectResponse(url="/login.html")


@app.get("/login.html", include_in_schema=False)
def get_login_page():
    return FileResponse(os.path.join(public_path, "login.html"))


@app.get("/index.html", include_in_schema=False)
def get_dashboard_page():
    return FileResponse(os.path.join(public_path, "index.html"))


@app.get("/supplier_dashboard.html", include_in_schema=False)
def get_supplier_dashboard_page():
    return FileResponse(os.path.join(public_path, "supplier_dashboard.html"))


@app.get("/sw.js", include_in_schema=False)
def get_service_worker():
    return FileResponse(
        os.path.join(public_path, "sw.js"),
        media_type="application/javascript"
    )


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "NegotiAgent AI", "environment": "live"}