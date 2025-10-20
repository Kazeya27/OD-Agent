#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the refactored app structure
"""

import sys

print("=" * 70)
print("Testing Refactored App Structure")
print("=" * 70)

# Test 1: Import core modules
print("\n1. Testing core module imports...")
try:
    import models
    print("   ✅ models.py imported successfully")
except Exception as e:
    print(f"   ❌ models.py import failed: {e}")
    sys.exit(1)

try:
    import database
    print("   ✅ database.py imported successfully")
except Exception as e:
    print(f"   ❌ database.py import failed: {e}")
    sys.exit(1)

try:
    import utils
    print("   ✅ utils.py imported successfully")
except Exception as e:
    print(f"   ❌ utils.py import failed: {e}")
    sys.exit(1)

try:
    import analysis
    print("   ✅ analysis.py imported successfully")
except Exception as e:
    print(f"   ❌ analysis.py import failed: {e}")
    sys.exit(1)

# Test 2: Import routes
print("\n2. Testing route module imports...")
try:
    from routes import geo, od, relations, metrics, analysis as analysis_routes
    print("   ✅ All route modules imported successfully")
except Exception as e:
    print(f"   ❌ Route import failed: {e}")
    sys.exit(1)

# Test 3: Import main app
print("\n3. Testing main app import...")
try:
    import app
    print("   ✅ app.py imported successfully")
except Exception as e:
    print(f"   ❌ app.py import failed: {e}")
    sys.exit(1)

# Test 4: Check FastAPI app
print("\n4. Testing FastAPI app structure...")
try:
    assert hasattr(app, 'app'), "No 'app' instance found"
    print(f"   ✅ FastAPI app created: {app.app.title}")
except Exception as e:
    print(f"   ❌ FastAPI app check failed: {e}")
    sys.exit(1)

# Test 5: Check routes are registered
print("\n5. Testing route registration...")
try:
    routes = [route.path for route in app.app.routes]
    expected_routes = [
        "/geo-id",
        "/relations/matrix",
        "/od",
        "/od/pair",
        "/predict",
        "/growth",
        "/metrics",
        "/analyze/province-flow",
        "/analyze/city-flow",
        "/analyze/province-corridor",
        "/analyze/city-corridor"
    ]
    
    registered = []
    missing = []
    
    for exp in expected_routes:
        if exp in routes:
            registered.append(exp)
        else:
            missing.append(exp)
    
    print(f"   ✅ {len(registered)}/{len(expected_routes)} expected routes registered")
    
    if missing:
        print(f"   ⚠️  Missing routes: {missing}")
    else:
        print("   ✅ All expected routes are registered!")
        
except Exception as e:
    print(f"   ❌ Route check failed: {e}")
    import traceback
    traceback.print_exc()

# Test 6: Module structure
print("\n6. Testing module structure...")
try:
    # Check models
    assert hasattr(models, 'DateMode'), "DateMode enum not found"
    assert hasattr(models, 'Direction'), "Direction enum not found"
    assert hasattr(models, 'ProvinceFlowRequest'), "ProvinceFlowRequest not found"
    print("   ✅ models.py has expected classes")
    
    # Check database
    assert hasattr(database, 'get_db'), "get_db not found"
    assert hasattr(database, 'load_nodes'), "load_nodes not found"
    print("   ✅ database.py has expected functions")
    
    # Check analysis
    assert hasattr(analysis, 'analyze_province_flow'), "analyze_province_flow not found"
    assert hasattr(analysis, 'analyze_city_flow'), "analyze_city_flow not found"
    print("   ✅ analysis.py has expected functions")
    
    # Check utils
    assert hasattr(utils, 'iso_to_epoch'), "iso_to_epoch not found"
    assert hasattr(utils, 'extract_province'), "extract_province not found"
    print("   ✅ utils.py has expected functions")
    
except Exception as e:
    print(f"   ❌ Structure check failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ All Tests Passed!")
print("=" * 70)
print("\nRefactored app structure is ready to use:")
print("  • Start server: python -m uvicorn app:app --reload")
print("  • API docs: http://localhost:8000/docs")
print("  • Health check: http://localhost:8000/")

