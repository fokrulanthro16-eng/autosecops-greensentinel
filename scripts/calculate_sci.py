#!/usr/bin/env python3
"""
AutoSecOps GreenSentinel - Software Carbon Intensity (SCI) Engine
Compliant with Green Software Foundation (GSF) Specification (SCI = ((E * I) + M) / R)
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from typing import Dict, Optional


# Official GCP Region Carbon Intensity Data (gCO2eq / kWh)
# Sources: Google Environmental Report & Electricity Maps Annual Averages
GCP_REGION_INTENSITIES: Dict[str, Dict[str, float]] = {
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
    "us-central1": {
        "location": "Iowa, USA",
        "grid_intensity_gco2_kwh": 394.0,
        "pue": 1.18,
        "cbe_score": 68.0,
    },
    "us-east4": {
        "location": "Northern Virginia, USA",
        "grid_intensity_gco2_kwh": 378.0,
        "pue": 1.15,
        "cbe_score": 62.0,
    },
    "asia-southeast1": {
        "location": "Jurong West, Singapore",
        "grid_intensity_gco2_kwh": 413.0,
        "pue": 1.25,
        "cbe_score": 4.0,
    },
    "asia-south1": {
        "location": "Mumbai, India",
        "grid_intensity_gco2_kwh": 632.0,
        "pue": 1.28,
        "cbe_score": 18.0,
    },
}

# Average hardware power profiles (Watts per vCPU under typical CI/CD load)
W_PER_VCPU = 18.5  # Intel Xeon / AMD EPYC thermal design average at 70% load
TOTAL_SERVER_EMBODIED_GCO2 = 1_200_000.0  # ~1.2 metric tons CO2e per 64-vCPU host
SERVER_LIFESPAN_HOURS = 4 * 365 * 24.0   # 35,040 hours (4-year depreciation)
SERVER_TOTAL_VCPUS = 64.0


@dataclass
class SCIMetrics:
    runtime_seconds: float
    runtime_hours: float
    vcpus: int
    region: str
    location: str
    grid_intensity_gco2_kwh: float
    pue: float
    energy_kwh: float            # E
    operational_carbon_gco2e: float  # E * I
    embodied_carbon_gco2e: float     # M
    sci_score_gco2e: float       # ((E * I) + M) / R
    functional_unit: str
    savings_vs_dirtiest_gco2e: float
    savings_percentage: float


class SCICalculator:
    """Calculates Software Carbon Intensity adhering to GSF SCI Standard."""

    @staticmethod
    def get_region_data(region: str) -> Dict[str, float]:
        normalized = region.lower().strip()
        if normalized not in GCP_REGION_INTENSITIES:
            # Default fallback to global average
            return {
                "location": f"Custom Region ({region})",
                "grid_intensity_gco2_kwh": 400.0,
                "pue": 1.20,
                "cbe_score": 50.0,
            }
        return GCP_REGION_INTENSITIES[normalized]

    @classmethod
    def calculate(
        cls,
        runtime_seconds: float,
        vcpus: int = 2,
        region: str = "europe-west9",
        functional_unit_name: str = "pipeline_run",
        functional_unit_count: float = 1.0,
    ) -> SCIMetrics:
        """
        Compute SCI = ((E * I) + M) / R
        """
        reg_info = cls.get_region_data(region)
        runtime_hours = max(runtime_seconds, 0.1) / 3600.0
        pue = reg_info["pue"]
        grid_i = reg_info["grid_intensity_gco2_kwh"]

        # E = (vCPU * Watts * Runtime_Hours * PUE) / 1000 W/kW
        watts = vcpus * W_PER_VCPU
        energy_kwh = (watts * runtime_hours * pue) / 1000.0

        # Operational Carbon: E * I
        operational_gco2e = energy_kwh * grid_i

        # M = TE * (TR / EL) * (RR / TR) -> TE * (Runtime / Lifespan) * (vCPUs / Host_vCPUs)
        resource_share = vcpus / SERVER_TOTAL_VCPUS
        time_share = runtime_hours / SERVER_LIFESPAN_HOURS
        embodied_gco2e = TOTAL_SERVER_EMBODIED_GCO2 * time_share * resource_share

        # SCI Score
        r_unit = max(functional_unit_count, 1.0)
        sci_score = (operational_gco2e + embodied_gco2e) / r_unit

        # Compare with worst case (e.g. asia-south1: 632 gCO2/kWh, PUE 1.28)
        worst_i = GCP_REGION_INTENSITIES["asia-south1"]["grid_intensity_gco2_kwh"]
        worst_pue = GCP_REGION_INTENSITIES["asia-south1"]["pue"]
        worst_energy = (watts * runtime_hours * worst_pue) / 1000.0
        worst_sci = ((worst_energy * worst_i) + embodied_gco2e) / r_unit

        savings = max(0.0, worst_sci - sci_score)
        savings_pct = (savings / worst_sci * 100.0) if worst_sci > 0 else 0.0

        return SCIMetrics(
            runtime_seconds=round(runtime_seconds, 2),
            runtime_hours=round(runtime_hours, 6),
            vcpus=vcpus,
            region=region,
            location=reg_info["location"],
            grid_intensity_gco2_kwh=grid_i,
            pue=pue,
            energy_kwh=round(energy_kwh, 6),
            operational_carbon_gco2e=round(operational_gco2e, 4),
            embodied_carbon_gco2e=round(embodied_gco2e, 4),
            sci_score_gco2e=round(sci_score, 4),
            functional_unit=functional_unit_name,
            savings_vs_dirtiest_gco2e=round(savings, 4),
            savings_percentage=round(savings_pct, 2),
        )

    @classmethod
    def select_best_region(cls, candidates: Optional[list] = None) -> Dict[str, any]:
        """Rank candidates by grid intensity (lowest carbon first)."""
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
        return {
            "selected_greenest_region": ranked[0]["region"] if ranked else "europe-west9",
            "ranked_regions": ranked,
        }


def main():
    parser = argparse.ArgumentParser(description="Green Software Foundation SCI Calculator")
    parser.add_argument("--runtime-seconds", type=float, default=120.0, help="Pipeline or task duration in seconds")
    parser.add_argument("--vcpus", type=int, default=2, help="Number of virtual CPU cores allocated")
    parser.add_argument("--region", type=str, default="europe-west9", help="Google Cloud Platform region")
    parser.add_argument("--functional-unit", type=str, default="pipeline_run", help="SCI functional unit denominator name")
    parser.add_argument("--json", action="store_true", help="Output pure JSON format")

    args = parser.parse_args()
    metrics = SCICalculator.calculate(
        runtime_seconds=args.runtime_seconds,
        vcpus=args.vcpus,
        region=args.region,
        functional_unit_name=args.functional_unit,
    )

    if args.json:
        print(json.dumps(asdict(metrics), indent=2))
    else:
        print("=" * 60)
        print(" AutoSecOps GreenSentinel - SCI Score Report")
        print("=" * 60)
        print(f" Region               : {metrics.region} ({metrics.location})")
        print(f" Grid Intensity (I)   : {metrics.grid_intensity_gco2_kwh} gCO2eq/kWh")
        print(f" PUE Factor           : {metrics.pue}")
        print(f" Energy Consumed (E)  : {metrics.energy_kwh:.6f} kWh")
        print(f" Operational Carbon   : {metrics.operational_carbon_gco2e:.4f} gCO2eq")
        print(f" Embodied Carbon (M)  : {metrics.embodied_carbon_gco2e:.4f} gCO2eq")
        print("-" * 60)
        print(f" >>> Total SCI Score  : {metrics.sci_score_gco2e:.4f} gCO2eq / {metrics.functional_unit}")
        print(f" >>> Carbon Reduction : {metrics.savings_percentage}% saved vs dirty grid")
        print(f" >>> Saved CO2 Mass   : {metrics.savings_vs_dirtiest_gco2e:.4f} gCO2eq")
        print("=" * 60)


if __name__ == "__main__":
    main()
