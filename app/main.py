"""
NegotiAgent AI - FastAPI Application Entry Point
Sponsored by Shri Mahalaxmi Marbles & Granites, Mudhal Titta, Kolhapur (Owner: Mr. Vikram Gurav)
Developed by CSE (AI & ML) Students, DYPCET Kolhapur
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
from dotenv import load_dotenv

from app.database.seed import seed_database
from app.routes.rfq_routes import router as rfq_router
from app.routes.supplier_routes import router as supplier_router
from app.routes.negotiation_routes import router as negotiation_router
from app.routes.order_routes import router as order_router
from app.routes.report_routes import router as report_router

load_dotenv()

seed_database()

app = FastAPI(
    title="NegotiAgent AI API",
    description="Autonomous Multi-Agent Procurement Negotiation System (Sponsored by Shri Mahalaxmi Marbles & Granites, Mudhal Titta, Kolhapur)",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rfq_router)
app.include_router(supplier_router)
app.include_router(negotiation_router)
app.include_router(order_router)
app.include_router(report_router)

@app.get("/api/health", tags=["System"])
def health_check():
    return {
        "status": "online",
        "system": "NegotiAgent AI",
        "backend": "FastAPI (Python 3.10+)",
        "database": "SQLite (negotiagent.db)",
        "sponsor": "Shri Mahalaxmi Marbles & Granites, Mudhal Titta, Kolhapur",
        "owner": "Mr. Vikram Gurav",
        "institution": "DYPCET Kolhapur (CSE - AI & ML)",
        "team": [
            "Rushikesh S. Powar",
            "Rohit A. Mengane",
            "Ganesh G. Kumbhar",
            "Pawan R. Payghan"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")