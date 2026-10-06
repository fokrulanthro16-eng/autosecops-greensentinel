#!/usr/bin/env python3
"""
AutoSecOps GreenSentinel - Comprehensive Test Suite
Validates API endpoints, GSF SCI carbon math, MCP self-healing engine, and green routing.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure root directory is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app, STAGES_REGISTRY
from scripts.calculate_sci import SCICalculator, GCP_REGION_INTENSITIES
from agent_mcp.server import (
    diagnose_pipeline_log,
    analyze_failure_and_heal,
    calculate_sci_score,
    select_greenest_gcp_region,
    generate_security_patch,
)

client = TestClient(app)


# ==========================================
# 1. API Endpoints Tests
# ==========================================

def test_health_check_endpoint():
    """Verify /health returns 200 and valid JSON with service name and uptime."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "AutoSecOps GreenSentinel"
    assert "uptime_seconds" in data
    assert "timestamp" in data
    # Check custom Prometheus/Carbon headers
    assert "X-Compute-Latency-ms" in response.headers
    assert "X-Carbon-Intensity-gCO2e" in response.headers
    assert response.headers["X-Agent-Status"] == "AUTONOMOUS_OPERATIONAL"


def test_telemetry_endpoint():
    """Verify /telemetry returns telemetry data and carbon attributes."""
    response = client.get("/telemetry")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "autosecops-greensentinel"
    assert data["grid_carbon_intensity_gco2_kwh"] > 0
    assert data["datacenter_pue"] >= 1.0
    assert data["self_healing_success_rate_percent"] == 100.0


def test_api_status_covers_all_9_stages():
    """Verify that all 9 DevSecOps stages are present and correctly reported."""
    expected_stages = [
        "plan",
        "create",
        "verify",
        "package",
        "secure",
        "govern",
        "release",
        "configure",
        "monitor",
    ]
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["stages_count"] == 9
    assert data["pipeline_status"] == "SUCCESSFUL_AUTONOMOUS"
    
    stages_in_response = [s["stage"] for s in data["stages"]]
    for expected in expected_stages:
        assert expected in stages_in_response, f"Missing stage in lifecycle: {expected}"
    
    # Verify plain english and Bengali summary exist for zero-cognitive load
    for stage_data in data["stages"]:
        assert len(stage_data["plain_english"]) > 0
        assert len(stage_data["bengali_summary"]) > 0


def test_sci_metrics_endpoint():
    """Verify /api/sci-metrics endpoint returns valid GSF equation outputs."""
    response = client.get("/api/sci-metrics?runtime_seconds=120&vcpus=2&region=europe-west9")
    assert response.status_code == 200
    data = response.json()
    assert "metrics" in data
    metrics = data["metrics"]
    assert metrics["energy_kwh"] > 0
    assert metrics["operational_carbon_gco2e"] > 0
    assert metrics["embodied_carbon_gco2e"] > 0
    assert metrics["sci_score_gco2e"] > 0
    assert metrics["savings_percentage"] > 0
    assert data["routing_recommendation"]["selected_greenest_region"] == "europe-west9"


# ==========================================
# 2. GSF SCI Engine Mathematical Tests
# ==========================================

def test_sci_engine_mathematical_accuracy():
    """
    Validate SCI equation: SCI = ((E * I) + M) / R
    where E = (vCPUs * Watts * hours * PUE) / 1000
    """
    runtime_s = 3600.0  # 1 hour
    vcpus = 2
    metrics = SCICalculator.calculate(
        runtime_seconds=runtime_s,
        vcpus=vcpus,
        region="europe-west9",
        functional_unit_name="hourly_run",
    )
    
    # Known values for europe-west9: PUE=1.10, I=51 gCO2/kWh, W_PER_VCPU=18.5
    expected_watts = 2 * 18.5  # 37 W
    expected_energy_kwh = (37 * 1.0 * 1.10) / 1000.0  # 0.0407 kWh
    expected_operational = expected_energy_kwh * 51.0   # 2.0757 gCO2e
    
    assert pytest.approx(metrics.energy_kwh, rel=1e-3) == expected_energy_kwh
    assert pytest.approx(metrics.operational_carbon_gco2e, rel=1e-3) == expected_operational
    assert metrics.sci_score_gco2e > metrics.operational_carbon_gco2e  # Includes embodied M


def test_green_routing_selection():
    """Verify selection of lowest carbon region among available GCP datacenters."""
    candidates = ["asia-south1", "us-central1", "europe-west9", "asia-southeast1"]
    result = SCICalculator.select_best_region(candidates)
    
    # europe-west9 is 51 gCO2/kWh, lowest in candidate list
    assert result["selected_greenest_region"] == "europe-west9"
    # Ensure ranking is ordered ascending by carbon intensity
    intensities = [r["intensity"] for r in result["ranked_regions"]]
    assert intensities == sorted(intensities)


# ==========================================
# 3. FastMCP Self-Healing & Tooling Tests
# ==========================================

def test_mcp_diagnose_carbon_budget_failure():
    """Verify agent detects carbon budget breach and produces regional reroute diff."""
    mock_log = "AssertionError: Carbon budget exceeded: 4.80 > 2.00 gCO2e"
    diag = diagnose_pipeline_log(mock_log)
    assert diag["status"] == "DIAGNOSED"
    assert "carbon budget" in diag["root_cause"].lower()
    assert "europe-west9" in diag["git_patch"]
    assert len(diag["plain_english_summary"]) > 0


def test_mcp_diagnose_syntax_failure():
    """Verify agent catches indentation errors and creates PEP8 fix diff."""
    mock_log = "IndentationError: unexpected indent in app/main.py:110"
    diag = analyze_failure_and_heal(mock_log)
    assert diag["status"] == "DIAGNOSED"
    assert "indentation" in diag["root_cause"].lower()
    assert "git_patch" in diag


def test_mcp_generate_security_patch():
    """Verify security scanner CVE triage produces valid remediation."""
    cve_report = "CWE-89: SQL Injection detected in runner database query"
    patch_result = generate_security_patch(cve_report)
    assert patch_result["vulnerability_type"] == "SQL Injection (CWE-89)"
    assert patch_result["severity"] == "CRITICAL"
    assert ":runner_id" in patch_result["git_patch"]
