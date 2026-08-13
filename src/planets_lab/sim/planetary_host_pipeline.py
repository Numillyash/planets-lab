from __future__ import annotations

from dataclasses import dataclass, field

from planets_lab.sim.cyborg_assimilation_phase import CyborgAssimilationPhase
from planets_lab.sim.engine import HostEngine, HostPhase
from planets_lab.sim.factory_supply_phase import FactorySupplyPhase
from planets_lab.sim.mineral_phases import MineralMiningPhase, TransUraniumMutationPhase
from planets_lab.sim.population_phases import (
    ColonistGrowthPhase,
    ColonistHappinessPhase,
    ColonistOverpopulationPhase,
)
from planets_lab.sim.society_phases import (
    AmorphousConsumptionPhase,
    CivilWarPhase,
    NativeGrowthPhase,
    NativeHappinessPhase,
    RiotsPhase,
    StructureDecayPhase,
)
from planets_lab.sim.tax_collection_phase import TaxCollectionPhase


PLANETARY_HOST_PHASE_ORDER = (
    "structure_decay",
    "colonist_happiness",
    "native_happiness",
    "factory_supplies",
    "tax_collection",
    "cyborg_assimilation",
    "colonist_growth",
    "native_growth",
    "colonist_overpopulation",
    "amorphous_consumption",
    "riots",
    "civil_war",
    "mineral_mining",
    "trans_uranium_mutation",
)


@dataclass(slots=True)
class PlanetaryHostPipeline:
    """Canonical order for the planetary Host mechanics currently implemented.

    The surrounding NuHost block also contains mechanics that are deliberately
    not simulated yet: Terraforming, Pillage/Plunder, Rebel Ground Attack,
    Campaign Enlighten, and Campaign Ore Condensing.  Keeping those omissions
    explicit prevents this pipeline from implying unsupported behaviour while
    preserving the documented relative order of every implemented phase.
    """

    structure_decay: StructureDecayPhase = field(default_factory=StructureDecayPhase)
    colonist_happiness: ColonistHappinessPhase = field(default_factory=ColonistHappinessPhase)
    native_happiness: NativeHappinessPhase = field(default_factory=NativeHappinessPhase)
    factory_supplies: FactorySupplyPhase = field(default_factory=FactorySupplyPhase)
    tax_collection: TaxCollectionPhase = field(default_factory=TaxCollectionPhase)
    cyborg_assimilation: CyborgAssimilationPhase = field(default_factory=CyborgAssimilationPhase)
    colonist_growth: ColonistGrowthPhase = field(default_factory=ColonistGrowthPhase)
    native_growth: NativeGrowthPhase = field(default_factory=NativeGrowthPhase)
    colonist_overpopulation: ColonistOverpopulationPhase = field(
        default_factory=ColonistOverpopulationPhase
    )
    amorphous_consumption: AmorphousConsumptionPhase = field(
        default_factory=AmorphousConsumptionPhase
    )
    riots: RiotsPhase = field(default_factory=RiotsPhase)
    civil_war: CivilWarPhase = field(default_factory=CivilWarPhase)
    mineral_mining: MineralMiningPhase = field(default_factory=MineralMiningPhase)
    trans_uranium_mutation: TransUraniumMutationPhase = field(
        default_factory=TransUraniumMutationPhase
    )

    @property
    def phases(self) -> tuple[HostPhase, ...]:
        phases: tuple[HostPhase, ...] = (
            self.structure_decay,
            self.colonist_happiness,
            self.native_happiness,
            self.factory_supplies,
            self.tax_collection,
            self.cyborg_assimilation,
            self.colonist_growth,
            self.native_growth,
            self.colonist_overpopulation,
            self.amorphous_consumption,
            self.riots,
            self.civil_war,
            self.mineral_mining,
            self.trans_uranium_mutation,
        )
        return phases

    def engine(self) -> HostEngine:
        return HostEngine(self.phases)
