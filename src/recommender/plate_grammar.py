"""
plate_grammar.py

Domain plate grammar assembly for Indian hostel dining.
Defines required and optional plate roles for Breakfast, Lunch, E-Tea, and Dinner.
Generates combinatorial candidate plates with explicit fallback handling for depleted pools.
"""

from dataclasses import dataclass, field
from itertools import product
from typing import List, Dict, Any, Optional


SLOT_GRAMMAR = {
    "BREAKFAST": {
        "primary_roles": [["STAPLE", "SNACK"]],
        "optional_roles": ["BEVERAGE", "ACCOMPANIMENT"],
        "max_dishes": 3
    },
    "LUNCH": {
        "primary_roles": [["STAPLE"], ["DAL_PROTEIN"]],
        "optional_roles": ["DRY_SABZI", "GRAVY_SABZI", "ACCOMPANIMENT"],
        "max_dishes": 4
    },
    "DINNER": {
        "primary_roles": [["STAPLE"], ["DAL_PROTEIN"]],
        "optional_roles": ["DRY_SABZI", "GRAVY_SABZI", "ACCOMPANIMENT", "DESSERT"],
        "max_dishes": 4
    },
    "E_TEA": {
        "primary_roles": [["SNACK", "BEVERAGE", "STAPLE"]],
        "optional_roles": ["BEVERAGE", "ACCOMPANIMENT"],
        "max_dishes": 2
    }
}


@dataclass
class AssemblyResult:
    success: bool
    plates: List[List[Dict[str, Any]]] = field(default_factory=list)
    status_code: str = "SUCCESS"
    diagnostic_message: str = "Candidate plates assembled successfully"


def assemble_candidate_plates(
    slot: str,
    available_dishes: List[Dict[str, Any]]
) -> AssemblyResult:
    """
    Assembles grammatically sound plate combinations from filtered available dishes.
    If constraints deplete dishes so that required roles cannot be filled, returns
    a graceful AssemblyResult with status NO_VALID_COMBINATION rather than crashing.
    """
    norm_slot = str(slot).strip().upper()
    if norm_slot not in SLOT_GRAMMAR:
        return AssemblyResult(
            success=False,
            status_code="INVALID_SLOT",
            diagnostic_message=f"Unknown operational meal slot: {norm_slot}"
        )

    if not available_dishes:
        return AssemblyResult(
            success=False,
            status_code="NO_VALID_COMBINATION",
            diagnostic_message=f"Candidate pool is empty for {norm_slot}. All menu items were filtered by constraints."
        )

    grammar = SLOT_GRAMMAR[norm_slot]
    dishes_by_role: Dict[str, List[Dict[str, Any]]] = {}
    for d in available_dishes:
        role = d.get("plate_role", "ACCOMPANIMENT")
        dishes_by_role.setdefault(role, []).append(d)

    # Check if every primary role group has at least one candidate available
    primary_pools: List[List[Dict[str, Any]]] = []
    for role_options in grammar["primary_roles"]:
        pool = []
        for r in role_options:
            pool.extend(dishes_by_role.get(r, []))
        if not pool:
            missing_roles = " / ".join(role_options)
            return AssemblyResult(
                success=False,
                status_code="NO_VALID_COMBINATION",
                diagnostic_message=(
                    f"Grammar assembly failed for {norm_slot}: Missing required primary role [{missing_roles}]. "
                    f"Available roles: {list(dishes_by_role.keys())}."
                )
            )
        primary_pools.append(pool)

    # Assemble core combinations from primary roles
    core_combos = list(product(*primary_pools))

    # Deduplicate within combinations
    valid_plates: List[List[Dict[str, Any]]] = []
    seen_plates = set()

    # Complementary options
    comp_pool = []
    for r in grammar["optional_roles"]:
        comp_pool.extend(dishes_by_role.get(r, []))

    for core in core_combos:
        core_dishes = list(core)
        core_names = tuple(sorted(d["canonical_dish"] for d in core_dishes))
        if len(set(core_names)) != len(core_names):
            continue  # duplicate dish in core

        if core_names not in seen_plates:
            seen_plates.add(core_names)
            valid_plates.append(core_dishes)

        # Also form 1-item optional additions if budget/room permits
        for comp in comp_pool:
            if comp["canonical_dish"] in core_names:
                continue
            combo = tuple(sorted(list(core_names) + [comp["canonical_dish"]]))
            if combo not in seen_plates and len(combo) <= grammar["max_dishes"]:
                seen_plates.add(combo)
                valid_plates.append(core_dishes + [comp])

    if not valid_plates:
        return AssemblyResult(
            success=False,
            status_code="NO_VALID_COMBINATION",
            diagnostic_message=f"No valid non-duplicate plate combinations could be formed for {norm_slot}."
        )

    return AssemblyResult(
        success=True,
        plates=valid_plates,
        status_code="SUCCESS",
        diagnostic_message=f"Assembled {len(valid_plates)} valid plate combinations for {norm_slot}."
    )
