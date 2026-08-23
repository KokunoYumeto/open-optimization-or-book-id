"""Sertifikat eksak dan pemeriksaan Pyomo+HiGHS untuk Bab 13.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    ConstraintList,
    NonNegativeReals,
    Objective,
    Set,
    SolverFactory,
    Var,
    maximize,
    minimize,
    value,
)
from pyomo.opt import SolverStatus, TerminationCondition


HERE = Path(__file__).resolve().parent
LANE_ROOT = HERE.parents[2]
LAB_ID = "o018.ch13.multiobjective"
EXERCISE_IDS = tuple(f"13.{index}" for index in range(1, 12))
TOLERANCE = 1e-8


def as_fraction(number: int | str | float | Fraction) -> Fraction:
    if isinstance(number, Fraction):
        return number
    if isinstance(number, int):
        return Fraction(number)
    if isinstance(number, float):
        return Fraction(str(number))
    return Fraction(number)


def exact(number: int | str | float | Fraction) -> int | str:
    fraction = as_fraction(number)
    if fraction.denominator == 1:
        return fraction.numerator
    return f"{fraction.numerator}/{fraction.denominator}"


def exact_vector(items: Iterable[int | str | float | Fraction]) -> list[int | str]:
    return [exact(item) for item in items]


def clean_float(number: float) -> int | float:
    if abs(number) < TOLERANCE:
        return 0
    rounded = round(number, 10)
    nearest = round(rounded)
    if abs(rounded - nearest) < TOLERANCE:
        return int(nearest)
    return rounded


def dot(
    first: Sequence[int | str | float | Fraction],
    second: Sequence[int | str | float | Fraction],
) -> Fraction:
    if len(first) != len(second):
        raise ValueError("panjang vektor tidak sama")
    return sum(
        (as_fraction(a) * as_fraction(b) for a, b in zip(first, second)),
        Fraction(0),
    )


def load_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != LAB_ID:
        raise ValueError("lab_id tidak sesuai")
    if tuple(data.get("exercise_order", ())) != EXERCISE_IDS:
        raise ValueError("exercise_order harus tepat memuat 13.1--13.11")
    exercises = data.get("exercises")
    if not isinstance(exercises, dict) or tuple(exercises) != EXERCISE_IDS:
        raise ValueError("data latihan tidak utuh atau tidak berurutan")
    difficulties = [spec["difficulty"] for spec in exercises.values()]
    if difficulties != [1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 3]:
        raise ValueError("tingkat kesulitan tidak sesuai urutan buku")
    labels = [spec["book_label"] for spec in exercises.values()]
    if len(labels) != len(set(labels)):
        raise ValueError("label latihan buku harus unik")
    mapping = {
        exercise_id: spec["manual_mapping"]["status"]
        for exercise_id, spec in exercises.items()
    }
    if mapping["13.10"] != "missing_from_manual":
        raise ValueError("ketiadaan manual 13.10 harus terlihat")
    if mapping["13.11"] != "manual_stale_alias":
        raise ValueError("alias manual lama untuk 13.11 harus terlihat")
    if any(
        mapping[f"13.{index}"] != "aligned" for index in range(1, 10)
    ):
        raise ValueError("pemetaan 13.1--13.9 harus selaras")
    defect_ids = [item["id"] for item in data.get("source_defects", ())]
    if defect_ids != [
        "DEF-CH13-MANUAL-OMISSION",
        "DEF-CH13-70PCT-FIGURE",
        "DEF-CH13-REVENUE-PROFIT-TERMS",
    ]:
        raise ValueError("inventaris cacat sumber tidak tertutup")
    if data.get("unresolved_exercises") != []:
        raise ValueError("laboratorium ini tidak memiliki latihan tak selesai")
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
        raise RuntimeError(
            f"terminasi HiGHS {variant}: {result.solver.termination_condition}"
        )


def _base_solver_record(
    model: ConcreteModel, result, variant: str, purpose: str
) -> dict[str, Any]:
    return {
        "maximum_violation": clean_float(_maximum_violation(model)),
        "purpose": purpose,
        "solver": "appsi_highs",
        "status": str(result.solver.status),
        "termination_condition": str(result.solver.termination_condition),
        "variant": variant,
    }


def _dominates(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return (
        first["f1"] <= second["f1"]
        and first["f2"] <= second["f2"]
        and (first["f1"] < second["f1"] or first["f2"] < second["f2"])
    )


def pareto_names(items: Sequence[dict[str, Any]]) -> list[str]:
    return [
        item["name"]
        for item in items
        if not any(
            other is not item and _dominates(other, item) for other in items
        )
    ]


def dominators(items: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        item["name"]: [
            other["name"]
            for other in items
            if other is not item and _dominates(other, item)
        ]
        for item in items
        if any(
            other is not item and _dominates(other, item) for other in items
        )
    }


def weighted_scores(
    items: Sequence[dict[str, Any]], alpha: int | str | Fraction
) -> dict[str, int | str]:
    weight = as_fraction(alpha)
    return {
        item["name"]: exact(
            weight * as_fraction(item["f1"])
            + (1 - weight) * as_fraction(item["f2"])
        )
        for item in items
    }


def solve_discrete(
    data: dict[str, Any],
    case_name: str,
    variant: str,
    *,
    alpha: int | str | Fraction = Fraction(1, 2),
    f1_upper: int | str | Fraction | None = None,
    f2_upper: int | str | Fraction | None = None,
) -> dict[str, Any]:
    case = data["cases"][case_name]
    items = case["items"]
    weight = as_fraction(alpha)
    model = ConcreteModel(name=f"ch13_{case_name}_{variant}")
    names = [item["name"] for item in items]
    by_name = {item["name"]: item for item in items}
    model.I = Set(initialize=names, ordered=True)
    model.z = Var(model.I, domain=Binary)
    model.choose_one = Constraint(expr=sum(model.z[name] for name in model.I) == 1)
    if f1_upper is not None:
        model.f1_limit = Constraint(
            expr=sum(by_name[name]["f1"] * model.z[name] for name in model.I)
            <= float(as_fraction(f1_upper))
        )
    if f2_upper is not None:
        model.f2_limit = Constraint(
            expr=sum(by_name[name]["f2"] * model.z[name] for name in model.I)
            <= float(as_fraction(f2_upper))
        )
    expression = sum(
        (
            float(weight) * by_name[name]["f1"]
            + float(1 - weight) * by_name[name]["f2"]
        )
        * model.z[name]
        for name in model.I
    )
    model.objective = Objective(expr=expression, sense=minimize)
    result = _solver().solve(model, tee=False)
    _assert_optimal(result, variant)
    selected = [
        name for name in model.I if float(value(model.z[name])) > 0.5
    ]
    if len(selected) != 1:
        raise RuntimeError(f"pilihan diskret {variant} tidak tunggal secara numerik")
    chosen = by_name[selected[0]]
    record = _base_solver_record(
        model, result, variant, "independent_discrete_pyomo_highs_corroboration"
    )
    record.update(
        {
            "alpha": exact(weight),
            "case": case_name,
            "f1": chosen["f1"],
            "f1_upper": None if f1_upper is None else exact(f1_upper),
            "f2": chosen["f2"],
            "f2_upper": None if f2_upper is None else exact(f2_upper),
            "objective": clean_float(float(value(model.objective))),
            "selected": selected[0],
        }
    )
    return record


def _add_linear_constraints(
    model: ConcreteModel,
    variables: Sequence,
    constraints: Sequence[dict[str, Any]],
) -> None:
    model.rows = ConstraintList()
    for row in constraints:
        expression = sum(
            float(as_fraction(coefficient)) * variables[index]
            for index, coefficient in enumerate(row["coefficients"])
        )
        rhs = float(as_fraction(row["rhs"]))
        if row["sense"] == "<=":
            model.rows.add(expression <= rhs)
        elif row["sense"] == ">=":
            model.rows.add(expression >= rhs)
        else:
            raise ValueError(f"sense kendala tidak dikenal: {row['sense']}")


def solve_epsilon_lp(
    data: dict[str, Any],
    case_name: str,
    variant: str,
    epsilon: int | str | Fraction,
) -> dict[str, Any]:
    case = data["cases"][case_name]
    eps = as_fraction(epsilon)
    model = ConcreteModel(name=f"ch13_{case_name}_{variant}")
    model.J = Set(initialize=range(len(case["variables"])), ordered=True)
    model.x = Var(model.J, domain=NonNegativeReals)
    variables = [model.x[index] for index in model.J]
    _add_linear_constraints(model, variables, case["constraints"])
    f1_expression = sum(
        float(as_fraction(coefficient)) * variables[index]
        for index, coefficient in enumerate(case["f1"])
    )
    f2_expression = sum(
        float(as_fraction(coefficient)) * variables[index]
        for index, coefficient in enumerate(case["f2"])
    )
    if case["objective_sense"] == "min":
        model.epsilon = Constraint(expr=f2_expression <= float(eps))
        objective_sense = minimize
    else:
        model.epsilon = Constraint(expr=f2_expression >= float(eps))
        objective_sense = maximize
    model.objective = Objective(expr=f1_expression, sense=objective_sense)
    result = _solver().solve(model, tee=False)
    _assert_optimal(result, variant)
    point = {
        name: clean_float(float(value(model.x[index])))
        for index, name in enumerate(case["variables"])
    }
    record = _base_solver_record(
        model, result, variant, "independent_continuous_pyomo_highs_corroboration"
    )
    record.update(
        {
            "case": case_name,
            "epsilon": exact(eps),
            "f1": clean_float(float(value(f1_expression))),
            "f2": clean_float(float(value(f2_expression))),
            "point": point,
        }
    )
    return record


def _furniture_model(data: dict[str, Any], name: str) -> tuple[ConcreteModel, list]:
    case = data["cases"]["furniture"]
    model = ConcreteModel(name=name)
    model.J = Set(initialize=range(2), ordered=True)
    model.x = Var(model.J, domain=NonNegativeReals)
    variables = [model.x[index] for index in model.J]
    _add_linear_constraints(model, variables, case["constraints"])
    return model, variables


def solve_furniture_weighted(
    data: dict[str, Any],
    variant: str,
    alpha: int | str | Fraction,
    *,
    revenue_scale: str,
) -> dict[str, Any]:
    case = data["cases"]["furniture"]
    weight = as_fraction(alpha)
    revenue_coefficients = case[
        "revenue_scaled" if revenue_scale == "thousands" else "revenue_raw"
    ]
    model, variables = _furniture_model(data, f"ch13_furniture_{variant}")
    revenue = sum(
        coefficient * variables[index]
        for index, coefficient in enumerate(revenue_coefficients)
    )
    revenue_raw = sum(
        coefficient * variables[index]
        for index, coefficient in enumerate(case["revenue_raw"])
    )
    waste = sum(
        coefficient * variables[index]
        for index, coefficient in enumerate(case["waste"])
    )
    model.objective = Objective(
        expr=float(weight) * revenue - float(1 - weight) * waste,
        sense=maximize,
    )
    result = _solver().solve(model, tee=False)
    _assert_optimal(result, variant)
    record = _base_solver_record(
        model, result, variant, "independent_furniture_pyomo_highs_corroboration"
    )
    record.update(
        {
            "alpha": exact(weight),
            "case": "furniture",
            "point": {
                name: clean_float(float(value(model.x[index])))
                for index, name in enumerate(case["variables"])
            },
            "revenue_raw": clean_float(float(value(revenue_raw))),
            "revenue_scale": revenue_scale,
            "waste": clean_float(float(value(waste))),
            "weighted_objective": clean_float(float(value(model.objective))),
        }
    )
    return record


def solve_furniture_lexicographic(
    data: dict[str, Any], variant: str
) -> tuple[list[dict[str, Any]], dict[str, int | float]]:
    case = data["cases"]["furniture"]
    model, variables = _furniture_model(data, f"ch13_furniture_{variant}")
    revenue = sum(
        coefficient * variables[index]
        for index, coefficient in enumerate(case["revenue_raw"])
    )
    waste = sum(
        coefficient * variables[index]
        for index, coefficient in enumerate(case["waste"])
    )
    model.primary = Objective(expr=revenue, sense=maximize)
    first_result = _solver().solve(model, tee=False)
    _assert_optimal(first_result, f"{variant}_stage1")
    optimum_revenue = clean_float(float(value(revenue)))
    first_record = _base_solver_record(
        model,
        first_result,
        f"{variant}_stage1",
        "lexicographic_primary_revenue_pyomo_highs",
    )
    first_record.update(
        {
            "case": "furniture",
            "objective": optimum_revenue,
            "point": {
                name: clean_float(float(value(model.x[index])))
                for index, name in enumerate(case["variables"])
            },
        }
    )
    model.primary.deactivate()
    model.revenue_lock = Constraint(expr=revenue == float(optimum_revenue))
    model.secondary = Objective(expr=waste, sense=minimize)
    second_result = _solver().solve(model, tee=False)
    _assert_optimal(second_result, f"{variant}_stage2")
    second_record = _base_solver_record(
        model,
        second_result,
        f"{variant}_stage2",
        "lexicographic_secondary_waste_pyomo_highs",
    )
    point = {
        name: clean_float(float(value(model.x[index])))
        for index, name in enumerate(case["variables"])
    }
    second_record.update(
        {
            "case": "furniture",
            "objective": clean_float(float(value(waste))),
            "point": point,
            "revenue_lock": optimum_revenue,
        }
    )
    return [first_record, second_record], point


def _base_result(
    spec: dict[str, Any],
    certificate: dict[str, Any],
    solver_checks: list[dict[str, Any]],
    *,
    status: str = "verified",
) -> dict[str, Any]:
    return {
        "book_label": spec["book_label"],
        "certificate": certificate,
        "difficulty": spec["difficulty"],
        "manual_mapping": spec["manual_mapping"],
        "method": spec["method"],
        "solver_checks": solver_checks,
        "status": status,
        "title": spec["title"],
    }


def evaluate_131(_data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    certificate = {
        "definition": "Tidak ada titik layak lain yang tidak lebih buruk pada kedua tujuan dan secara tegas lebih baik pada sedikitnya satu tujuan.",
        "formal_conditions": [
            "f_i(x_bar)<=f_i(x) untuk i=1,2",
            "f_i(x_bar)<f_i(x) untuk sedikitnya satu i",
        ],
        "maximization_conversion": "Balik kedua pertidaksamaan untuk bentuk maksimisasi.",
        "pareto_frontier": "Himpunan semua titik optimal Pareto.",
    }
    return _base_result(spec, certificate, [])


def evaluate_132(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    items = data["cases"][spec["case"]]["items"]
    checks = [
        solve_discrete(
            data,
            "contracts",
            f"epsilon_f2_{epsilon}",
            alpha=1,
            f2_upper=epsilon,
        )
        for epsilon in (9, 7, 5, 3)
    ]
    frontier = set(pareto_names(items))
    certificate = {
        "dominators": dominators(items),
        "pareto_order_increasing_f1": [
            item["name"]
            for item in sorted(items, key=lambda item: item["f1"])
            if item["name"] in frontier
        ],
        "solver_epsilon_selection": [check["selected"] for check in checks],
        "unique_f1_minimizer_claim": True,
        "uniqueness_note": "Tanpa keunikan, alternatif yang seri pada f1 tetapi memiliki f2 lebih besar dapat terdominasi.",
    }
    return _base_result(spec, certificate, checks)


def evaluate_133(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    items = data["cases"][spec["case"]]["items"]
    checks = [
        solve_discrete(data, "contracts", "weights_3_5_2_5", alpha="3/5"),
        solve_discrete(data, "contracts", "weights_1_5_4_5", alpha="1/5"),
    ]
    certificate = {
        "dominance_gap_I_minus_H": "w1+w2",
        "positive_weights_exclude_I": True,
        "weights_1_5_4_5": {
            "scores": weighted_scores(items, Fraction(1, 5)),
            "winner": "J",
        },
        "weights_3_5_2_5": {
            "scores": weighted_scores(items, Fraction(3, 5)),
            "winner": "G",
        },
    }
    return _base_result(spec, certificate, checks)


def evaluate_134(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    items = data["cases"][spec["case"]]["items"]
    checks = [
        solve_discrete(data, "designs", "weighted_alpha_0", alpha=0),
        solve_discrete(data, "designs", "weighted_alpha_1_5", alpha="1/5"),
        solve_discrete(data, "designs", "weighted_alpha_3_10", alpha="3/10"),
        solve_discrete(data, "designs", "weighted_alpha_1_2", alpha="1/2"),
        solve_discrete(
            data,
            "designs",
            "epsilon_f2_5",
            alpha=1,
            f2_upper=5,
        ),
    ]
    certificate = {
        "dominated": dominators(items),
        "epsilon_5_selection": "A",
        "pareto_frontier": pareto_names(items),
        "supported_by_weighted_sum": ["D", "C", "F"],
        "unsupported_pareto": ["A"],
        "weighted_intervals": {
            "C": ["1/4", "1/3"],
            "D": ["1/3", 1],
            "F": [0, "1/4"],
        },
    }
    return _base_result(spec, certificate, checks)


def evaluate_135(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    items = data["cases"][spec["case"]]["items"]
    checks = [
        solve_discrete(data, "projects", "equal_weights", alpha="1/2"),
        solve_discrete(data, "projects", "cost_only", alpha=1),
        solve_discrete(data, "projects", "accessibility_only", alpha=0),
    ]
    certificate = {
        "dominated": dominators(items),
        "equal_weight_scores": weighted_scores(items, Fraction(1, 2)),
        "equal_weight_winner": "P1",
        "pareto_frontier": pareto_names(items),
        "P3_selectable_by_nonnegative_weights": False,
        "P3_minus_P1_score": "w1+w2",
    }
    return _base_result(spec, certificate, checks)


def evaluate_136(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    checks = [
        solve_epsilon_lp(data, "epsilon_lp", f"epsilon_{epsilon}", epsilon)
        for epsilon in (10, 6, 12, 4)
    ]
    certificate = {
        "epsilon_10": {"f1": 5, "f2": 10, "point": [3, 1]},
        "epsilon_10_pareto": True,
        "epsilon_6": {"f1": 7, "f2": 6, "point": [1, 3]},
        "epsilon_6_pareto": True,
        "epsilon_at_least_12": {
            "f1": 4,
            "f2": 12,
            "point": [4, 0],
            "status": "kendala_epsilon_tidak_aktif",
        },
        "epsilon_below_4": "infeasible",
        "epsilon_feasible_range": [4, 12],
        "f2_individual_minimum": {"f2": 4, "point": [0, 4]},
        "frontier_objective_endpoints": [[4, 12], [8, 4]],
        "single_objective_lp": {
            "constraints": [
                "3*x1+x2<=epsilon",
                "x1+x2>=4",
                "0<=x1<=5",
                "0<=x2<=5",
            ],
            "objective": "min x1+2*x2",
        },
        "solution_affine": {
            "f1": "10-epsilon/2",
            "x1": "(epsilon-4)/2",
            "x2": "(12-epsilon)/2",
        },
    }
    return _base_result(spec, certificate, checks)


def evaluate_137(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    epsilons = (6, 10, 14, 18)
    checks = [
        solve_epsilon_lp(data, "triangle", f"epsilon_{epsilon}", epsilon)
        for epsilon in epsilons
    ]
    certificate = {
        "epsilon_table": [
            {"epsilon": 6, "f1": 18, "f2": 6, "point": [6, 0]},
            {"epsilon": 10, "f1": 14, "f2": 10, "point": [4, 2]},
            {"epsilon": 14, "f1": 10, "f2": 14, "point": [2, 4]},
            {"epsilon": 18, "f1": 6, "f2": 18, "point": [0, 6]},
        ],
        "epsilon_greater_than_18": "infeasible",
        "f1_individual_maximizer": [6, 0],
        "f2_individual_maximizer": [0, 6],
        "frontier_decision_edge": "x1+x2=6, dari (6,0) ke (0,6)",
        "objective_parameterization": {
            "f1": "18-2t",
            "f2": "6+2t",
            "x2": "t",
        },
        "tradeoff_rate_delta_f1_per_delta_f2": -1,
        "vertex_objectives": {
            "(0,0)": [0, 0],
            "(0,6)": [6, 18],
            "(6,0)": [18, 6],
        },
    }
    return _base_result(spec, certificate, checks)


def evaluate_138(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    items = data["cases"][spec["case"]]["items"]
    checks = [
        solve_discrete(
            data,
            "tradeoff",
            "budget_50_min_emissions",
            alpha=0,
            f1_upper=50,
        )
    ]
    ratios = []
    for first, second in zip(items, items[1:]):
        ratios.append(
            {
                "from": first["name"],
                "to": second["name"],
                "delta_cost": second["f1"] - first["f1"],
                "delta_emissions": second["f2"] - first["f2"],
                "emissions_reduced_per_1000_dollars": exact(
                    Fraction(
                        first["f2"] - second["f2"],
                        second["f1"] - first["f1"],
                    )
                ),
            }
        )
    certificate = {
        "budget_50_choice": "S2",
        "budget_feasible": ["S1", "S2"],
        "largest_reduction_per_dollar_step": "S1->S2",
        "marginal_tradeoffs": ratios,
        "natural_knee": "S2",
        "objective_space_polyline": [[40, 20], [45, 14], [55, 10], [70, 8]],
        "plot_improvement_direction": "kiri_bawah",
        "pareto_frontier": pareto_names(items),
    }
    return _base_result(spec, certificate, checks)


def evaluate_139(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    items = data["cases"][spec["case"]]["items"]
    checks = [
        solve_discrete(data, "nonconvex", "weighted_alpha_0", alpha=0),
        solve_discrete(data, "nonconvex", "weighted_alpha_1_2", alpha="1/2"),
        solve_discrete(data, "nonconvex", "weighted_alpha_1", alpha=1),
        solve_discrete(
            data,
            "nonconvex",
            "epsilon_f2_3",
            alpha=1,
            f2_upper=3,
        ),
    ]
    certificate = {
        "epsilon_3_selection": "Q",
        "lower_convex_hull": ["P", "R"],
        "pareto_frontier": pareto_names(items),
        "Q_supported_by_weighted_sum": False,
        "score_functions": {
            "P": "4-4*alpha",
            "Q": 3,
            "R": "4*alpha",
        },
        "strict_bound": "min(S_P,S_R)<=2<3=S_Q untuk semua alpha dalam [0,1]",
    }
    return _base_result(spec, certificate, checks)


def evaluate_1310(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    lex_checks, lex_point = solve_furniture_lexicographic(
        data, "lexicographic"
    )
    weighted_checks = [
        solve_furniture_weighted(
            data, "raw_alpha_1", 1, revenue_scale="raw"
        ),
        solve_furniture_weighted(
            data, "raw_alpha_1_2", "1/2", revenue_scale="raw"
        ),
    ]
    certificate = {
        "alpha_1_optimal_edge": "80x+20y=960, dari (10,8) ke (12,0)",
        "alpha_1_not_lexicographic": "Bobot nol pada limbah tidak memutus seri pendapatan.",
        "general_finite_vertex_claim": "Selisih positif hingga pada tujuan primer memungkinkan bobot sekunder yang cukup kecil mereproduksi optimum leksikografis.",
        "lexicographic_solution": [lex_point["x"], lex_point["y"]],
        "raw_revenue_unique_threshold": "19/14019",
        "status_without_manual_solution": "verified_from_book_statement_and_independent_derivation",
    }
    return _base_result(
        spec,
        certificate,
        lex_checks + weighted_checks,
        status="verified_without_manual_solution",
    )


def evaluate_1311(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    checks = [
        solve_furniture_weighted(
            data, "scaled_alpha_1_4", "1/4", revenue_scale="thousands"
        ),
        solve_furniture_weighted(
            data, "scaled_alpha_11_20", "11/20", revenue_scale="thousands"
        ),
        solve_furniture_weighted(
            data, "scaled_alpha_4_5", "4/5", revenue_scale="thousands"
        ),
        solve_furniture_weighted(
            data, "raw_alpha_11_10000", "11/10000", revenue_scale="raw"
        ),
        solve_furniture_weighted(
            data, "raw_alpha_1_500", "1/500", revenue_scale="raw"
        ),
    ]
    certificate = {
        "breakpoint_optimal_faces": {
            "1": "sisi pendapatan-optimal dari (10,8) ke (12,0)",
            "1/2": "seluruh sisi x=0 dari (0,0) ke (0,20)",
            "19/33": "seluruh sisi rosewood dari (0,20) ke (10,8)",
        },
        "dominated_vertex_at_alpha_1": [12, 0],
        "raw_dollar_breakpoints": ["1/1001", "19/14019"],
        "scaled_intervals": {
            "(0,0)": [0, "1/2"],
            "(0,20)": ["1/2", "19/33"],
            "(10,8)": ["19/33", 1],
        },
        "vertex_values_scaled": {
            "(0,0)": "0",
            "(0,20)": "80*alpha-40",
            "(10,8)": "212*alpha-116",
            "(12,0)": "216*alpha-120",
        },
        "zero_weight_warning": "Bobot nol dapat menghasilkan titik yang tidak optimal Pareto.",
    }
    return _base_result(spec, certificate, checks)


EVALUATORS = {
    "13.1": evaluate_131,
    "13.2": evaluate_132,
    "13.3": evaluate_133,
    "13.4": evaluate_134,
    "13.5": evaluate_135,
    "13.6": evaluate_136,
    "13.7": evaluate_137,
    "13.8": evaluate_138,
    "13.9": evaluate_139,
    "13.10": evaluate_1310,
    "13.11": evaluate_1311,
}


def evaluate_all(data: dict[str, Any]) -> dict[str, Any]:
    exercises = {
        exercise_id: EVALUATORS[exercise_id](data, spec)
        for exercise_id, spec in data["exercises"].items()
    }
    checks = [
        check
        for exercise in exercises.values()
        for check in exercise["solver_checks"]
    ]
    termination_counts = Counter(
        check["termination_condition"] for check in checks
    )
    method_counts = Counter(
        exercise["method"] for exercise in exercises.values()
    )
    manual_status_counts = Counter(
        exercise["manual_mapping"]["status"]
        for exercise in exercises.values()
    )
    return {
        "authority_commit": data["authority_commit"],
        "exercises": exercises,
        "lab_id": LAB_ID,
        "manual_alignment": {
            "book_primary_ids": list(EXERCISE_IDS),
            "manual_status_counts": dict(sorted(manual_status_counts.items())),
            "missing_book_exercise_in_manual": "13.10",
            "stale_manual_alias": {"manual_id": "13.10", "book_id": "13.11"},
        },
        "provenance": data["provenance"],
        "schema_version": data["schema_version"],
        "source_defects": data["source_defects"],
        "summary": {
            "exercise_count": len(exercises),
            "manual_discrepancy_count": 2,
            "maximum_solver_violation": clean_float(
                max((float(check["maximum_violation"]) for check in checks), default=0)
            ),
            "method_counts": dict(sorted(method_counts.items())),
            "o018_math_correction_count": 0,
            "solver_call_count": len(checks),
            "solver_termination_counts": dict(sorted(termination_counts.items())),
            "source_defect_count": len(data["source_defects"]),
            "unresolved_count": len(data["unresolved_exercises"]),
            "verified_count": sum(
                exercise["status"].startswith("verified")
                for exercise in exercises.values()
            ),
        },
        "unresolved_exercises": data["unresolved_exercises"],
    }
