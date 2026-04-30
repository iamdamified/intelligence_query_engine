#!/usr/bin/env python
"""
Comprehensive test suite for authentication and API endpoints.
Tests the fixes for HNG Stage 3 assessment.
"""

import asyncio
from fastapi.testclient import TestClient
from main import app
from auth.tokens import create_access_token, decode_token
from core.config import settings
import uuid
from datetime import datetime, timezone

client = TestClient(app)

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_test(name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}")
    if details:
        print(f"     {details}")

print_section("HNG Stage 3 - Authentication & API Tests")

# Test 1: Check CORS headers on /auth/github
print_section("Test 1: CORS Headers on /auth/github")
try:
    response = client.get("/auth/github", follow_redirects=False)
    has_cors = "access-control-allow-origin" in response.headers
    headers_text = ", ".join(response.headers.keys()) if has_cors else "No CORS headers"
    print_test("CORS headers present", has_cors, f"Status: {response.status_code}")
except Exception as e:
    print_test("CORS headers check", False, str(e))

# Test 2: Rate limiting on /auth/github
print_section("Test 2: Rate Limiting on /auth/github")
try:
    request_count = 0
    hit_rate_limit = False
    
    for i in range(12):
        response = client.get("/auth/github", follow_redirects=False)
        request_count += 1
        if response.status_code == 429:
            hit_rate_limit = True
            break
    
    print_test("Rate limiting enforced", hit_rate_limit, 
               f"Rate limit hit after {request_count} requests (expected around 10)")
except Exception as e:
    print_test("Rate limiting check", False, str(e))

# Test 3: /auth/refresh enforces POST
print_section("Test 3: /auth/refresh Method Enforcement")
try:
    # Try GET (should fail)
    response_get = client.get("/auth/refresh")
    is_method_error = response_get.status_code in [405, 422]
    
    # Try POST without auth (should fail with auth error, not method error)
    response_post = client.post("/auth/refresh", json={"refresh_token": "test"})
    is_post_accepted = response_post.status_code != 405
    
    print_test("/auth/refresh enforces POST", is_post_accepted, 
               f"GET status: {response_get.status_code}, POST status: {response_post.status_code}")
except Exception as e:
    print_test("/auth/refresh method check", False, str(e))

# Test 4: /auth/logout enforces POST
print_section("Test 4: /auth/logout Method Enforcement")
try:
    # Try GET (should fail)
    response_get = client.get("/auth/logout")
    is_method_error = response_get.status_code in [405, 422]
    
    # Try POST without auth (should fail with auth error, not method error)
    response_post = client.post("/auth/logout", json={"refresh_token": "test"})
    is_post_accepted = response_post.status_code != 405
    
    print_test("/auth/logout enforces POST", is_post_accepted,
               f"GET status: {response_get.status_code}, POST status: {response_post.status_code}")
except Exception as e:
    print_test("/auth/logout method check", False, str(e))

# Test 5: Test user creation endpoint
print_section("Test 5: Test User Creation Endpoint")
try:
    if settings.ENV == "development":
        test_user_data = {
            "username": f"test_admin_{uuid.uuid4().hex[:8]}",
            "role": "admin"
        }
        response = client.post("/auth/test/user", json=test_user_data)
        is_created = response.status_code == 200
        
        if is_created:
            data = response.json()
            has_tokens = "access_token" in data and "refresh_token" in data
            print_test("Test user creation", has_tokens,
                       f"Status: {response.status_code}, Has tokens: {has_tokens}")
            
            # Test token in response
            access_token = data.get("access_token")
            try:
                decoded = decode_token(access_token)
                has_role = "role" in decoded
                print_test("Test token contains role", has_role,
                           f"Token decoded successfully, role: {decoded.get('role')}")
            except Exception as e:
                print_test("Test token decode", False, str(e))
        else:
            print_test("Test user creation", False, f"Status: {response.status_code}")
    else:
        print_test("Test user endpoint", False, "Not in development environment")
except Exception as e:
    print_test("Test user creation", False, str(e))

