"""Model Pyomo terbuka untuk peran matematis Latihan 3.1--3.9.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

from pyomo.environ import (
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Objective,
    RangeSet,
    Reals,
    Set,
    SolverFactory,
    Suffix,
    Var,
    maximize,
    minimize,
    value,
)
from pyomo.opt import SolverStatus, TerminationCondition


TOLERANCE = 1e-7
EXERCISE_IDS = tuple(f"3.{index}" for index in range(1, 10))


def load_data(path: Path) -> dict[str, Any]:
    """Membaca data dan menolak kontrak yang tidak lengkap atau berubah domain."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != "o018.ch03.spreadsheet-replacements":
        raise ValueError("lab_id tidak sesuai kontrak")
    exercises = data.get("exercises")
    if not isinstance(exercises, dict) or tuple(sorted(exercises)) != EXERCISE_IDS:
        raise ValueError("data harus memuat tepat Latihan 3.1--3.9")
    for exercise_id in ("3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7"):
        if exercises[exercise_id].get("domain") != "NonNegativeReals":
            raise ValueError(f"domain {exercise_id} harus NonNegativeReals")
    modes = exercises["3.9"].get("modes", {})
    if modes.get("nonnegative_checkbox_on", {}).get("A_domain") != "NonNegativeReals":
        raise ValueError("mode checkbox aktif harus membatasi A nonnegatif")
    if modes.get("nonnegative_checkbox_off", {}).get("A_domain") != "Reals":
        raise ValueError("mode checkbox nonaktif harus membebaskan A")
    return data


def _clean(number: float) -> float:
    number = float(number)
    if abs(number) <= 1e-10:
        return 0.0
    return round(number, 10)


def _maximum_violation(model: ConcreteModel) -> float:
    violation = 0.0
    for variable in model.component_data_objects(Var, active=True):
        current = float(value(variable))
        if variable.lb is not None:
            violation = max(violation, float(value(variable.lb)) - current)
        if variable.ub is not None:
            violation = max(violation, current - float(value(variable.ub)))
    for constraint in model.component_data_objects(Constraint, active=True):
        body = float(value(constraint.body))
        if constraint.lower is not None:
            violation = max(violation, float(value(constraint.lower)) - body)
        if constraint.upper is not None:
            violation = max(violation, body - float(value(constraint.upper)))
    return max(0.0, violation)


def _solve(model: ConcreteModel) -> dict[str, Any]:
    solver = SolverFactory("appsi_highs")
    if not solver.available(exception_flag=False):
        raise RuntimeError("pemecah appsi_highs tidak tersedia")
    solver.options["output_flag"] = False
    result = solver.solve(model, tee=False)
    if result.solver.status not in {SolverStatus.ok, SolverStatus.warning}:
        raise RuntimeError(f"status pemecah tidak diterima: {result.solver.status}")
    if result.solver.termination_condition != TerminationCondition.optimal:
        raise RuntimeError(
            "model tidak berhenti pada optimum: "
            f"{result.solver.termination_condition}"
        )
    maximum_violation = _maximum_violation(model)
    if maximum_violation > TOLERANCE:
        raise RuntimeError(f"pelanggaran kelayakan {maximum_violation} melebihi toleransi")
    return {
        "maximum_violation": _clean(maximum_violation),
        "solver": "appsi_highs",
        "status": str(result.solver.status),
        "termination_condition": str(result.solver.termination_condition),
    }


def _dual(model: ConcreteModel, constraint: Any) -> float:
    try:
        return _clean(model.dual[constraint])
    except KeyError as error:
        raise RuntimeError(f"dual tidak dimuat untuk {constraint.name}") from error


def _reduced_cost(model: ConcreteModel, variable: Any) -> float:
    try:
        return _clean(model.rc[variable])
    except KeyError as error:
        raise RuntimeError(f"reduced cost tidak dimuat untuk {variable.name}") from error


