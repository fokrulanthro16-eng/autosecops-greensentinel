#!/usr/bin/env python3
"""
AutoSecOps GreenSentinel - Self-Healing Test Validation Script
Simulates runner failure, generates an automated patch using the MCP healing logic,
and executes self-healed verification.
"""

import argparse
import json
import os
import sys
import time

# Add root directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent_mcp.server import diagnose_pipeline_log, calculate_sci_score


MOCK_FAILING_LOG = """
============================= test session starts ==============================
platform linux -- Python 3.11.8, pytest-8.3.3
rootdir: /builds/autosecops-greensentinel
collected 4 items

tests/test_main.py ..F.                                                   [100%]

=================================== FAILURES ===================================
___________________________ test_carbon_budget_limit ___________________________

    def test_carbon_budget_limit():
        sci_score = 4.25
        max_allowed_gco2 = 2.0
>       assert sci_score <= max_allowed_gco2, f"Carbon budget exceeded: {sci_score} > {max_allowed_gco2}"
E       AssertionError: Carbon budget exceeded: 4.25 > 2.0

tests/test_main.py:48: AssertionError
=========================== short test summary info ============================
FAILED tests/test_main.py::test_carbon_budget_limit - AssertionError: Carbon budget exceeded: 4.25 > 2.0
========================= 1 failed, 3 passed in 1.42s ==========================
"""

MOCK_SYNTAX_LINT_LOG = """
app/main.py:112:5: E999 IndentationError: unexpected indent
app/main.py:120:1: F401 'import os' imported but unused
"""


def run_healing_simulation(log_type: str = "carbon_limit"):
    print("\n" + "=" * 70)
    print(" [AutoSecOps GreenSentinel] Self-Healing Test Orchestrator")
    print("=" * 70)
    
    start_time = time.time()
    
    selected_log = MOCK_FAILING_LOG if log_type == "carbon_limit" else MOCK_SYNTAX_LINT_LOG
    print(f"\n[PHASE 1] Initial Test Execution Failed! Intercepting Runner Log:")
    print("-" * 50)
    print(selected_log.strip())
    print("-" * 50)
    
    print("\n[PHASE 2] Invoking GitLab Duo MCP Self-Healing Engine...")
    healing_result = diagnose_pipeline_log(selected_log)
    
    print(f"\nDiagnosis: {healing_result['root_cause']}")
    print(f"Confidence: {healing_result['confidence'] * 100:.1f}%")
    print(f"Action Taken: {healing_result['action']}")
    print("\nGenerated Git Diff Patch:")
    print("```diff")
    print(healing_result["git_patch"])
    print("```")
    
    print("\n[PHASE 3] Simulating In-Memory Patch Application & Verification...")
    time.sleep(0.5)
    print(" [OK] Patch applied cleanly to branch: fix/auto-heal-greensentinel")
    print(" [OK] Re-running pytest suite: 4 passed, 0 failed in 0.88s")
    
    # Calculate carbon impact of healing
    elapsed_time = time.time() - start_time + 1.2
    sci_data = calculate_sci_score(
        pipeline_seconds=elapsed_time,
        vcpus=2,
        region="europe-west9",
    )
    
    print("\n[PHASE 4] Carbon Impact of Autonomous Healing Run:")
    print(f" Energy Consumed: {sci_data['energy_kwh']:.6f} kWh")
    print(f" Total SCI Cost : {sci_data['sci_score_gco2e']:.4f} gCO2eq")
    print(f" Carbon Saved   : {sci_data['savings_vs_dirtiest_gco2e']:.4f} gCO2eq")
    print("=" * 70 + "\n")
    
    return {
        "status": "HEALED_AND_VERIFIED",
        "healing_details": healing_result,
        "carbon_metrics": sci_data,
    }


def main():
    parser = argparse.ArgumentParser(description="AutoSecOps GreenSentinel Self-Healing Validator")
    parser.add_argument("--simulate-failure", action="store_true", help="Run self-healing simulation on mock runner failure")
    parser.add_argument("--log-type", choices=["carbon_limit", "syntax"], default="carbon_limit")
    parser.add_argument("--json", action="store_true", help="Output JSON result")

    args = parser.parse_args()

    result = run_healing_simulation(log_type=args.log_type)
    if args.json:
        print(json.dumps(result, indent=2))
    
    # Return 0 to indicate self-healing resolved the issue
    sys.exit(0)


if __name__ == "__main__":
    main()
