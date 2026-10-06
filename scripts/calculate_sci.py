#!/usr/bin/env python3
"""
AutoSecOps GreenSentinel - Software Carbon Intensity (SCI) Engine
Compliant with Green Software Foundation (GSF) Specification (SCI = ((E * I) + M) / R)
Stand-alone CLI and Python Module.
"""

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


# Official GCP Region Carbon Intensity Data (gCO2eq / kWh)
# Sources: Google Environmental Report & Electricity Maps Annual Averages
GCP_REGION_INTENSITIES: Dict[str, Dict[str, Any]] = {
    "europe-west9": {
        "location": "Paris, France",
        "grid_intensity_gco2_kwh": 51.0,
        "pue": 1.10,
        "cbe_score": 96.0,  # Carbon-Free Energy %
    },
    "europe-north1": {
        "location": "Hamina, Finland",
        "grid_intensity_gco2_kwh": 85.0,
        "pue": 1.12,
        "cbe_score": 93.0,
    },
    "us-east4": {
        "location": "Northern Virginia, USA",
        "grid_intensity_gco2_kwh": 378.0,
        "pue": 1.15,
        "cbe_score": 62.0,
    },
    "us-central1": {
        "location": "Iowa, USA",
        "grid_intensity_gco2_kwh": 394.0,
        "pue": 1.18,
        "cbe_score": 68.0,
    },
    "asia-southeast1": {
        "location": "Jurong West, Singapore",
        "grid_intensity_gco2_kwh": 413.0,
        "pue": 1.25,
        "cbe_score": 4.0,
    },
    "us-east1": {
        "location": "South Carolina, USA",
        "grid_intensity_gco2_kwh": 480.0,
        "pue": 1.20,
        "cbe_score": 56.0,
    },
    "asia-south1": {
        "location": "Mumbai, India",
        "grid_intensity_gco2_kwh": 632.0,
        "pue": 1.28,
        "cbe_score": 18.0,
    },
}

# GSF Model Parameters
STANDARD_INSTANCE_TDP_WATTS = 50.0  # Server baseline TDP watts per instance
DEFAULT_CPU_LOAD = 0.5             # 50% average operational compute utilization
DEFAULT_EMBODIED_M = 0.005         # 0.005 gCO2e embodied hardware emissions baseline
BASELINE_HIGH_CARBON_REGION = "us-east1"  # 480 gCO2/kWh


@dataclass
class SCIMetrics:
    runtime_seconds: float
    runtime_hours: float
    instances: int
    vcpus: int
    region: str
    location: str
    grid_intensity_gco2_kwh: float
    pue: float
    avg_cpu_load: float
    energy_kwh: float                    # E
    operational_carbon_gco2e: float      # E * I
    embodied_carbon_gco2e: float         # M
    sci_score_gco2e: float               # ((E * I) + M) / R
    functional_unit: str
    baseline_region: str
    baseline_grid_intensity_gco2_kwh: float
    baseline_sci_score_gco2e: float
    savings_vs_dirtiest_gco2e: float     # Carbon saved (gCO2e)
    carbon_saved_gco2e: float            # Alias
    savings_percentage: float            # Carbon reduction %
    carbon_reduction_percent: float      # Alias
    formula: str = "SCI = ((E * I) + M) / R"


