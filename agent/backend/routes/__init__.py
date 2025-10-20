#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Routes
"""

from fastapi import APIRouter
from . import geo, od, relations, analysis, metrics

# Create main router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(geo.router, tags=["Geo"])
api_router.include_router(relations.router, tags=["Relations"])
api_router.include_router(od.router, tags=["OD"])
api_router.include_router(metrics.router, tags=["Metrics"])
api_router.include_router(analysis.router, tags=["Analysis"])