def build_exercise_3_1(spec: dict[str, Any]) -> ConcreteModel:
    warehouses = tuple(spec["supply"])
    stores = tuple(spec["demand"])
    model = ConcreteModel(name="exercise_3_1_min_cost_network")
    model.W = Set(initialize=warehouses, ordered=True)
    model.S = Set(initialize=stores, ordered=True)
    model.flow = Var(
        model.W,
        model.S,
        domain=NonNegativeReals,
        bounds=lambda _, warehouse, store: (
            0.0,
            float(spec["route_capacity"][warehouse][store]),
        ),
    )
    model.supply = Constraint(
        model.W,
        rule=lambda current, warehouse: sum(
            current.flow[warehouse, store] for store in current.S
        )
        <= float(spec["supply"][warehouse]),
    )
    model.demand = Constraint(
        model.S,
        rule=lambda current, store: sum(
            current.flow[warehouse, store] for warehouse in current.W
        )
        == float(spec["demand"][store]),
    )
    model.objective = Objective(
        expr=sum(
            float(spec["cost"][warehouse][store]) * model.flow[warehouse, store]
            for warehouse in model.W
            for store in model.S
        ),
        sense=minimize,
    )
    return model


def solve_exercise_3_1(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_exercise_3_1(spec)
    execution = _solve(model)
    route_flow = {
        f"{warehouse}-{store}": _clean(value(model.flow[warehouse, store]))
        for warehouse in model.W
        for store in model.S
    }
    saturated_routes = [
        f"{warehouse}-{store}"
        for warehouse in model.W
        for store in model.S
        if abs(
            route_flow[f"{warehouse}-{store}"]
            - float(spec["route_capacity"][warehouse][store])
        )
        <= TOLERANCE
    ]
    return {
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "route_flow": route_flow,
        "saturated_routes": saturated_routes,
    }


def build_exercise_3_2(spec: dict[str, Any]) -> ConcreteModel:
    period_count = len(spec["demand"])
    model = ConcreteModel(name="exercise_3_2_ten_period_production")
    model.T = RangeSet(1, period_count)
    model.production = Var(model.T, domain=NonNegativeReals)
    model.inventory = Var(model.T, domain=NonNegativeReals)

    def balance_rule(current: ConcreteModel, period: int):
        previous = (
            float(spec["initial_inventory"])
            if period == 1
            else current.inventory[period - 1]
        )
        return (
            previous + current.production[period]
            == float(spec["demand"][period - 1]) + current.inventory[period]
        )

    model.balance = Constraint(model.T, rule=balance_rule)
    model.objective = Objective(
        expr=sum(
            float(spec["production_cost"][period - 1]) * model.production[period]
            + float(spec["holding_cost"]) * model.inventory[period]
            for period in model.T
        ),
        sense=minimize,
    )
    return model


def solve_exercise_3_2(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_exercise_3_2(spec)
    execution = _solve(model)
    return {
        "ending_inventory": [_clean(value(model.inventory[t])) for t in model.T],
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "production": [_clean(value(model.production[t])) for t in model.T],
    }


def build_exercise_3_3(spec: dict[str, Any]) -> ConcreteModel:
    foods = tuple(spec["foods"])
    nutrients = tuple(spec["minimum"])
    model = ConcreteModel(name="exercise_3_3_continuous_diet")
    model.F = Set(initialize=foods, ordered=True)
    model.N = Set(initialize=nutrients, ordered=True)
    model.amount = Var(model.F, domain=NonNegativeReals)
    model.minimum = Constraint(
        model.N,
        rule=lambda current, nutrient: sum(
            float(spec["nutrient"][food][nutrient]) * current.amount[food]
            for food in current.F
        )
        >= float(spec["minimum"][nutrient]),
    )
    model.objective = Objective(
        expr=sum(float(spec["price"][food]) * model.amount[food] for food in model.F),
        sense=minimize,
    )
    return model


def solve_exercise_3_3(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_exercise_3_3(spec)
    execution = _solve(model)
    totals = {
        nutrient: _clean(
            sum(
                float(spec["nutrient"][food][nutrient])
                * float(value(model.amount[food]))
                for food in model.F
            )
        )
        for nutrient in model.N
    }
    return {
        "active_minimums": [
            nutrient
            for nutrient in model.N
            if abs(totals[nutrient] - float(spec["minimum"][nutrient])) <= TOLERANCE
        ],
        "amount": {food: _clean(value(model.amount[food])) for food in model.F},
        "exact_objective_fraction": spec["exact_objective_fraction"],
        "execution": execution,
        "nutrient_total": totals,
        "objective": _clean(value(model.objective)),
    }


def build_exercise_3_4(
    spec: dict[str, Any], *, widget_profit: float | None = None
) -> ConcreteModel:
    products = tuple(spec["profit"])
    resources = tuple(spec["resource_capacity"])
    profit = dict(spec["profit"])
    if widget_profit is not None:
        profit["widget"] = widget_profit
    model = ConcreteModel(name="exercise_3_4_two_product")
    model.P = Set(initialize=products, ordered=True)
    model.R = Set(initialize=resources, ordered=True)
    model.production = Var(model.P, domain=NonNegativeReals)
    model.resource = Constraint(
        model.R,
        rule=lambda current, resource: sum(
            float(spec["resource_use"][product][resource])
            * current.production[product]
            for product in current.P
        )
        <= float(spec["resource_capacity"][resource]),
    )
    model.objective = Objective(
        expr=sum(float(profit[product]) * model.production[product] for product in model.P),
        sense=maximize,
    )
    model.dual = Suffix(direction=Suffix.IMPORT)
    model.rc = Suffix(direction=Suffix.IMPORT)
    return model


def _solve_exercise_3_4_case(
    spec: dict[str, Any], *, widget_profit: float | None = None
) -> dict[str, Any]:
    model = build_exercise_3_4(spec, widget_profit=widget_profit)
    execution = _solve(model)
    result = {
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "production": {
            product: _clean(value(model.production[product])) for product in model.P
        },
    }
    if widget_profit is None:
        result["reduced_cost"] = {
            product: _reduced_cost(model, model.production[product]) for product in model.P
        }
        result["resource_dual"] = {
            resource: _dual(model, model.resource[resource]) for resource in model.R
        }
    return result


def solve_exercise_3_4(spec: dict[str, Any]) -> dict[str, Any]:
    rerun_profit = float(spec["sensitivity"]["widget_profit_rerun"])
    return {
        "baseline": _solve_exercise_3_4_case(spec),
        "widget_profit_9": _solve_exercise_3_4_case(
            spec, widget_profit=rerun_profit
        ),
        "widget_profit_allowable_range": [
            _clean(number)
            for number in spec["sensitivity"]["widget_profit_allowable_range"]
        ],
    }


def build_exercise_3_5(spec: dict[str, Any]) -> ConcreteModel:
    warehouses = tuple(spec["supply"])
    stores = tuple(spec["demand"])
    model = ConcreteModel(name="exercise_3_5_balanced_transportation")
    model.W = Set(initialize=warehouses, ordered=True)
    model.S = Set(initialize=stores, ordered=True)
    model.flow = Var(model.W, model.S, domain=NonNegativeReals)
    model.supply = Constraint(
        model.W,
        rule=lambda current, warehouse: sum(
            current.flow[warehouse, store] for store in current.S
        )
        <= float(spec["supply"][warehouse]),
    )
    model.demand = Constraint(
        model.S,
        rule=lambda current, store: sum(
            current.flow[warehouse, store] for warehouse in current.W
        )
        == float(spec["demand"][store]),
    )
    model.objective = Objective(
        expr=sum(
            float(spec["cost"][warehouse][store]) * model.flow[warehouse, store]
            for warehouse in model.W
            for store in model.S
        ),
        sense=minimize,
    )
    return model


def solve_exercise_3_5(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_exercise_3_5(spec)
    execution = _solve(model)
    return {
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "route_flow": {
            f"{warehouse}-{store}": _clean(value(model.flow[warehouse, store]))
            for warehouse in model.W
            for store in model.S
        },
    }


def build_exercise_3_6(
    spec: dict[str, Any],
    *,
    desk_profit: float | None = None,
    finishing_capacity: float | None = None,
) -> ConcreteModel:
    products = tuple(spec["profit"])
    resources = tuple(spec["resource_capacity"])
    profit = dict(spec["profit"])
    capacity = dict(spec["resource_capacity"])
    if desk_profit is not None:
        profit["desk"] = desk_profit
    if finishing_capacity is not None:
        capacity["finishing"] = finishing_capacity
    model = ConcreteModel(name="exercise_3_6_furniture_sensitivity")
    model.P = Set(initialize=products, ordered=True)
    model.R = Set(initialize=resources, ordered=True)
    model.production = Var(model.P, domain=NonNegativeReals)
    model.resource = Constraint(
        model.R,
        rule=lambda current, resource: sum(
            float(spec["resource_use"][product][resource])
            * current.production[product]
            for product in current.P
        )
        <= float(capacity[resource]),
    )
    model.objective = Objective(
        expr=sum(float(profit[product]) * model.production[product] for product in model.P),
        sense=maximize,
    )
    model.dual = Suffix(direction=Suffix.IMPORT)
    model.rc = Suffix(direction=Suffix.IMPORT)
    return model


def _solve_exercise_3_6_case(
    spec: dict[str, Any],
    *,
    desk_profit: float | None = None,
    finishing_capacity: float | None = None,
    sensitivity_output: bool = False,
) -> dict[str, Any]:
    model = build_exercise_3_6(
        spec,
        desk_profit=desk_profit,
        finishing_capacity=finishing_capacity,
    )
    execution = _solve(model)
    result = {
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "production": {
            product: _clean(value(model.production[product])) for product in model.P
        },
    }
    if sensitivity_output:
        result["desk_reduced_cost"] = _reduced_cost(
            model, model.production["desk"]
        )
        result["resource_dual"] = {
            resource: _dual(model, model.resource[resource]) for resource in model.R
        }
    return result


def solve_exercise_3_6(spec: dict[str, Any]) -> dict[str, Any]:
    finishing_plus = float(spec["sensitivity"]["finishing_capacity_increase"])
    finishing_capacity = float(spec["resource_capacity"]["finishing"])
    desk_profits = spec["sensitivity"]["desk_profit_reruns"]
    return {
        "baseline": _solve_exercise_3_6_case(spec, sensitivity_output=True),
        "desk_profit_100": _solve_exercise_3_6_case(
            spec, desk_profit=float(desk_profits[0])
        ),
        "desk_profit_110": _solve_exercise_3_6_case(
            spec, desk_profit=float(desk_profits[1])
        ),
        "finishing_plus_20": _solve_exercise_3_6_case(
            spec, finishing_capacity=finishing_capacity + finishing_plus
        ),
        "shadow_price_scope": spec["sensitivity"]["shadow_price_scope"],
    }


def build_exercise_3_7(spec: dict[str, Any]) -> ConcreteModel:
    plants = tuple(spec["supply_capacity"])
    cities = tuple(spec["demand"])
    model = ConcreteModel(name="exercise_3_7_unbalanced_transportation")
    model.P = Set(initialize=plants, ordered=True)
    model.C = Set(initialize=cities, ordered=True)
    model.flow = Var(model.P, model.C, domain=NonNegativeReals)
    model.supply = Constraint(
        model.P,
        rule=lambda current, plant: sum(
            current.flow[plant, city] for city in current.C
        )
        <= float(spec["supply_capacity"][plant]),
    )
    model.demand = Constraint(
        model.C,
        rule=lambda current, city: sum(
            current.flow[plant, city] for plant in current.P
        )
        == float(spec["demand"][city]),
    )
    model.objective = Objective(
        expr=sum(
            float(spec["cost"][plant][city]) * model.flow[plant, city]
            for plant in model.P
            for city in model.C
        ),
        sense=minimize,
    )
    model.dual = Suffix(direction=Suffix.IMPORT)
    model.rc = Suffix(direction=Suffix.IMPORT)
    return model


def solve_exercise_3_7(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_exercise_3_7(spec)
    execution = _solve(model)
    city_total = {
        city: _clean(sum(value(model.flow[plant, city]) for plant in model.P))
        for city in model.C
    }
    total_unused_capacity = sum(float(spec["supply_capacity"][plant]) for plant in model.P) - sum(
        city_total.values()
    )
    return {
        "city_total": city_total,
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "route_flows_omitted_due_to_degeneracy": True,
        "supply_dual": {
            plant: _dual(model, model.supply[plant]) for plant in model.P
        },
        "total_unused_capacity": _clean(total_unused_capacity),
    }


def build_exercise_3_9(spec: dict[str, Any], *, short_selling: bool) -> ConcreteModel:
    model = ConcreteModel(
        name=(
            "exercise_3_9_nonnegative_checkbox_off"
            if short_selling
            else "exercise_3_9_nonnegative_checkbox_on"
        )
    )
    model.asset_a = Var(domain=Reals if short_selling else NonNegativeReals)
    model.asset_b = Var(
        domain=NonNegativeReals,
        bounds=(0.0, float(spec["assets"]["B"]["upper_bound"])),
    )
    model.budget = Constraint(
        expr=model.asset_a + model.asset_b == float(spec["budget"])
    )
    model.objective = Objective(
        expr=float(spec["assets"]["A"]["return"]) * model.asset_a
        + float(spec["assets"]["B"]["return"]) * model.asset_b,
        sense=maximize,
    )
    return model


def _solve_exercise_3_9_case(
    spec: dict[str, Any], *, short_selling: bool
) -> dict[str, Any]:
    model = build_exercise_3_9(spec, short_selling=short_selling)
    execution = _solve(model)
    return {
        "execution": execution,
        "holdings": {
            "A": _clean(value(model.asset_a)),
            "B": _clean(value(model.asset_b)),
        },
        "objective": _clean(value(model.objective)),
    }


def solve_exercise_3_9(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "nonnegative_checkbox_off": _solve_exercise_3_9_case(
            spec, short_selling=True
        ),
        "nonnegative_checkbox_on": _solve_exercise_3_9_case(
            spec, short_selling=False
        ),
    }


def solve_all(data: dict[str, Any]) -> dict[str, Any]:
    """Menjalankan seluruh LP dan menyalin perbandingan konseptual 3.8."""
    exercises = data["exercises"]
    return {
        "exercises": {
            "3.1": solve_exercise_3_1(exercises["3.1"]),
            "3.2": solve_exercise_3_2(exercises["3.2"]),
            "3.3": solve_exercise_3_3(exercises["3.3"]),
            "3.4": solve_exercise_3_4(exercises["3.4"]),
            "3.5": solve_exercise_3_5(exercises["3.5"]),
            "3.6": solve_exercise_3_6(exercises["3.6"]),
            "3.7": solve_exercise_3_7(exercises["3.7"]),
            "3.8": {
                "comparison": exercises["3.8"]["comparison"],
                "formula_case": exercises["3.8"]["formula_case"],
                "smooth_example": exercises["3.8"]["smooth_example"],
            },
            "3.9": solve_exercise_3_9(exercises["3.9"]),
        },
        "lab_id": data["lab_id"],
        "runtime": {
            "highspy": version("highspy"),
            "numpy": version("numpy"),
            "pyomo": version("pyomo"),
            "solver_interface": "appsi_highs",
        },
        "schema_version": "1.0.0",
    }
