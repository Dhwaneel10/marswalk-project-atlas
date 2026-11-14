"""MarsWalk 2.0 / Project Atlas  Milestone 13S: Surface Power System & Energy Balances.

Models Nuclear Fission (NASA 2024 ACR reference), Solar PV with dust accumulation
and cleaning cycles, Hybrid Battery Storage, and time-dependent energy balances
with policy-driven load shedding under 13R fault conditions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PowerSourceType(str, Enum):
    """Primary surface electrical generation technologies."""
    NUCLEAR_FISSION = "NUCLEAR_FISSION"      # Low-enriched uranium Stirling/Brayton reactor (continuous)
    SOLAR_PV = "SOLAR_PV"                    # Multi-junction photovoltaic array with diurnal/dust variation
    HYBRID_STORAGE = "HYBRID_STORAGE"        # Solar PV combined with stationary battery storage
    FUEL_CELL_STORAGE = "FUEL_CELL_STORAGE"  # Regenerative hydrogen-oxygen fuel cell system


class LoadPriority(int, Enum):
    """Shedding priority under power deficit (1 = highest priority, never shed)."""
    CRITICAL_LIFE_SUPPORT = 1                # ECLSS atmospheric pressure, O2 loop, survival heaters
    PRIMARY_COMMS = 2                        # Earth DTE and orbiter uplink
    HABITAT_THERMAL = 3                      # Internal living temperature maintenance
    ISRU_PRODUCTION = 4                      # Water extraction and oxygen liquefaction plants
    SCIENCE_LABORATORY = 5                   # Analytical instruments and sample freezers
    ROBOTIC_CONSTRUCTION = 6                 # Automated excavation, grading, and cranes
    ROVER_CHARGING_DEPOT = 7                 # Fleet battery recharge (shed first during emergencies)


@dataclass
class PowerLoadItem:
    """An individual electrical consumer in the settlement."""
    load_id: str
    name: str
    priority: LoadPriority
    nominal_power_kw: float
    duty_cycle: float = 1.0                  # Fraction of sol active (0.0 to 1.0)
    current_allocated_power_kw: float = 0.0
    is_shed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "load_id": self.load_id,
            "name": self.name,
            "priority": self.priority.value,
            "nominal_power_kw": round(self.nominal_power_kw, 2),
            "duty_cycle": round(self.duty_cycle, 2),
            "current_allocated_power_kw": round(self.current_allocated_power_kw, 2),
            "is_shed": self.is_shed,
        }


@dataclass
class PowerSystemTelemetry:
    """Instantaneous snapshot of settlement energy balance."""
    timestamp_sol: int
    time_of_sol_s: float                     # 0 to 88775 seconds
    solar_insolation_wm2: float
    dust_accumulation_factor: float          # 1.0 = pristine clean, 0.4 = heavy dust coverage
    generation_gross_kw: float
    distribution_losses_kw: float
    total_demand_kw: float
    total_delivered_kw: float
    unmet_demand_kw: float
    battery_charge_kwh: float
    battery_soc_pct: float                   # State of charge (0 to 100%)
    battery_degradation_factor: float        # 1.0 to 0.7 over mission life
    active_shed_loads: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp_sol": self.timestamp_sol,
            "time_of_sol_s": round(self.time_of_sol_s, 1),
            "solar_insolation_wm2": round(self.solar_insolation_wm2, 1),
            "dust_accumulation_factor": round(self.dust_accumulation_factor, 3),
            "generation_gross_kw": round(self.generation_gross_kw, 2),
            "distribution_losses_kw": round(self.distribution_losses_kw, 2),
            "total_demand_kw": round(self.total_demand_kw, 2),
            "total_delivered_kw": round(self.total_delivered_kw, 2),
            "unmet_demand_kw": round(self.unmet_demand_kw, 2),
            "battery_charge_kwh": round(self.battery_charge_kwh, 2),
            "battery_soc_pct": round(self.battery_soc_pct, 1),
            "battery_degradation_factor": round(self.battery_degradation_factor, 3),
            "active_shed_loads": self.active_shed_loads,
        }


class SettlementPowerSystem:
    """Simulates surface power generation, storage thermodynamics, and priority shedding."""

    def __init__(
        self,
        system_type: PowerSourceType = PowerSourceType.NUCLEAR_FISSION,
        nameplate_capacity_kw: float = 120.0,
        battery_capacity_kwh: float = 600.0,
        solar_array_area_m2: float = 1400.0,
        solar_efficiency: float = 0.28,
        distribution_loss_pct: float = 4.5,
    ):
        self.system_type = system_type
        self.nameplate_capacity_kw = nameplate_capacity_kw
        self.battery_capacity_kwh = battery_capacity_kwh
        self.current_battery_kwh = battery_capacity_kwh * 0.90  # Start at 90% SoC
        self.solar_array_area_m2 = solar_array_area_m2
        self.solar_efficiency = solar_efficiency
        self.distribution_loss_pct = distribution_loss_pct

        self.dust_accumulation_factor: float = 1.0
        self.battery_degradation_factor: float = 1.0
        self.generator_availability_factor: float = 1.0  # 0.0 under generator outage

        self._loads: Dict[str, PowerLoadItem] = self._build_default_loads()

    def set_generator_status(self, availability: float) -> None:
        """Sets generator health (e.g., 0.0 for emergency trip, 0.5 for partial loop fail)."""
        self.generator_availability_factor = max(0.0, min(1.0, availability))

    def perform_dust_cleaning_cycle(self) -> None:
        """Electrostatic dust shield or mechanical wiper cleaning restores panel transmission."""
        self.dust_accumulation_factor = min(1.0, self.dust_accumulation_factor + 0.35)

    def step_sol_time(
        self,
        sol: int,
        time_s: float,
        dt_s: float = 3600.0,
        atmospheric_tau: float = 0.45,
    ) -> PowerSystemTelemetry:
        """Computes power generation, load distribution, and battery updates for timestep dt_s."""
        # Mars sol length = 88775 seconds
        sol_fraction = (time_s % 88775.0) / 88775.0
        sun_elevation = math.sin((sol_fraction - 0.25) * 2.0 * math.pi)

        # Diurnal solar insolation
        if sun_elevation > 0.0:
            direct_flux = 590.0 * math.exp(-atmospheric_tau / max(0.1, sun_elevation))
            insolation = direct_flux * sun_elevation
        else:
            insolation = 0.0

        # Natural dust accumulation (continuous deposition)
        self.dust_accumulation_factor = max(0.20, self.dust_accumulation_factor - 0.00008 * (dt_s / 3600.0))
        # Battery degradation (cycle wear)
        self.battery_degradation_factor = max(0.65, self.battery_degradation_factor - 0.00002 * (dt_s / 3600.0))

        # Generation calculation
        if self.system_type == PowerSourceType.NUCLEAR_FISSION:
            gross_gen_kw = self.nameplate_capacity_kw * self.generator_availability_factor
        elif self.system_type == PowerSourceType.SOLAR_PV:
            pv_gen_kw = (insolation * self.solar_array_area_m2 * self.solar_efficiency * self.dust_accumulation_factor) / 1000.0
            gross_gen_kw = pv_gen_kw * self.generator_availability_factor
        else: # HYBRID_STORAGE
            fission_base = (self.nameplate_capacity_kw * 0.6) * self.generator_availability_factor
            pv_solar = (insolation * (self.solar_array_area_m2 * 0.7) * self.solar_efficiency * self.dust_accumulation_factor) / 1000.0
            gross_gen_kw = fission_base + pv_solar

        dist_loss_kw = gross_gen_kw * (self.distribution_loss_pct / 100.0)
        net_gen_kw = max(0.0, gross_gen_kw - dist_loss_kw)

        # Demand calculation
        total_demand_kw = sum(l.nominal_power_kw * l.duty_cycle for l in self._loads.values())

        # Power balance & Battery integration
        # P_net = P_available - P_demand
        active_shed: List[str] = []
        allocated_total_kw = 0.0

        # Sort loads by priority (Priority 1 = life support first, Priority 7 = rover depot last)
        sorted_loads = sorted(self._loads.values(), key=lambda l: l.priority.value)

        # If net generation >= demand, supply all and charge battery
        effective_batt_max = self.battery_capacity_kwh * self.battery_degradation_factor

        if net_gen_kw >= total_demand_kw:
            surplus_kw = net_gen_kw - total_demand_kw
            for l in sorted_loads:
                l.current_allocated_power_kw = l.nominal_power_kw * l.duty_cycle
                l.is_shed = False
            allocated_total_kw = total_demand_kw

            # Charge battery (92% roundtrip efficiency)
            charge_energy_kwh = surplus_kw * (dt_s / 3600.0) * 0.92
            self.current_battery_kwh = min(effective_batt_max, self.current_battery_kwh + charge_energy_kwh)
            unmet_kw = 0.0

        else:
            # Deficit: net generation < demand
            # Draw from battery if available above 15% reserve limit
            deficit_kw = total_demand_kw - net_gen_kw
            min_reserve_kwh = effective_batt_max * 0.15
            available_battery_kwh = max(0.0, self.current_battery_kwh - min_reserve_kwh)
            max_batt_discharge_kw = available_battery_kwh / (dt_s / 3600.0)

            batt_support_kw = min(deficit_kw, max_batt_discharge_kw)
            self.current_battery_kwh -= batt_support_kw * (dt_s / 3600.0)

            total_available_kw = net_gen_kw + batt_support_kw

            # Allocate power according to priority rules; shed noncritical loads
            remaining_supply_kw = total_available_kw
            for l in sorted_loads:
                req_kw = l.nominal_power_kw * l.duty_cycle
                if remaining_supply_kw >= req_kw:
                    l.current_allocated_power_kw = req_kw
                    l.is_shed = False
                    remaining_supply_kw -= req_kw
                    allocated_total_kw += req_kw
                elif remaining_supply_kw > 0.0 and l.priority.value <= 3:
                    # Partial power for critical/life support
                    l.current_allocated_power_kw = remaining_supply_kw
                    l.is_shed = False
                    allocated_total_kw += remaining_supply_kw
                    remaining_supply_kw = 0.0
                else:
                    l.current_allocated_power_kw = 0.0
                    l.is_shed = True
                    active_shed.append(l.name)

            unmet_kw = max(0.0, total_demand_kw - allocated_total_kw)

        soc_pct = (self.current_battery_kwh / max(1.0, effective_batt_max)) * 100.0

        return PowerSystemTelemetry(
            timestamp_sol=sol,
            time_of_sol_s=time_s,
            solar_insolation_wm2=insolation,
            dust_accumulation_factor=self.dust_accumulation_factor,
            generation_gross_kw=gross_gen_kw,
            distribution_losses_kw=dist_loss_kw,
            total_demand_kw=total_demand_kw,
            total_delivered_kw=allocated_total_kw,
            unmet_demand_kw=unmet_kw,
            battery_charge_kwh=self.current_battery_kwh,
            battery_soc_pct=soc_pct,
            battery_degradation_factor=self.battery_degradation_factor,
            active_shed_loads=active_shed,
        )

    def _build_default_loads(self) -> Dict[str, PowerLoadItem]:
        return {
            "LOAD-ECLSS": PowerLoadItem(
                load_id="LOAD-ECLSS",
                name="ECLSS Atmospheric Pressure & Oxygen Recirculation",
                priority=LoadPriority.CRITICAL_LIFE_SUPPORT,
                nominal_power_kw=18.5,
                duty_cycle=1.0,
            ),
            "LOAD-COMMS": PowerLoadItem(
                load_id="LOAD-COMMS",
                name="Telecom UHF/X-band Earth Uplink & Relay",
                priority=LoadPriority.PRIMARY_COMMS,
                nominal_power_kw=2.5,
                duty_cycle=1.0,
            ),
            "LOAD-THERMAL": PowerLoadItem(
                load_id="LOAD-THERMAL",
                name="Habitat Active Insulation & Trace Heaters",
                priority=LoadPriority.HABITAT_THERMAL,
                nominal_power_kw=14.0,
                duty_cycle=0.85,
            ),
            "LOAD-ISRU-WATER": PowerLoadItem(
                load_id="LOAD-ISRU-WATER",
                name="ISRU Subsurface Water Extraction Reactor",
                priority=LoadPriority.ISRU_PRODUCTION,
                nominal_power_kw=28.0,
                duty_cycle=0.75,
            ),
            "LOAD-ISRU-O2": PowerLoadItem(
                load_id="LOAD-ISRU-O2",
                name="ISRU Sabatier Methane & Oxygen Liquefaction",
                priority=LoadPriority.ISRU_PRODUCTION,
                nominal_power_kw=22.0,
                duty_cycle=0.70,
            ),
            "LOAD-SCIENCE": PowerLoadItem(
                load_id="LOAD-SCIENCE",
                name="Science Laboratory Mass Spectrometers & Glovebox",
                priority=LoadPriority.SCIENCE_LABORATORY,
                nominal_power_kw=12.0,
                duty_cycle=0.60,
            ),
            "LOAD-CONSTRUCT": PowerLoadItem(
                load_id="LOAD-CONSTRUCT",
                name="Autonomous Construction Robots & Mobile Cranes",
                priority=LoadPriority.ROBOTIC_CONSTRUCTION,
                nominal_power_kw=16.0,
                duty_cycle=0.50,
            ),
            "LOAD-ROVER-DEPOT": PowerLoadItem(
                load_id="LOAD-ROVER-DEPOT",
                name="Surface Mobility Fleet Inductive Charging Depot",
                priority=LoadPriority.ROVER_CHARGING_DEPOT,
                nominal_power_kw=15.0,
                duty_cycle=0.40,
            ),
        }