class SCICalculator:
    """Calculates Software Carbon Intensity adhering to GSF SCI Standard."""

    @staticmethod
    def get_region_data(region: str) -> Dict[str, Any]:
        normalized = region.lower().strip()
        if normalized not in GCP_REGION_INTENSITIES:
            return {
                "location": f"Custom Region ({region})",
                "grid_intensity_gco2_kwh": 400.0,
                "pue": 1.15,
                "cbe_score": 50.0,
            }
        return GCP_REGION_INTENSITIES[normalized]

    @classmethod
    def calculate(
        cls,
        runtime_seconds: float,
        instances: int = 1,
        vcpus: Optional[int] = None,
        region: str = "europe-west9",
        avg_cpu_load: float = DEFAULT_CPU_LOAD,
        functional_unit_name: str = "pipeline_run",
        functional_unit_count: float = 1.0,
    ) -> SCIMetrics:
        """
        Compute GSF SCI = ((E * I) + M) / R
        """
        if vcpus is None:
            vcpus = instances * 2
        effective_instances = max(instances, 1)

        reg_info = cls.get_region_data(region)
        runtime_hours = max(runtime_seconds, 0.01) / 3600.0
        pue = reg_info["pue"]
        grid_i = reg_info["grid_intensity_gco2_kwh"]

        # E = (Watts * Runtime_Hours * PUE) / 1000
        if vcpus is not None:
            active_watts = vcpus * 18.5
        else:
            active_watts = effective_instances * STANDARD_INSTANCE_TDP_WATTS * avg_cpu_load
        energy_kwh = (active_watts * runtime_hours * pue) / 1000.0

        # Operational Carbon: E * I
        operational_gco2e = energy_kwh * grid_i

        # Embodied Carbon: M = 0.005 gCO2e per instance scaled by runtime
        embodied_gco2e = DEFAULT_EMBODIED_M * effective_instances * max(runtime_seconds / 120.0, 0.5)

        # Total SCI Score = ((E * I) + M) / R
        r_unit = max(functional_unit_count, 1.0)
        sci_score = (operational_gco2e + embodied_gco2e) / r_unit

        # Baseline High Carbon Comparison (us-east1: 480 gCO2/kWh, PUE 1.20)
        base_data = GCP_REGION_INTENSITIES.get(BASELINE_HIGH_CARBON_REGION, {"grid_intensity_gco2_kwh": 480.0, "pue": 1.20})
        base_i = base_data["grid_intensity_gco2_kwh"]
        base_pue = base_data["pue"]
        base_energy = (active_watts * runtime_hours * base_pue) / 1000.0
        base_sci = ((base_energy * base_i) + embodied_gco2e) / r_unit

        saved_carbon = max(0.0, base_sci - sci_score)
        savings_pct = (saved_carbon / base_sci * 100.0) if base_sci > 0 else 0.0

        return SCIMetrics(
            runtime_seconds=round(runtime_seconds, 2),
            runtime_hours=round(runtime_hours, 6),
            instances=effective_instances,
            vcpus=vcpus,
            region=region,
            location=reg_info["location"],
            grid_intensity_gco2_kwh=grid_i,
            pue=pue,
            avg_cpu_load=avg_cpu_load,
            energy_kwh=round(energy_kwh, 6),
            operational_carbon_gco2e=round(operational_gco2e, 4),
            embodied_carbon_gco2e=round(embodied_gco2e, 4),
            sci_score_gco2e=round(sci_score, 4),
            functional_unit=functional_unit_name,
            baseline_region=BASELINE_HIGH_CARBON_REGION,
            baseline_grid_intensity_gco2_kwh=base_i,
            baseline_sci_score_gco2e=round(base_sci, 4),
            savings_vs_dirtiest_gco2e=round(saved_carbon, 4),
            carbon_saved_gco2e=round(saved_carbon, 4),
            savings_percentage=round(savings_pct, 2),
            carbon_reduction_percent=round(savings_pct, 2),
            formula="SCI = ((E * I) + M) / R",
        )

    @classmethod
    def select_best_region(cls, candidates: Optional[List[str]] = None) -> Dict[str, Any]:
        """Rank candidate regions by grid intensity (lowest gCO2/kWh first)."""
        if not candidates:
            candidates = list(GCP_REGION_INTENSITIES.keys())

        ranked = []
        for reg in candidates:
            reg_clean = reg.strip().lower()
            if reg_clean in GCP_REGION_INTENSITIES:
                data = GCP_REGION_INTENSITIES[reg_clean]
                ranked.append({
                    "region": reg_clean,
                    "location": data["location"],
                    "intensity": data["grid_intensity_gco2_kwh"],
                    "cbe_score": data["cbe_score"],
                    "pue": data["pue"],
                })

        ranked.sort(key=lambda x: (x["intensity"], x["pue"]))
        best = ranked[0] if ranked else {
            "region": "europe-west9",
            "location": "Paris, France",
            "intensity": 51.0,
            "cbe_score": 96.0,
            "pue": 1.10
        }

        return {
            "selected_greenest_region": best["region"],
            "lowest_intensity_gco2_kwh": best["intensity"],
            "location": best["location"],
            "pue": best["pue"],
            "carbon_free_energy_percent": best["cbe_score"],
            "ranked_regions": ranked,
        }


def main():
    parser = argparse.ArgumentParser(description="Green Software Foundation SCI Calculator")
    parser.add_argument("--runtime-seconds", type=float, default=120.0, help="Pipeline duration in seconds")
    parser.add_argument("--region", type=str, default="europe-west9", help="Google Cloud region")
    parser.add_argument("--instances", type=int, default=1, help="Number of compute instances")
    parser.add_argument("--vcpus", type=int, default=None, help="vCPU count (defaults to instances * 2)")
    parser.add_argument("--output-file", type=str, default=None, help="Save JSON report to file")
    parser.add_argument("--json", action="store_true", help="Output pure JSON")

    args = parser.parse_args()
    metrics = SCICalculator.calculate(
        runtime_seconds=args.runtime_seconds,
        instances=args.instances,
        vcpus=args.vcpus,
        region=args.region,
    )

    metrics_dict = asdict(metrics)

    if args.output_file:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(metrics_dict, f, indent=2)
        print(f"[OK] SCI report saved to {args.output_file}")

    if args.json:
        print(json.dumps(metrics_dict, indent=2))
    else:
        print("=" * 65)
        print(" AutoSecOps GreenSentinel - Software Carbon Intensity Report")
        print(" Standard: Green Software Foundation (GSF) SCI Equation")
        print("=" * 65)
        print(f" Region               : {metrics.region} ({metrics.location})")
        print(f" Grid Intensity (I)   : {metrics.grid_intensity_gco2_kwh} gCO2eq/kWh")
        print(f" Datacenter PUE       : {metrics.pue}")
        print(f" CPU Load             : {metrics.avg_cpu_load * 100:.0f}%")
        print(f" Energy Consumed (E)  : {metrics.energy_kwh:.6f} kWh")
        print(f" Operational Carbon   : {metrics.operational_carbon_gco2e:.4f} gCO2eq")
        print(f" Embodied Carbon (M)  : {metrics.embodied_carbon_gco2e:.4f} gCO2eq")
        print("-" * 65)
        print(f" >>> SCI Score        : {metrics.sci_score_gco2e:.4f} gCO2eq / {metrics.functional_unit}")
        print(f" >>> Baseline Grid    : {metrics.baseline_region} ({metrics.baseline_grid_intensity_gco2_kwh} gCO2eq/kWh)")
        print(f" >>> Carbon Prevented : {metrics.carbon_saved_gco2e:.4f} gCO2eq (-{metrics.carbon_reduction_percent}%)")
        print("=" * 65)


if __name__ == "__main__":
    main()
