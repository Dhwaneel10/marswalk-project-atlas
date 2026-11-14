"""MarsWalk 2.0 / Project Atlas  Milestone 13S: In-Situ Resource Utilization (ISRU) Engine.

Models subsurface water extraction, atmospheric CO2 electrolysis (MOXIE),
catalytic Sabatier methane/oxygen synthesis, regolith sintering, and enforces
strict closed mass-balance conservation: m_inputs = m_products + m_waste + m_losses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ISRUProcessType(str, Enum):
    """Core planetary commodity conversion pathways."""
    WATER_EXTRACTION = "WATER_EXTRACTION"        # Thermal sublimation of hydrated clays/pore ice
    ATMOSPHERIC_OXYGEN = "ATMOSPHERIC_OXYGEN"    # Solid oxide electrolysis of ambient CO2 (2 CO2 -> 2 CO + O2)
    SABATIER_METHANATION = "SABATIER_METHANATION"# Catalytic methanation (CO2 + 4 H2 -> CH4 + 2 H2O)
    WATER_ELECTROLYSIS = "WATER_ELECTROLYSIS"    # Splitting water (2 H2O -> 2 H2 + O2)
    REGOLITH_SINTERING = "REGOLITH_SINTERING"    # Microwave/thermal sintering of regolith for berms/paving


@dataclass
class MassBalanceAudit:
    """Formal mass conservation record for an ISRU conversion process."""
    process_type: ISRUProcessType
    total_inputs_kg: float
    total_products_kg: float
    total_waste_kg: float
    total_losses_kg: float
    imbalance_residual_kg: float
    energy_consumed_kwh: float
    is_conserved: bool                       # True if |imbalance| < 1e-4 kg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_type": self.process_type.value,
            "total_inputs_kg": round(self.total_inputs_kg, 4),
            "total_products_kg": round(self.total_products_kg, 4),
            "total_waste_kg": round(self.total_waste_kg, 4),
            "total_losses_kg": round(self.total_losses_kg, 4),
            "imbalance_residual_kg": round(self.imbalance_residual_kg, 6),
            "energy_consumed_kwh": round(self.energy_consumed_kwh, 3),
            "is_conserved": self.is_conserved,
        }


@dataclass
class ResourceStorageInventories:
    """Live stored inventories of local commodities."""
    water_h2o_kg: float = 1200.0
    liquid_oxygen_o2_kg: float = 850.0
    liquid_methane_ch4_kg: float = 240.0
    hydrogen_h2_kg: float = 65.0             # Precious feedstock; must never appear from thin air
    carbon_dioxide_co2_kg: float = 450.0
    sintered_regolith_blocks_kg: float = 8500.0
    raw_excavated_regolith_kg: float = 12500.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "water_h2o_kg": round(self.water_h2o_kg, 2),
            "liquid_oxygen_o2_kg": round(self.liquid_oxygen_o2_kg, 2),
            "liquid_methane_ch4_kg": round(self.liquid_methane_ch4_kg, 2),
            "hydrogen_h2_kg": round(self.hydrogen_h2_kg, 2),
            "carbon_dioxide_co2_kg": round(self.carbon_dioxide_co2_kg, 2),
            "sintered_regolith_blocks_kg": round(self.sintered_regolith_blocks_kg, 1),
            "raw_excavated_regolith_kg": round(self.raw_excavated_regolith_kg, 1),
        }


class ISRUEngine:
    """Planetary chemical processing and resource conversion engine."""

    def __init__(self, initial_inventories: Optional[ResourceStorageInventories] = None):
        self.inventories: ResourceStorageInventories = initial_inventories or ResourceStorageInventories()
        self._audit_log: List[MassBalanceAudit] = []

    def extract_water_from_regolith(
        self,
        excavated_feedstock_kg: float,
        water_wt_pct: float = 7.0,
        thermal_efficiency: float = 0.88,
        purification_loss_pct: float = 4.5,
    ) -> MassBalanceAudit:
        """Extracts potable H2O via thermal auger sublimation of hydrated phyllosilicates.

        Inputs: raw excavated regolith.
        Products: purified water H2O.
        Waste: dry spent regolith tailings + perchlorate/sulfate sludge.
        Losses: vapor leakage / condenser unrecovered fraction.
        """
        # Mass balance calculation
        theoretical_water_kg = excavated_feedstock_kg * (water_wt_pct / 100.0)
        dry_tailings_kg = excavated_feedstock_kg - theoretical_water_kg

        sublimated_water_kg = theoretical_water_kg * thermal_efficiency
        thermal_vapor_loss_kg = theoretical_water_kg * (1.0 - thermal_efficiency)

        purified_water_kg = sublimated_water_kg * (1.0 - purification_loss_pct / 100.0)
        purification_waste_kg = sublimated_water_kg * (purification_loss_pct / 100.0)

        total_products = purified_water_kg
        total_waste = dry_tailings_kg + purification_waste_kg
        total_losses = thermal_vapor_loss_kg

        # Conservation check: inputs == products + waste + losses
        residual = excavated_feedstock_kg - (total_products + total_waste + total_losses)
        is_conserved = abs(residual) < 1e-4

        # Specific thermal energy: ~1.85 kWh per kg water produced
        energy_kwh = purified_water_kg * 1.85

        # Update inventory
        self.inventories.water_h2o_kg += purified_water_kg
        self.inventories.raw_excavated_regolith_kg = max(0.0, self.inventories.raw_excavated_regolith_kg - excavated_feedstock_kg)

        audit = MassBalanceAudit(
            process_type=ISRUProcessType.WATER_EXTRACTION,
            total_inputs_kg=excavated_feedstock_kg,
            total_products_kg=total_products,
            total_waste_kg=total_waste,
            total_losses_kg=total_losses,
            imbalance_residual_kg=residual,
            energy_consumed_kwh=energy_kwh,
            is_conserved=is_conserved,
        )
        self._audit_log.append(audit)
        return audit

    def generate_atmospheric_oxygen(
        self,
        co2_intake_kg: float,
        electrolysis_conversion_pct: float = 42.0, # 2 CO2 -> 2 CO + O2 (Theoretical max yield by mass is ~36.4%)
    ) -> MassBalanceAudit:
        """Solid oxide electrolysis (SOXE) splitting atmospheric CO2 into breathable O2 and CO waste.

        2 CO2 (88 g/mol) -> 2 CO (56 g/mol) + O2 (32 g/mol)
        Yield: 32 / 88 = 0.3636 kg O2 per kg converted CO2.
        """
        # Compressor seal leakage (0.5% unreacted loss prior to electrolysis)
        compressor_loss_kg = co2_intake_kg * 0.005
        co2_entering_cell_kg = co2_intake_kg - compressor_loss_kg

        co2_reacted_kg = co2_entering_cell_kg * (electrolysis_conversion_pct / 100.0)
        unreacted_co2_kg = co2_entering_cell_kg - co2_reacted_kg

        produced_o2_kg = co2_reacted_kg * (32.0 / 88.0)
        produced_co_kg = co2_reacted_kg * (56.0 / 88.0)

        produced_o2_net_kg = produced_o2_kg * 0.995
        o2_vent_loss_kg = produced_o2_kg * 0.005

        total_products = produced_o2_net_kg
        total_waste = produced_co_kg + unreacted_co2_kg
        total_losses = compressor_loss_kg + o2_vent_loss_kg

        residual = co2_intake_kg - (total_products + total_waste + total_losses)
        is_conserved = abs(residual) < 1e-4

        # Electrical energy: ~4.2 kWh per kg O2 (MOXIE scaling)
        energy_kwh = produced_o2_net_kg * 4.2

        self.inventories.liquid_oxygen_o2_kg += produced_o2_net_kg

        audit = MassBalanceAudit(
            process_type=ISRUProcessType.ATMOSPHERIC_OXYGEN,
            total_inputs_kg=co2_intake_kg,
            total_products_kg=total_products,
            total_waste_kg=total_waste,
            total_losses_kg=total_losses,
            imbalance_residual_kg=residual,
            energy_consumed_kwh=energy_kwh,
            is_conserved=is_conserved,
        )
        self._audit_log.append(audit)
        return audit

    def synthesize_sabatier_methane(
        self,
        co2_input_kg: float,
        h2_input_kg: float,
        conversion_efficiency: float = 0.95,
    ) -> MassBalanceAudit:
        """Catalytic Sabatier reaction: CO2 + 4 H2 -> CH4 + 2 H2O.

        Stoichiometry:
        CO2 (44 g/mol) + 4 H2 (8 g/mol) = 52 g/mol reactants
        -> CH4 (16 g/mol) + 2 H2O (36 g/mol) = 52 g/mol products
        Ratio: 44 kg CO2 requires 8 kg H2 (5.5:1 mass ratio).
        """
        # Determine limiting reagent
        required_h2_for_co2 = co2_input_kg * (8.0 / 44.0)

        if h2_input_kg < required_h2_for_co2:
            # Hydrogen limited
            h2_reacted = h2_input_kg * conversion_efficiency
            co2_reacted = (h2_reacted * 44.0) / 8.0
            excess_co2 = co2_input_kg - co2_reacted
            excess_h2 = h2_input_kg - h2_reacted
        else:
            # CO2 limited
            co2_reacted = co2_input_kg * conversion_efficiency
            h2_reacted = (co2_reacted * 8.0) / 44.0
            excess_co2 = co2_input_kg - co2_reacted
            excess_h2 = h2_input_kg - h2_reacted

        produced_ch4_kg = co2_reacted * (16.0 / 44.0)
        produced_h2o_kg = co2_reacted * (36.0 / 44.0)

        total_inputs = co2_input_kg + h2_input_kg
        total_products = produced_ch4_kg + produced_h2o_kg
        total_waste = excess_co2 + excess_h2
        total_losses = 0.0  # Sealed reactor vessel

        residual = total_inputs - (total_products + total_waste + total_losses)
        is_conserved = abs(residual) < 1e-4

        # Sabatier is exothermic, but condenser and preheater consume ~1.2 kWh/kg CH4
        energy_kwh = produced_ch4_kg * 1.20

        # Update inventory
        self.inventories.hydrogen_h2_kg = max(0.0, self.inventories.hydrogen_h2_kg - h2_reacted)
        self.inventories.liquid_methane_ch4_kg += produced_ch4_kg
        self.inventories.water_h2o_kg += produced_h2o_kg

        audit = MassBalanceAudit(
            process_type=ISRUProcessType.SABATIER_METHANATION,
            total_inputs_kg=total_inputs,
            total_products_kg=total_products,
            total_waste_kg=total_waste,
            total_losses_kg=total_losses,
            imbalance_residual_kg=residual,
            energy_consumed_kwh=energy_kwh,
            is_conserved=is_conserved,
        )
        self._audit_log.append(audit)
        return audit

    def sinter_regolith_blocks(
        self,
        raw_regolith_kg: float,
        sintering_efficiency: float = 0.94,
    ) -> MassBalanceAudit:
        """Microwave/thermal sintering of basaltic regolith for radiation berms and landing pads.

        Volatiles (adsorbed H2O, CO2) are driven off during heating.
        """
        volatiles_mass_kg = raw_regolith_kg * 0.04
        dense_solid_mass_kg = raw_regolith_kg - volatiles_mass_kg

        usable_blocks_kg = dense_solid_mass_kg * sintering_efficiency
        spallation_waste_kg = dense_solid_mass_kg * (1.0 - sintering_efficiency)

        total_products = usable_blocks_kg
        total_waste = spallation_waste_kg + volatiles_mass_kg
        total_losses = 0.0

        residual = raw_regolith_kg - (total_products + total_waste + total_losses)
        is_conserved = abs(residual) < 1e-4

        # Sintering specific energy: ~0.65 kWh per kg solid block
        energy_kwh = usable_blocks_kg * 0.65

        self.inventories.sintered_regolith_blocks_kg += usable_blocks_kg
        self.inventories.raw_excavated_regolith_kg = max(0.0, self.inventories.raw_excavated_regolith_kg - raw_regolith_kg)

        audit = MassBalanceAudit(
            process_type=ISRUProcessType.REGOLITH_SINTERING,
            total_inputs_kg=raw_regolith_kg,
            total_products_kg=total_products,
            total_waste_kg=total_waste,
            total_losses_kg=total_losses,
            imbalance_residual_kg=residual,
            energy_consumed_kwh=energy_kwh,
            is_conserved=is_conserved,
        )
        self._audit_log.append(audit)
        return audit

    def get_recent_audits(self) -> List[MassBalanceAudit]:
        return list(self._audit_log)