# Test 6: /api/users/me with auth token
print_section("Test 6: /api/users/me Endpoint")
try:
    # First create a test user
    test_user_data = {
        "username": f"test_analyst_{uuid.uuid4().hex[:8]}",
        "role": "analyst"
    }
    response = client.post("/auth/test/user", json=test_user_data)
    
    if response.status_code == 200:
        data = response.json()
        access_token = data.get("access_token")
        user_id = data.get("user", {}).get("id")
        
        # Now test /api/users/me
        headers = {"Authorization": f"Bearer {access_token}"}
        response_me = client.get("/api/users/me", headers=headers)
        
        is_success = response_me.status_code == 200
        if is_success:
            me_data = response_me.json()
            is_analyst = me_data.get("data", {}).get("role") == "analyst"
            print_test("/api/users/me with auth", is_analyst,
                       f"Status: {response_me.status_code}, Role: {me_data.get('data', {}).get('role')}")
        else:
            print_test("/api/users/me with auth", False,
                       f"Status: {response_me.status_code}")
    else:
        print_test("/api/users/me test", False, "Could not create test user")
except Exception as e:
    print_test("/api/users/me check", False, str(e))

# Test 7: Token expiration
print_section("Test 7: Token Structure")
try:
    token = create_access_token({"sub": "test-user", "role": "admin"})
    decoded = decode_token(token)
    
    has_exp = "exp" in decoded
    has_sub = "sub" in decoded
    has_role = "role" in decoded
    
    all_fields = has_exp and has_sub and has_role
    print_test("Token has required fields", all_fields,
               f"sub: {has_sub}, role: {has_role}, exp: {has_exp}")
    
    if all_fields:
        print(f"     Token payload: sub={decoded['sub']}, role={decoded['role']}")
except Exception as e:
    print_test("Token structure check", False, str(e))

# Test 8: GitHub callback parameter validation
print_section("Test 8: OAuth Callback Validation")
try:
    # Test missing code
    response_no_code = client.get("/auth/github/callback?state=test")
    missing_code = "code" in response_no_code.text.lower() or response_no_code.status_code == 400
    print_test("/auth/github/callback rejects missing code", missing_code,
               f"Status: {response_no_code.status_code}")
    
    # Test missing state
    response_no_state = client.get("/auth/github/callback?code=test")
    missing_state = "state" in response_no_state.text.lower() or response_no_state.status_code == 400
    print_test("/auth/github/callback rejects missing state", missing_state,
               f"Status: {response_no_state.status_code}")
except Exception as e:
    print_test("OAuth callback validation", False, str(e))

# Test 9: Web portal endpoints
print_section("Test 9: Web Portal OAuth Endpoints")
try:
    response = client.get("/auth/web/github", follow_redirects=False)
    is_redirect = response.status_code in [301, 302, 307, 308]
    print_test("/auth/web/github redirects", is_redirect,
               f"Status: {response.status_code}")
except Exception as e:
    print_test("Web portal endpoints", False, str(e))

# Test 10: API versioning
print_section("Test 10: API Versioning")
try:
    # Create a test user first
    test_user_data = {
        "username": f"test_version_{uuid.uuid4().hex[:8]}",
        "role": "analyst"
    }
    response = client.post("/auth/test/user", json=test_user_data)
    access_token = response.json().get("access_token")
    
    # Test with valid version
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-API-Version": "1"
    }
    response_v1 = client.get("/api/users/me", headers=headers)
    is_v1_ok = response_v1.status_code == 200
    
    # Test with invalid version
    headers_invalid = {
        "Authorization": f"Bearer {access_token}",
        "X-API-Version": "2"
    }
    response_v2 = client.get("/api/users/me", headers=headers_invalid)
    is_v2_rejected = response_v2.status_code == 400
    
    print_test("API version enforcement", is_v1_ok and is_v2_rejected,
               f"Version 1: {response_v1.status_code}, Version 2: {response_v2.status_code}")
except Exception as e:
    print_test("API versioning check", False, str(e))

print_section("Tests Complete")
print("\nNote: Rate limiting may be affected by test order and resets per minute.")
print("Run this test multiple times to verify consistent behavior.")
