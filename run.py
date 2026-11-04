"""
Convenience launcher for NegotiAgent AI FastAPI Server.
Run via: python run.py
"""

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print("=" * 60)
    print(" Starting NegotiAgent AI (FastAPI Backend)")
    print(f" App Interface: http://127.0.0.1:{port}")
    print(f" Interactive Swagger API Docs: http://127.0.0.1:{port}/docs")
    print("=" * 60)
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)