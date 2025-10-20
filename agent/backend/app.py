#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI backend for Geo OD analysis

Refactored structure:
- models.py: Pydantic models
- database.py: Database connections
- analysis.py: Analysis functions
- utils.py: Utility functions
- routes/: API endpoints
"""

import os
from fastapi import FastAPI
from database import DB_PATH, T_PLACES, T_REL, T_DYNA
from routes import api_router

# Create FastAPI app
app = FastAPI(
    title="Geo OD API",
    version="2.0.0",
    description="人员流动分析 API - 重构版"
)

# Include all routes
app.include_router(api_router)


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "ok": True,
        "version": "2.0.0",
        "db": os.path.abspath(DB_PATH),
        "tables": {
            "places": T_PLACES,
            "relations": T_REL,
            "dyna": T_DYNA
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

