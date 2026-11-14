"""MarsWalk 2.0 / Project Atlas  Milestone 13S: Habitat & Thermal Digital Twin.

Models surface habitat module geometry, thermal networks (dU/dt = Q_in - Q_out),
internal atmospheric pressure differentials, and regolith radiation shielding
attenuation with explicit scientific fidelity boundaries.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class HabitatModuleType(str, Enum):
    """Functional categorization of surface habitat units."""
    CREW_QUARTERS = "CREW_QUARTERS"              # Berthing, personal stowage, hygiene
    LABORATORY = "LABORATORY"                    # Analytical chemistry, microscopy, glovebox
    MEDICAL_BAY = "MEDICAL_BAY"                  # Telemedicine, trauma stabilization, research
    STORAGE_LOGISTICS = "STORAGE_LOGISTICS"      # Dry rations, spare parts, consumables
    POWER_ENCLOSURE = "POWER_ENCLOSURE"          # PDU, inverters, backup batteries
    GREENHOUSE_DEMO = "GREENHOUSE_DEMO"          # Hydroponic crop research chamber
    WORKSHOP = "WORKSHOP"                        # 3D printer, robotic maintenance tools
    AIRLOCK_SUITLOCK = "AIRLOCK_SUITLOCK"        # Dual-chamber dust mitigation egress
    UTILITY_HUB = "UTILITY_HUB"                  # Central piping, manifold, data switch


class ShieldingType(str, Enum):
    """Regolith and passive radiation protection configurations."""
    UNSHIELDED_BARE_SHELL = "UNSHIELDED_BARE_SHELL"  # Bare inflatable kevlar/mylar pressure vessel
    REGOLITH_BERM_1M = "REGOLITH_BERM_1M"            # 1.0m uncompacted regolith cover
    SINTERED_ARCH_2M = "SINTERED_ARCH_2M"            # 2.0m dense sintered regolith vault
    WATER_WALL_COMPOSITE = "WATER_WALL_COMPOSITE"    # Polyethylene bladder backed by potable H2O jacket


@dataclass
class HabitatModuleSpec:
    """Engineering physical specification of an individual habitat shell."""
    module_id: str
    name: str
    module_type: HabitatModuleType
    diameter_m: float
    length_m: float
    internal_volume_m3: float
    shell_surface_area_m2: float
    structural_mass_kg: float
    internal_pressure_kpa: float             # 56.5 kPa (8.2 psi NASA exploration atmosphere)
    design_temperature_c: float = 21.0       # Nominal internal shirt-sleeve temperature
    current_temperature_c: float = 20.5
    internal_heat_gen_kw: float = 3.5        # Electronics, pumps, lighting, metabolic
    insulation_u_value_w_m2k: float = 0.18   # Aerogel blanket thermal conductance
    shielding: ShieldingType = ShieldingType.REGOLITH_BERM_1M

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "name": self.name,
            "module_type": self.module_type.value,
            "diameter_m": round(self.diameter_m, 2),
            "length_m": round(self.length_m, 2),
            "internal_volume_m3": round(self.internal_volume_m3, 1),
            "shell_surface_area_m2": round(self.shell_surface_area_m2, 1),
            "structural_mass_kg": round(self.structural_mass_kg, 1),
            "internal_pressure_kpa": round(self.internal_pressure_kpa, 1),
            "design_temperature_c": round(self.design_temperature_c, 1),
            "current_temperature_c": round(self.current_temperature_c, 2),
            "internal_heat_gen_kw": round(self.internal_heat_gen_kw, 2),
            "insulation_u_value_w_m2k": round(self.insulation_u_value_w_m2k, 3),
            "shielding": self.shielding.value,
        }


@dataclass
class HabitatThermalTelemetry:
    """Thermal energy balance snapshot for a habitat module."""
    module_id: str
    external_ambient_temp_c: float
    internal_temp_c: float
    q_solar_in_kw: float
    q_internal_gen_kw: float
    q_conduction_loss_kw: float
    q_radiation_loss_kw: float
    q_active_heating_required_kw: float
    q_active_cooling_required_kw: float
    pressure_differential_kpa: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "external_ambient_temp_c": round(self.external_ambient_temp_c, 1),
            "internal_temp_c": round(self.internal_temp_c, 2),
            "q_solar_in_kw": round(self.q_solar_in_kw, 3),
            "q_internal_gen_kw": round(self.q_internal_gen_kw, 3),
            "q_conduction_loss_kw": round(self.q_conduction_loss_kw, 3),
            "q_radiation_loss_kw": round(self.q_radiation_loss_kw, 3),
            "q_active_heating_required_kw": round(self.q_active_heating_required_kw, 3),
            "q_active_cooling_required_kw": round(self.q_active_cooling_required_kw, 3),
            "pressure_differential_kpa": round(self.pressure_differential_kpa, 2),
        }


class HabitatThermalNetwork:
    """Simulates multi-node conductive, radiative, and metabolic energy balances."""

    def __init__(self, modules: Optional[List[HabitatModuleSpec]] = None):
        self.modules: Dict[str, HabitatModuleSpec] = {m.module_id: m for m in (modules or self._build_default_cluster())}

    def evaluate_thermal_step(
        self,
        ambient_temp_c: float = -65.0,
        solar_flux_wm2: float = 350.0,
        dt_s: float = 3600.0,
    ) -> List[HabitatThermalTelemetry]:
        """Calculates instantaneous heat flows and updates internal temperatures."""
        results: List[HabitatThermalTelemetry] = []
        stefan_boltzmann = 5.670374e-8 # W / (m^2 * K^4)
        ambient_k = ambient_temp_c + 273.15

        for mod in self.modules.values():
            internal_k = mod.current_temperature_c + 273.15
            delta_t = internal_k - ambient_k

            # Solar absorption on exposed roof (attenuated by regolith shielding if present)
            shielding_mult = 0.05 if "REGOLITH" in mod.shielding.value else 0.85
            exposed_area = mod.shell_surface_area_m2 * 0.40
            q_solar_kw = (exposed_area * solar_flux_wm2 * 0.70 * shielding_mult) / 1000.0

            # Internal heat generation (constant baseline from computers & crew)
            q_internal_kw = mod.internal_heat_gen_kw

            # Conductive heat loss through walls & floor
            effective_u = mod.insulation_u_value_w_m2k
            if mod.shielding == ShieldingType.REGOLITH_BERM_1M:
                effective_u *= 0.45 # Extra 1m regolith insulation
            elif mod.shielding == ShieldingType.SINTERED_ARCH_2M:
                effective_u *= 0.25 # 2m sintered arch insulation

            q_conduction_kw = (mod.shell_surface_area_m2 * effective_u * delta_t) / 1000.0

            # Radiative heat loss to Mars cold sky (~180 K)
            sky_temp_k = 185.0
            emissivity = 0.85 * shielding_mult
            q_radiation_kw = (emissivity * stefan_boltzmann * exposed_area * (internal_k**4 - sky_temp_k**4)) / 1000.0

            # Net passive heat balance
            net_heat_flow_kw = (q_solar_kw + q_internal_kw) - (q_conduction_kw + q_radiation_kw)

            # Active HVAC control (maintain between 19C and 22C)
            heating_req_kw = 0.0
            cooling_req_kw = 0.0

            if net_heat_flow_kw < 0.0:
                # Habitat is cooling down -> heater required
                heating_req_kw = abs(net_heat_flow_kw)
                heat_supplied_kw = heating_req_kw
            else:
                # Habitat is heating up -> heat rejection cooling required
                cooling_req_kw = net_heat_flow_kw
                heat_supplied_kw = -cooling_req_kw

            # Effective temperature update
            # Air thermal capacity: ~1.2 kJ/(m^3*K) * Volume
            air_heat_capacity_kj_k = 1.2 * mod.internal_volume_m3
            unbalanced_kw = net_heat_flow_kw + (heating_req_kw - cooling_req_kw)
            delta_temp = (unbalanced_kw * dt_s) / max(1.0, air_heat_capacity_kj_k)

            mod.current_temperature_c += delta_temp
            # Clamp to physical range
            mod.current_temperature_c = max(-40.0, min(35.0, mod.current_temperature_c))

            pressure_diff = mod.internal_pressure_kpa - 0.61 # Mars atmospheric pressure ~0.61 kPa

            results.append(HabitatThermalTelemetry(
                module_id=mod.module_id,
                external_ambient_temp_c=ambient_temp_c,
                internal_temp_c=mod.current_temperature_c,
                q_solar_in_kw=q_solar_kw,
                q_internal_gen_kw=q_internal_kw,
                q_conduction_loss_kw=q_conduction_kw,
                q_radiation_loss_kw=q_radiation_kw,
                q_active_heating_required_kw=heating_req_kw,
                q_active_cooling_required_kw=cooling_req_kw,
                pressure_differential_kpa=pressure_diff,
            ))

        return results

    def _build_default_cluster(self) -> List[HabitatModuleSpec]:
        return [
            HabitatModuleSpec(
                module_id="HAB-CREW-01",
                name="Primary Crew Habitation & Berthing Node",
                module_type=HabitatModuleType.CREW_QUARTERS,
                diameter_m=6.5,
                length_m=8.5,
                internal_volume_m3=280.0,
                shell_surface_area_m2=210.0,
                structural_mass_kg=12500.0,
                internal_pressure_kpa=56.5,
                design_temperature_c=21.0,
                current_temperature_c=21.0,
                internal_heat_gen_kw=3.8,
                insulation_u_value_w_m2k=0.16,
                shielding=ShieldingType.REGOLITH_BERM_1M,
            ),
            HabitatModuleSpec(
                module_id="HAB-LAB-01",
                name="Astrobiology & Analytical Chemistry Laboratory",
                module_type=HabitatModuleType.LABORATORY,
                diameter_m=5.0,
                length_m=7.0,
                internal_volume_m3=135.0,
                shell_surface_area_m2=130.0,
                structural_mass_kg=8500.0,
                internal_pressure_kpa=56.5,
                design_temperature_c=20.0,
                current_temperature_c=20.0,
                internal_heat_gen_kw=5.2, # High analytical electronics load
                insulation_u_value_w_m2k=0.18,
                shielding=ShieldingType.SINTERED_ARCH_2M,
            ),
            HabitatModuleSpec(
                module_id="HAB-LOGISTICS-01",
                name="Consumables Stowage & Maintenance Workshop",
                module_type=HabitatModuleType.STORAGE_LOGISTICS,
                diameter_m=5.0,
                length_m=9.0,
                internal_volume_m3=175.0,
                shell_surface_area_m2=160.0,
                structural_mass_kg=9200.0,
                internal_pressure_kpa=56.5,
                design_temperature_c=16.0, # Cooler storage zone
                current_temperature_c=16.0,
                internal_heat_gen_kw=1.8,
                insulation_u_value_w_m2k=0.20,
                shielding=ShieldingType.REGOLITH_BERM_1M,
            ),
        ]
