import asyncio
import aiohttp
import time
import json
import sys

NODE_URL = "http://localhost:3000"
PYTHON_URL = "http://localhost:8000"

results = {
    "api_tests": [],
    "security_tests": [],
    "performance": [],
    "mcp": []
}

def log_pass(category, name, details=""):
    results[category].append({"name": name, "status": "PASS", "details": details})
    print(f"PASS: {name}")

def log_fail(category, name, expected, actual, severity="Major", details=""):
    results[category].append({"name": name, "status": "FAIL", "expected": expected, "actual": actual, "severity": severity, "details": details})
    print(f"FAIL: {name} (Severity: {severity})")

async def test_api_news(session):
    name = "GET /api/news (Node)"
    try:
        async with session.get(f"{NODE_URL}/api/news") as resp:
            data = await resp.json()
            if "items" in data:
                log_pass("api_tests", name)
            else:
                log_fail("api_tests", name, "JSON with 'items'", str(data)[:100])
    except Exception as e:
        log_fail("api_tests", name, "Success", str(e))

async def test_api_fact_check_local(session):
    name = "POST /api/fact-check local fallback"
    try:
        async with session.post(f"{NODE_URL}/api/fact-check", json={"title": "Test Headline", "source": "BBC"}) as resp:
            data = await resp.json()
            if "score" in data and "verdict" in data:
                log_pass("api_tests", name)
            else:
                log_fail("api_tests", name, "JSON with score and verdict", str(data)[:100])
    except Exception as e:
        log_fail("api_tests", name, "Success", str(e))

async def test_empty_body(session):
    name = "POST /api/fact-check empty body"
    try:
        async with session.post(f"{NODE_URL}/api/fact-check", json={}) as resp:
            if resp.status == 400:
                log_pass("api_tests", name)
            else:
                log_fail("api_tests", name, "400 status", f"Status {resp.status}", "Minor")
    except Exception as e:
        log_fail("api_tests", name, "400 status", str(e))

async def test_huge_payload(session):
    name = "POST /api/fact-check huge payload"
    huge_string = "A" * 15000
    try:
        async with session.post(f"{NODE_URL}/api/fact-check", json={"title": huge_string}) as resp:
            if resp.status in [400, 413]:
                log_pass("security_tests", name)
            else:
                log_fail("security_tests", name, "400 or 413 status", f"Status {resp.status}", "Major", "Payload not rejected by length limits")
    except Exception as e:
        log_fail("security_tests", name, "Rejected", str(e))

async def test_missing_chat_msg(session):
    name = "POST /api/chat missing msg"
    try:
        async with session.post(f"{NODE_URL}/api/chat", json={}) as resp:
            if resp.status == 400:
                log_pass("api_tests", name)
            else:
                log_fail("api_tests", name, "400 status", f"Status {resp.status}")
    except Exception as e:
        log_fail("api_tests", name, "400 status", str(e))

async def test_python_health(session):
    name = "GET /api/health (Python)"
    try:
        async with session.get(f"{PYTHON_URL}/api/health") as resp:
            if resp.status == 200:
                log_pass("api_tests", name)
            else:
                log_fail("api_tests", name, "200 status", f"Status {resp.status}")
    except Exception as e:
        log_fail("api_tests", name, "200 status", str(e))

async def test_cors(session):
    name = "CORS Headers (Python)"
    try:
        async with session.options(f"{PYTHON_URL}/api/fact-check", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"}) as resp:
            if resp.headers.get("Access-Control-Allow-Origin"):
                log_pass("api_tests", name)
            else:
                log_fail("api_tests", name, "Access-Control-Allow-Origin present", "Missing", "Major")
    except Exception as e:
        log_fail("api_tests", name, "Headers present", str(e))

async def test_malformed_json(session):
    name = "POST /api/fact-check Malformed JSON (Python)"
    try:
        async with session.post(f"{PYTHON_URL}/api/fact-check", data="invalid json", headers={"Content-Type": "application/json"}) as resp:
            if resp.status in [400, 422]:
                log_pass("api_tests", name)
            else:
                log_fail("api_tests", name, "422 or 400 status", f"Status {resp.status}", "Major")
    except Exception as e:
        log_fail("api_tests", name, "Error status", str(e))

async def test_xss_injection(session):
    name = "XSS Payload"
    payload = "<script>alert('xss')</script>Breaking news today"
    try:
        async with session.post(f"{NODE_URL}/api/fact-check", json={"title": payload}) as resp:
            data = await resp.json()
            # If server crashes it's a fail, but we also check if input is echoed unescaped
            if "<script>" in str(data):
                log_fail("security_tests", name, "Escaped output", "Unescaped script tags", "Critical")
            else:
                log_pass("security_tests", name)
    except Exception as e:
        log_fail("security_tests", name, "Handled safely", str(e))

async def test_sql_injection(session):
    name = "SQL Injection Payload"
    payload = "'; DROP TABLE facts; -- major discovery today"
    try:
        async with session.post(f"{NODE_URL}/api/fact-check", json={"title": payload}) as resp:
            if resp.status == 200:
                log_pass("security_tests", name)
            else:
                log_fail("security_tests", name, "200 status (safe handle)", f"Status {resp.status}", "Major")
    except Exception as e:
        log_fail("security_tests", name, "Handled safely", str(e))

async def test_rate_limiting(session):
    name = "Rate Limiting"
    try:
        resps = await asyncio.gather(*[session.post(f"{NODE_URL}/api/fact-check", json={"title": "Test"}) for _ in range(15)])
        statuses = [r.status for r in resps]
        if 429 in statuses:
            log_pass("security_tests", name)
        else:
            log_fail("security_tests", name, "At least one 429 status", "All requests passed", "Minor", "Rate limiting not enforced")
    except Exception as e:
        log_fail("security_tests", name, "Graceful rate limit", str(e))

async def test_mcp_source(session):
    name = "MCP Source Analysis"
    try:
        async with session.get(f"{NODE_URL}/api/source/bbc") as resp:
            data = await resp.json()
            if data.get("found") and "Tier 1" in data.get("tier", ""):
                log_pass("mcp", name)
            else:
                log_fail("mcp", name, "Tier 1 found", str(data))
    except Exception as e:
        log_fail("mcp", name, "Success", str(e))

async def test_performance_simultaneous(session):
    name = "Performance: 3 Simultaneous Requests"
    start = time.time()
    try:
        resps = await asyncio.gather(*[session.post(f"{NODE_URL}/api/verify", json={"title": "Is climate change real?"}) for _ in range(3)])
        durations = []
        all_ok = True
        for r in resps:
            # Consume stream to end
            text = await r.text()
            if r.status != 200 or "[DONE]" not in text:
                all_ok = False
        duration = time.time() - start
        if all_ok and duration < 30: # Within reasonable time
            log_pass("performance", name, f"Duration: {duration:.2f}s")
        else:
            log_fail("performance", name, "All streams complete successfully", f"Success={all_ok}, Duration={duration:.2f}s")
    except Exception as e:
        log_fail("performance", name, "Complete successfully", str(e))

async def main():
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            test_api_news(session),
            test_api_fact_check_local(session),
            test_empty_body(session),
            test_huge_payload(session),
            test_missing_chat_msg(session),
            test_python_health(session),
            test_cors(session),
            test_malformed_json(session),
            test_xss_injection(session),
            test_sql_injection(session),
            test_mcp_source(session)
        )
        # Sequential for rate limiting and performance so they don't clobber
        await test_rate_limiting(session)
        await test_performance_simultaneous(session)

    with open("qa_api_report.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
