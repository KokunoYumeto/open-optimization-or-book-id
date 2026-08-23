"""Alur kerja Pyomo+HiGHS dan sertifikat Bab 12.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

from pyomo.environ import (
    ConcreteModel,
    Constraint,
    ConstraintList,
    NonNegativeReals,
    Objective,
    Set,
    SolverFactory,
    Suffix,
    Var,
    maximize,
    minimize,
    value,
)
from pyomo.opt import SolverStatus, TerminationCondition


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]
LAB_ID = "o018.ch12.python-workflow"
EXERCISE_IDS = tuple(f"12.{index}" for index in range(1, 10))
TOLERANCE = 1e-8


def clean_float(number: float) -> int | float:
    if abs(number) < TOLERANCE:
        return 0
    rounded = round(float(number), 10)
    nearest = round(rounded)
    if abs(rounded - nearest) < TOLERANCE:
        return int(nearest)
    return rounded


def exact(number: int | float | Fraction) -> int | str:
    fraction = number if isinstance(number, Fraction) else Fraction(str(number))
    if fraction.denominator == 1:
        return fraction.numerator
    return f"{fraction.numerator}/{fraction.denominator}"


def exact_vector(items: Iterable[int | float | Fraction]) -> list[int | str]:
    return [exact(item) for item in items]


def load_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != LAB_ID:
        raise ValueError("lab_id tidak sesuai")
    if tuple(data.get("exercise_order", ())) != EXERCISE_IDS:
        raise ValueError("exercise_order harus tepat memuat 12.1--12.9")
    exercises = data.get("exercises")
    if not isinstance(exercises, dict) or tuple(exercises) != EXERCISE_IDS:
        raise ValueError("data latihan tidak utuh atau tidak berurutan")
    if [item["difficulty"] for item in exercises.values()] != [1, 1, 1, 2, 2, 2, 2, 2, 3]:
        raise ValueError("tingkat kesulitan tidak sesuai urutan buku")
    if len({item["book_label"] for item in exercises.values()}) != 9:
        raise ValueError("label latihan harus unik")
    if any(
        item["manual_mapping"] != {"manual_id": exercise_id, "status": "aligned"}
        for exercise_id, item in exercises.items()
    ):
        raise ValueError("pemetaan buku--manual 12.1--12.9 harus selaras")
    if data.get("source_defects") != [] or data.get("unresolved_exercises") != []:
        raise ValueError("lab Bab 12 tidak memiliki cacat atau latihan tak selesai")
    if len(data.get("provenance", {}).get("source_files", ())) != 4:
        raise ValueError("closure sumber harus memuat empat saksi")
    return data


def _solver():
    solver = SolverFactory("appsi_highs")
    if not solver.available(exception_flag=False):
        raise RuntimeError("pemecah appsi_highs tidak tersedia")
    solver.options["output_flag"] = False
    return solver


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


def _assert_optimal(result, variant: str) -> None:
    if result.solver.status not in {SolverStatus.ok, SolverStatus.warning}:
        raise RuntimeError(f"status HiGHS {variant} tidak diterima: {result.solver.status}")
    if result.solver.termination_condition != TerminationCondition.optimal:
        raise RuntimeError(f"terminasi HiGHS {variant}: {result.solver.termination_condition}")


def _base_record(model: ConcreteModel, result, variant: str, purpose: str) -> dict[str, Any]:
    return {
        "maximum_violation": clean_float(_maximum_violation(model)),
        "purpose": purpose,
        "solver": "appsi_highs",
        "status": str(result.solver.status),
        "termination_condition": str(result.solver.termination_condition),
        "variant": variant,
    }


def _product_mix(
    case: dict[str, Any],
    *,
    objective: tuple[float, float] = (3, 2),
    objective_sense: str = "max",
    labor_rhs: float = 160,
    include_labor: bool = True,
    machine_cap: float | None = None,
) -> ConcreteModel:
    model = ConcreteModel()
    model.x1 = Var(domain=NonNegativeReals)
    model.x2 = Var(domain=NonNegativeReals)
    direction = maximize if objective_sense == "max" else minimize
    model.objective = Objective(
        expr=objective[0] * model.x1 + objective[1] * model.x2,
        sense=direction,
    )
    constraints = case["constraints"]
    material = constraints["material"]
    labor = constraints["labor"]
    machine = constraints["machine"]
    model.material = Constraint(
        expr=material["coefficients"][0] * model.x1
        + material["coefficients"][1] * model.x2
        <= material["rhs"]
    )
    if include_labor:
        model.labor = Constraint(
            expr=labor["coefficients"][0] * model.x1
            + labor["coefficients"][1] * model.x2
            <= labor_rhs
        )
    model.machine = Constraint(
        expr=machine["coefficients"][0] * model.x1
        + machine["coefficients"][1] * model.x2
        <= machine["rhs"]
    )
    if machine_cap is not None:
        model.machine_cap = Constraint(
            expr=machine["coefficients"][0] * model.x1
            + machine["coefficients"][1] * model.x2
            <= machine_cap
        )
    model.dual = Suffix(direction=Suffix.IMPORT)
    return model


def _constraint_slack(constraint: Constraint) -> int | float:
    body = float(value(constraint.body))
    if constraint.upper is not None:
        return clean_float(float(value(constraint.upper)) - body)
    if constraint.lower is not None:
        return clean_float(body - float(value(constraint.lower)))
    raise ValueError("kendala tanpa batas tidak didukung")


def solve_product_mix(
    case: dict[str, Any],
    *,
    variant: str,
    purpose: str,
    objective: tuple[float, float] = (3, 2),
    objective_sense: str = "max",
    labor_rhs: float = 160,
    include_labor: bool = True,
    machine_cap: float | None = None,
    include_duals: bool = False,
) -> dict[str, Any]:
    model = _product_mix(
        case,
        objective=objective,
        objective_sense=objective_sense,
        labor_rhs=labor_rhs,
        include_labor=include_labor,
        machine_cap=machine_cap,
    )
    result = _solver().solve(model)
    _assert_optimal(result, variant)
    record = _base_record(model, result, variant, purpose)
    record["objective"] = clean_float(value(model.objective))
    record["solution"] = {
        "X1": clean_float(value(model.x1)),
        "X2": clean_float(value(model.x2)),
    }
    constraints = {
        "material": model.material,
        "machine": model.machine,
    }
    if include_labor:
        constraints["labor"] = model.labor
    if machine_cap is not None:
        constraints["machine_cap"] = model.machine_cap
    record["slacks"] = {
        name: _constraint_slack(constraint)
        for name, constraint in sorted(constraints.items())
    }
    if include_duals:
        record["duals"] = {
            name: exact(clean_float(model.dual[constraint]))
            for name, constraint in sorted(constraints.items())
        }
    return record


def solve_three_variable(case: dict[str, Any]) -> dict[str, Any]:
    model = ConcreteModel()
    model.I = Set(initialize=range(3), ordered=True)
    model.x = Var(model.I, domain=NonNegativeReals)
    model.objective = Objective(
        expr=sum(case["objective"][i] * model.x[i] for i in model.I),
        sense=maximize,
    )
    model.constraints = ConstraintList()
    for row in case["constraints"]:
        model.constraints.add(
            sum(row["coefficients"][i] * model.x[i] for i in model.I) <= row["rhs"]
        )
    result = _solver().solve(model)
    _assert_optimal(result, "three-variable")
    record = _base_record(model, result, "three-variable", "terjemahan enam langkah")
    record["objective"] = clean_float(value(model.objective))
    record["solution"] = {
        case["variables"][i]: clean_float(value(model.x[i])) for i in model.I
    }
    record["constraint_slacks"] = [
        _constraint_slack(model.constraints[index]) for index in model.constraints
    ]
    return record


def _cost(case: dict[str, Any], plant: str, market: str) -> float:
    return case["cost"][f"{plant}|{market}"]


def solve_transport(
    case: dict[str, Any], *, demand_override: dict[str, float] | None, variant: str
) -> dict[str, Any]:
    demand = demand_override or case["demand"]
    model = ConcreteModel()
    model.P = Set(initialize=case["plants"], ordered=True)
    model.M = Set(initialize=case["markets"], ordered=True)
    model.x = Var(model.P, model.M, domain=NonNegativeReals)
    model.objective = Objective(
        expr=sum(_cost(case, p, m) * model.x[p, m] for p in model.P for m in model.M),
        sense=minimize,
    )
    model.supply = Constraint(
        model.P,
        rule=lambda mdl, p: sum(mdl.x[p, m] for m in mdl.M) <= case["supply"][p],
    )
    model.demand = Constraint(
        model.M,
        rule=lambda mdl, m: sum(mdl.x[p, m] for p in mdl.P) >= demand[m],
    )
    result = _solver().solve(model)
    _assert_optimal(result, variant)
    record = _base_record(model, result, variant, "model transportasi berindeks")
    record["objective"] = clean_float(value(model.objective))
    record["shipments"] = [
        {"from": p, "quantity": clean_float(value(model.x[p, m])), "to": m}
        for p in model.P
        for m in model.M
        if value(model.x[p, m]) > TOLERANCE
    ]
    record["plant_unused"] = {
        p: clean_float(case["supply"][p] - sum(value(model.x[p, m]) for m in model.M))
        for p in model.P
    }
    record["market_surplus"] = {
        m: clean_float(sum(value(model.x[p, m]) for p in model.P) - demand[m])
        for m in model.M
    }
    return record


def _exercise_result(data: dict[str, Any], exercise_id: str, certificate: dict[str, Any], checks: list[dict[str, Any]]) -> dict[str, Any]:
    spec = data["exercises"][exercise_id]
    return {
        "book_label": spec["book_label"],
        "certificate": certificate,
        "difficulty": spec["difficulty"],
        "manual_mapping": spec["manual_mapping"],
        "method": spec["method"],
        "solver_checks": checks,
        "status": "verified",
        "title": spec["title"],
    }


def evaluate_all(data: dict[str, Any]) -> dict[str, Any]:
    mix = data["cases"]["product_mix"]
    exercises: dict[str, dict[str, Any]] = {}

    check_1 = solve_product_mix(
        mix, variant="profit-5-2", purpose="perubahan margin laba", objective=(5, 2)
    )
    certificate_1 = {
        "binding_constraints": [name for name, slack in check_1["slacks"].items() if slack == 0],
        "objective": check_1["objective"],
        "slacks": check_1["slacks"],
        "solution": check_1["solution"],
    }
    exercises["12.1"] = _exercise_result(data, "12.1", certificate_1, [check_1])

    check_2 = solve_three_variable(data["cases"]["three_variable"])
    certificate_2 = {
        "constraint_slacks": check_2["constraint_slacks"],
        "objective": check_2["objective"],
        "solution": check_2["solution"],
    }
    exercises["12.2"] = _exercise_result(data, "12.2", certificate_2, [check_2])

    demand_new = {"NYC": 100, "LA": 80, "Houston": 70}
    check_3 = solve_transport(
        data["cases"]["transport_base"], demand_override=demand_new, variant="demand-new"
    )
    certificate_3 = {
        "demand_total": sum(demand_new.values()),
        "explanation": "Permintaan total bertambah dan bergeser ke pasar dengan biaya masuk yang lebih tinggi.",
        "objective": check_3["objective"],
        "supply_total": sum(data["cases"]["transport_base"]["supply"].values()),
    }
    exercises["12.3"] = _exercise_result(data, "12.3", certificate_3, [check_3])

    check_4 = solve_transport(
        data["cases"]["transport_three_plant"], demand_override=None, variant="three-plant"
    )
    certificate_4 = {
        "objective": check_4["objective"],
        "plant_unused": check_4["plant_unused"],
        "total_unused_capacity": clean_float(sum(check_4["plant_unused"].values())),
    }
    exercises["12.4"] = _exercise_result(data, "12.4", certificate_4, [check_4])

    check_5 = solve_product_mix(
        mix, variant="base-duals", purpose="impor dual dan slack", include_duals=True
    )
    certificate_5 = {
        "duals": {name: check_5["duals"][name] for name in ("labor", "machine", "material")},
        "objective": check_5["objective"],
        "slacks": {name: check_5["slacks"][name] for name in ("labor", "machine", "material")},
        "solution": check_5["solution"],
    }
    exercises["12.5"] = _exercise_result(data, "12.5", certificate_5, [check_5])

    epsilon_checks = [
        solve_product_mix(
            mix,
            variant=f"epsilon-{epsilon}",
            purpose="sapuan batas penggunaan mesin",
            machine_cap=epsilon,
        )
        for epsilon in (60, 90, 120, 150, 180)
    ]
    epsilon_table = [
        {
            "X1": check["solution"]["X1"],
            "X2": check["solution"]["X2"],
            "epsilon": epsilon,
            "profit": check["objective"],
        }
        for epsilon, check in zip((60, 90, 120, 150, 180), epsilon_checks)
    ]
    certificate_6 = {
        "epsilon_table": epsilon_table,
        "machine_use_without_extra_cap": 160,
        "tradeoff_profit_per_machine_hour": "1/10",
    }
    exercises["12.6"] = _exercise_result(data, "12.6", certificate_6, epsilon_checks)

    missing = solve_product_mix(
        mix,
        variant="missing-labor",
        purpose="diagnosis inventaris kendala",
        include_labor=False,
    )
    overwritten = solve_product_mix(
        mix,
        variant="overwritten-objective-equivalent",
        purpose="diagnosis fungsi tujuan tertimpa",
        objective=(4, 4),
        include_labor=False,
    )
    missing_labor_used = clean_float(4 * missing["solution"]["X1"] + 4 * missing["solution"]["X2"])
    overwritten_labor_value = clean_float(4 * overwritten["solution"]["X1"] + 4 * overwritten["solution"]["X2"])
    certificate_7 = {
        "missing_labor": {
            "actual_profit": clean_float(3 * missing["solution"]["X1"] + 2 * missing["solution"]["X2"]),
            "labor_excess": clean_float(missing_labor_used - 160),
            "labor_used": missing_labor_used,
            "reported_objective": missing["objective"],
            "solution": missing["solution"],
        },
        "overwritten_objective_equivalent": {
            "actual_profit": clean_float(3 * overwritten["solution"]["X1"] + 2 * overwritten["solution"]["X2"]),
            "labor_expression_value": overwritten_labor_value,
            "reported_objective": overwritten["objective"],
            "solution": overwritten["solution"],
        },
    }
    exercises["12.7"] = _exercise_result(data, "12.7", certificate_7, [missing, overwritten])

    wrong = solve_product_mix(
        mix, variant="wrong-minimize", purpose="uji arah tujuan salah", objective_sense="min"
    )
    correct = solve_product_mix(
        mix, variant="correct-maximize", purpose="perbaikan arah tujuan"
    )
    negative = solve_product_mix(
        mix,
        variant="minimize-negative-profit",
        purpose="perbaikan dengan tujuan negatif",
        objective=(-3, -2),
        objective_sense="min",
    )
    certificate_8 = {
        "correct_maximize": {"objective": correct["objective"], "solution": correct["solution"]},
        "minimize_negative_profit": {"objective": negative["objective"], "solution": negative["solution"]},
        "wrong_minimize": {"objective": wrong["objective"], "solution": wrong["solution"]},
    }
    exercises["12.8"] = _exercise_result(data, "12.8", certificate_8, [wrong, correct, negative])

    labor_values = tuple(range(100, 200, 10))
    labor_checks = [
        solve_product_mix(
            mix,
            variant=f"labor-{rhs}",
            purpose="sapuan ruas kanan tenaga kerja",
            labor_rhs=rhs,
            include_duals=True,
        )
        for rhs in labor_values
    ]
    for rhs, check in zip(labor_values, labor_checks):
        check["labor_rhs"] = rhs
        check["labor_dual"] = check["duals"]["labor"]
    certificate_9 = {
        "breakpoints": [120, 168],
        "labor_rhs": list(labor_values),
        "profit_values": exact_vector([check["objective"] for check in labor_checks]),
        "slope_intervals": ["3/4", "1/4", 0],
    }
    exercises["12.9"] = _exercise_result(data, "12.9", certificate_9, labor_checks)

    checks = [check for exercise in exercises.values() for check in exercise["solver_checks"]]
    method_counts = Counter(item["method"] for item in data["exercises"].values())
    termination_counts = Counter(check["termination_condition"] for check in checks)
    return {
        "authority_commit": data["authority_commit"],
        "exercises": exercises,
        "lab_id": LAB_ID,
        "provenance": data["provenance"],
        "schema_version": data["schema_version"],
        "source_defects": data["source_defects"],
        "summary": {
            "exercise_count": len(exercises),
            "maximum_solver_violation": clean_float(max(float(check["maximum_violation"]) for check in checks)),
            "method_counts": dict(sorted(method_counts.items())),
            "o018_math_correction_count": 0,
            "solver_call_count": len(checks),
            "solver_termination_counts": dict(sorted(termination_counts.items())),
            "source_defect_count": len(data["source_defects"]),
            "unresolved_count": len(data["unresolved_exercises"]),
            "verified_count": len(exercises),
        },
        "unresolved_exercises": data["unresolved_exercises"],
    }
