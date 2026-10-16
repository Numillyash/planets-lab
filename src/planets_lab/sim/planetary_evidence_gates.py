"""Read-only joint-evidence gates for observed planetary stock balances.

This module deliberately does NOT infer mechanics or alter simulator state.
It joins four independently published Tminus1/T comparisons by exact
(game_id, turn, planet_id, owner_id, race_id), rejects incomplete pairings,
and keeps stock-balance residuals separate from causal Host explanations.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

FAMILIES=("supplies","taxes","minerals","populations")
EXACT="CONDITIONAL_EXACT_ALL_FIELDS"
MISMATCH="CONDITIONAL_MISMATCH_UNATTRIBUTED"
COMPARABLE=frozenset((EXACT,MISMATCH))
MINERALS=("neutronium","duranium","tritanium","molybdenum")
GROUND=tuple("ground"+mineral for mineral in MINERALS)
SHIP_CARGO=MINERALS
KEY=("game_id","turn","planet_id","owner_id","race_id")


def identity(row:Mapping[str,Any])->tuple[int,int,int,int,int|None]:
    fields=tuple(row.get(key) for key in KEY)
    if (any(type(x) is not int or x<=0 for x in fields[:4]) or
        (fields[4] is not None and (type(fields[4]) is not int or fields[4]<=0))):
        raise ValueError("missing or invalid source identity")
    return fields


def signed_residual(row:Mapping[str,Any],field:str)->int:
    """Observed T stock delta minus canonical conditional modeled T delta."""
    if row.get("status") not in COMPARABLE:
        raise ValueError("cannot score unqualified/abstained stock row")
    predicted=row.get("model_T",{})
    observed=row.get("archive_T",{})
    before=row.get("Tminus1",{})
    if not all(isinstance(x,Mapping) for x in (predicted,observed,before)):
        raise ValueError("missing frozen forecast/baseline/archive evidence")
    vals=(predicted.get(field),observed.get(field),before.get(field))
    if any(type(x) is not int or x<0 for x in vals):
        raise ValueError("invalid or absent comparable stock field")
    p,o,b=vals
    delta_p=row.get("delta_model",{}).get(field)
    delta_o=row.get("delta_archive",{}).get(field)
    if (type(delta_p) is not int or type(delta_o) is not int
        or delta_p!=p-b or delta_o!=o-b):
        raise ValueError("published stock deltas do not reconcile to frozen states")
    return o-p


def join_four(rows:Mapping[str,Sequence[Mapping[str,Any]]])->list[dict[str,Any]]:
    """Reject any missing, duplicated or non-aligned identity (no silent intersection)."""
    if set(rows)!=set(FAMILIES):
        raise ValueError("four full source report families required")
    indexed={}
    for family in FAMILIES:
        by_key={}
        for r in rows[family]:
            k=identity(r)
            if k in by_key:raise ValueError("duplicate planetary comparison identity")
            if r.get("family")!=family:
                raise ValueError("cross-family source label drift")
            by_key[k]=r
        indexed[family]=by_key
    keys=set(indexed[FAMILIES[0]])
    if any(set(indexed[family])!=keys for family in FAMILIES[1:]):
        raise ValueError("cross-family planet/time/owner coverage mismatch")
    result=[]
    for key in sorted(keys):
        source={name:indexed[name][key] for name in FAMILIES}
        statuses={name:source[name].get("status") for name in FAMILIES}
        comparable=all(status in COMPARABLE for status in statuses.values())
        if not comparable and any(status in COMPARABLE for status in statuses.values()):
            raise ValueError("mixed comparable and abstention source across same planet identity")
        if not comparable and len(set(statuses.values()))!=1:
            raise ValueError("inconsistent cross-family abstention cause")
        mark="".join("E" if statuses[name]==EXACT else
                     "M" if statuses[name]==MISMATCH else "A" for name in FAMILIES)
        delta={}
        if comparable:
            for name in FAMILIES:
                required={"supplies":("supplies",),"taxes":("megacredits",),
                          "minerals":MINERALS+GROUND,
                          "populations":("clans","nativeclans")}[name]
                delta[name]={field:signed_residual(source[name],field) for field in required}
                expected_exact=all(value==0 for value in delta[name].values())
                if (statuses[name]==EXACT)!=expected_exact:
                    raise ValueError("published exact/mismatch does not match stock residuals")
        result.append({
            "game_id":key[0],"turn":key[1],"planet_id":key[2],
            "owner_id":key[3],"race_id":key[4],
            "statuses":statuses,
            "signature":mark,
            "qualified":comparable,
            "Tminus1_to_T_unmodeled_external_orders_not_excluded":True,
            "signed_stock_residuals":delta,
            "causal_Host_formula_explanation_proven":False,
        })
    return result


def summarize_joint(joined:Sequence[Mapping[str,Any]])->dict[str,Any]:
    qualified=[r for r in joined if r["qualified"]]
    signatures=Counter(r["signature"] for r in qualified)
    if any(len(x)!=4 or set(x)-set("EM") for x in signatures):
        raise ValueError("invalid joint four-family signature")
    all_exact=[r for r in qualified if r["signature"]=="EEEE"]
    game_windows={(r["game_id"],r["turn"]) for r in joined}
    return {
        "all_source_planet_rows":len(joined),
        "qualified_four_family_planets":len(qualified),
        "abstained_four_family_planets":len(joined)-len(qualified),
        "four_family_conditional_exact":len(all_exact),
        "four_family_conditional_mismatch_at_least_one":len(qualified)-len(all_exact),
        "four_family_exact_game_turn_clusters":len({(r["game_id"],r["turn"]) for r in all_exact}),
        "source_game_turn_clusters":len(game_windows),
        "signature_counts":dict(sorted(signatures.items())),
        "mechanism_or_player_order_absence_proven":False,
    }


def summarize_resource(joined:Sequence[Mapping[str,Any]])->dict[str,Any]:
    q=[r for r in joined if r["qualified"]]
    quadrant=Counter()
    anomaly=Counter()
    supply=Counter()
    credits=Counter()
    ground_counts=Counter()
    surface_counts=Counter()
    for r in q:
        m=r["signed_stock_residuals"]["minerals"]
        surface=any(m[x]!=0 for x in MINERALS)
        underground=any(m[x]!=0 for x in GROUND)
        if surface and underground:quadrant["SURFACE_AND_GROUND_DEVIATE"]+=1
        elif surface:quadrant["SURFACE_ONLY_DEVIATES"]+=1
        elif underground:quadrant["GROUND_ONLY_DEVIATES"]+=1
        else:quadrant["ALL_EIGHT_MINERAL_FIELDS_EXACT"]+=1
        for field in MINERALS:
            if m[field]:surface_counts[field]+=1
        for field in GROUND:
            if m[field]:ground_counts[field]+=1
        d=r["signed_stock_residuals"]
        s=d["supplies"]["supplies"];t=d["taxes"]["megacredits"]
        supply[s]+=1;credits[t]+=1
        anomaly[("SUPPLIES_MISMATCH" if s else "SUPPLIES_EXACT")+"/"+
                ("MC_MISMATCH" if t else "MC_EXACT")]+=1
    return {
        "qualified_planets":len(q),
        "mineral_8_field_quadrants":dict(sorted(quadrant.items())),
        "surface_mineral_fields_different":dict(sorted(surface_counts.items())),
        "ground_mineral_fields_different":dict(sorted(ground_counts.items())),
        "supply_MC_cobehavior":dict(sorted(anomaly.items())),
        "common_supply_signed_residuals":top_residuals(supply),
        "common_MC_signed_residuals":top_residuals(credits),
        "stock_change_cause_attributed_to_player_actions":False,
        "ground_extraction_phase_proven":False,
    }


def summarize_population(joined:Sequence[Mapping[str,Any]])->dict[str,Any]:
    q=[r for r in joined if r["qualified"]]
    categories=Counter()
    clans=Counter()
    natives=Counter()
    for r in q:
        d=r["signed_stock_residuals"]["populations"]
        col=d["clans"];native=d["nativeclans"]
        clans[col]+=1;natives[native]+=1
        if col and native:categories["COLONIST_AND_NATIVE_DEVIATE"]+=1
        elif col:categories["COLONIST_ONLY_DEVIATES"]+=1
        elif native:categories["NATIVE_ONLY_DEVIATES"]+=1
        else:categories["BOTH_POPULATION_FIELDS_EXACT"]+=1
    return {
        "qualified_planets":len(q),
        "population_2_field_quadrants":dict(sorted(categories.items())),
        "common_colonist_signed_residuals":top_residuals(clans),
        "common_native_signed_residuals":top_residuals(natives),
        "observed_stock_delta_is_not_unique_growth_phase_evidence":True,
    }


def top_residuals(counts:Counter[int],max_values:int=12)->list[dict[str,int]]:
    if max_values<1:raise ValueError("max_values must be positive")
    return [{"signed_residual":value,"planet_rows":count}
            for value,count in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:max_values]]
