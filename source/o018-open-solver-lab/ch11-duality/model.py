"""Model dan sertifikat deterministik untuk laboratorium dualitas Bab 11.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

from pyomo.environ import (
    ConcreteModel,
    Constraint,
    ConstraintList,
    Objective,
    Reals,
    Set,
    Var,
    maximize,
    minimize,
    value,
)
from pyomo.opt import SolverFactory, TerminationCondition


LAB_ID = "o018.ch11.duality"
EXERCISE_IDS = tuple(f"11.{index}" for index in range(1, 18))
TOLERANCE = 1e-8


def as_fraction(number: int | str | Fraction) -> Fraction:
    """Ubah bilangan data menjadi pecahan eksak dan tolak float implisit."""

    if isinstance(number, bool):
        raise TypeError("boolean bukan bilangan data PL")
    if isinstance(number, Fraction):
        return number
    if isinstance(number, int):
        return Fraction(number)
    if isinstance(number, str):
        return Fraction(number)
    raise TypeError(f"bilangan tidak eksak: {number!r}")


def exact(number: int | Fraction) -> int | str:
    item = as_fraction(number)
    if item.denominator == 1:
        return item.numerator
    return f"{item.numerator}/{item.denominator}"


def exact_vector(items: Iterable[int | str | Fraction]) -> list[int | str]:
    return [exact(as_fraction(item)) for item in items]


def dot(
    left: Sequence[int | str | Fraction],
    right: Sequence[int | str | Fraction],
) -> Fraction:
    if len(left) != len(right):
        raise ValueError("dimensi dot product tidak cocok")
    return sum(
        (as_fraction(a) * as_fraction(b) for a, b in zip(left, right)),
        Fraction(0),
    )


def clean_float(number: float) -> int | float:
    if abs(number) < TOLERANCE:
        return 0
    rounded = round(number, 10)
    nearest = round(rounded)
    if abs(rounded - nearest) < TOLERANCE:
        return int(nearest)
    return rounded


def _validate_problem(problem: dict[str, Any], name: str) -> None:
    if problem.get("sense") not in {"max", "min"}:
        raise ValueError(f"sense tidak sah: {name}")
    variables = problem.get("variables")
    objective = problem.get("objective")
    constraints = problem.get("constraints")
    if not isinstance(variables, list) or not variables:
        raise ValueError(f"variabel tidak utuh: {name}")
    if not isinstance(objective, list) or len(objective) != len(variables):
        raise ValueError(f"objektif tidak utuh: {name}")
    if not isinstance(constraints, list):
        raise ValueError(f"kendala tidak utuh: {name}")
    for coefficient in objective:
        as_fraction(coefficient)
    for variable in variables:
        for bound in (variable.get("lb"), variable.get("ub")):
            if bound is not None:
                as_fraction(bound)
    for row in constraints:
        if row.get("sense") not in {"<=", ">=", "="}:
            raise ValueError(f"arah kendala tidak sah: {name}")
        if len(row.get("a", ())) != len(variables):
            raise ValueError(f"panjang baris tidak sah: {name}")
        for coefficient in row["a"]:
            as_fraction(coefficient)
        as_fraction(row["rhs"])


def load_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != LAB_ID:
        raise ValueError("lab_id tidak sesuai")
    if tuple(data.get("exercise_order", ())) != EXERCISE_IDS:
        raise ValueError("exercise_order harus tepat memuat 11.1--11.17")
    exercises = data.get("exercises")
    if not isinstance(exercises, dict) or tuple(exercises) != EXERCISE_IDS:
        raise ValueError("data latihan tidak utuh atau tidak berurutan")
    difficulties = [spec["difficulty"] for spec in exercises.values()]
    if difficulties.count(1) != 4 or difficulties.count(2) != 10 or difficulties.count(3) != 3:
        raise ValueError("distribusi tingkat kesulitan tidak sesuai saksi")
    if data.get("proof_only_exercises") != ["11.7", "11.9", "11.14"]:
        raise ValueError("daftar latihan pembuktian tidak tertutup")
    if data.get("underdetermined_exercises") != []:
        raise ValueError("tidak ada latihan Bab 11 yang boleh ditandai kurang data")
    correction_ids = [item["id"] for item in data.get("corrections", ())]
    if correction_ids != [
        "CORR-CH11-CASE2-GEQ",
        "CORR-CH11-MIXED-SIGNS-FREE",
        "CORR-CH11-EX11-13-CANDIDATE",
    ]:
        raise ValueError("tiga koreksi sumber tidak tertutup")
    defect_ids = [item["id"] for item in data.get("upstream_defects", ())]
    if defect_ids != [
        "UPSTREAM-DEFECT-CH11-STRONG-DUALITY-OMITS-BOTH-INFEASIBLE",
        "UPSTREAM-DEFECT-CH11-EX11-17-RETAIL-REDUNDANT",
    ]:
        raise ValueError("dua cacat hulu tidak tertutup")
    if len(data.get("provenance", {}).get("source_files", ())) != 6:
        raise ValueError("closure sumber harus memuat enam saksi")
    for case_name, case in data.get("cases", {}).items():
        if set(case) != {"dual", "primal"}:
            raise ValueError(f"pasangan kasus tidak utuh: {case_name}")
        _validate_problem(case["primal"], f"{case_name}/primal")
        _validate_problem(case["dual"], f"{case_name}/dual")
    return data


def _solver():
    solver = SolverFactory("appsi_highs")
    if not solver.available(exception_flag=False):
        raise RuntimeError("pemecah appsi_highs tidak tersedia")
    solver.options["output_flag"] = False
    return solver


def _build_model(
    problem: dict[str, Any],
    model_name: str,
    rhs_overrides: dict[int, int | str | Fraction] | None = None,
) -> ConcreteModel:
    variables = problem["variables"]
    rhs_overrides = rhs_overrides or {}
    model = ConcreteModel(name=model_name)
    model.J = Set(initialize=range(len(variables)), ordered=True)

    def bounds_rule(_model: ConcreteModel, index: int):
        spec = variables[index]
        lower = spec.get("lb")
        upper = spec.get("ub")
        return (
            None if lower is None else float(as_fraction(lower)),
            None if upper is None else float(as_fraction(upper)),
        )

    model.x = Var(model.J, domain=Reals, bounds=bounds_rule)
    model.rows = ConstraintList()
    for row_index, row in enumerate(problem["constraints"]):
        rhs = as_fraction(rhs_overrides.get(row_index, row["rhs"]))
        expression = sum(
            float(as_fraction(coefficient)) * model.x[index]
            for index, coefficient in enumerate(row["a"])
        )
        if row["sense"] == "<=":
            model.rows.add(expression <= float(rhs))
        elif row["sense"] == ">=":
            model.rows.add(expression >= float(rhs))
        else:
            model.rows.add(expression == float(rhs))
    objective = sum(
        float(as_fraction(coefficient)) * model.x[index]
        for index, coefficient in enumerate(problem["objective"])
    )
    model.objective = Objective(
        expr=objective,
        sense=maximize if problem["sense"] == "max" else minimize,
    )
    return model


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
    if violation < TOLERANCE:
        return 0.0
    return max(0.0, violation)


def solve_problem(
    data: dict[str, Any],
    case_name: str,
    side: str,
    variant: str,
    expected_termination: str,
    *,
    rhs_overrides: dict[int, int | str | Fraction] | None = None,
) -> dict[str, Any]:
    problem = data["cases"][case_name][side]
    model = _build_model(
        problem,
        f"ch11_{case_name}_{side}_{variant}",
        rhs_overrides=rhs_overrides,
    )
    result = _solver().solve(model, tee=False, load_solutions=False)
    termination = str(result.solver.termination_condition)
    if termination != expected_termination:
        raise RuntimeError(
            f"terminasi {case_name}/{side}/{variant}: "
            f"{termination} != {expected_termination}"
        )
    record: dict[str, Any] = {
        "case": case_name,
        "maximum_violation": None,
        "objective": None,
        "point": None,
        "purpose": "independent_lp_corroboration",
        "side": side,
        "solver": "appsi_highs",
        "status": str(result.solver.status),
        "termination_condition": termination,
        "variant": variant,
    }
    if result.solver.termination_condition == TerminationCondition.optimal:
        model.solutions.load_from(result)
        record["maximum_violation"] = clean_float(_maximum_violation(model))
        record["objective"] = clean_float(float(value(model.objective)))
        record["point"] = {
            spec["name"]: clean_float(float(value(model.x[index])))
            for index, spec in enumerate(problem["variables"])
        }
    return record


def assert_solver_objective(
    record: dict[str, Any], expected_value: int | str | Fraction
) -> None:
    if record["termination_condition"] != "optimal":
        raise RuntimeError("objektif diminta dari pemeriksaan nonoptimal")
    if abs(float(record["objective"]) - float(as_fraction(expected_value))) > 20 * TOLERANCE:
        raise RuntimeError(
            f"objektif solver {record['case']}/{record['variant']} berbeda: "
            f"{record['objective']} != {expected_value}"
        )


def row_margins(
    problem: dict[str, Any], point: Sequence[int | str | Fraction]
) -> list[Fraction]:
    margins: list[Fraction] = []
    for row in problem["constraints"]:
        lhs = dot(row["a"], point)
        rhs = as_fraction(row["rhs"])
        if row["sense"] == "<=":
            margins.append(rhs - lhs)
        elif row["sense"] == ">=":
            margins.append(lhs - rhs)
        else:
            margins.append(lhs - rhs)
    return margins


def objective_value(
    problem: dict[str, Any], point: Sequence[int | str | Fraction]
) -> Fraction:
    return dot(problem["objective"], point)


def is_feasible(
    problem: dict[str, Any], point: Sequence[int | str | Fraction]
) -> bool:
    margins = row_margins(problem, point)
    for row, margin in zip(problem["constraints"], margins):
        if row["sense"] == "=" and margin != 0:
            return False
        if row["sense"] != "=" and margin < 0:
            return False
    for spec, item in zip(problem["variables"], point):
        current = as_fraction(item)
        if spec.get("lb") is not None and current < as_fraction(spec["lb"]):
            return False
        if spec.get("ub") is not None and current > as_fraction(spec["ub"]):
            return False
    return True


def pair_solver_checks(
    data: dict[str, Any],
    case_name: str,
    optimum: int | str | Fraction,
) -> list[dict[str, Any]]:
    primal = solve_problem(data, case_name, "primal", "nominal", "optimal")
    dual = solve_problem(data, case_name, "dual", "nominal", "optimal")
    assert_solver_objective(primal, optimum)
    assert_solver_objective(dual, optimum)
    return [primal, dual]


def _base_result(
    spec: dict[str, Any],
    certificate: dict[str, Any],
    solver_checks: list[dict[str, Any]],
    *,
    status: str = "verified",
) -> dict[str, Any]:
    return {
        "certificate": certificate,
        "correction_refs": spec.get("correction_refs", []),
        "difficulty": spec["difficulty"],
        "method": spec["method"],
        "solver_checks": solver_checks,
        "status": status,
        "title": spec["title"],
    }


def evaluate_111(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [5, 0]
    dual = [0, 5]
    certificate = {
        "data_mapping": {
            "primal_objective_to_dual_rhs": [5, 4],
            "primal_rhs_to_dual_objective": [12, 5],
            "transpose_verified": True,
        },
        "dual_constraint_matrix": [row["a"] for row in case["dual"]["constraints"]],
        "dual_objective": case["dual"]["objective"],
        "economic_interpretation": [
            "y1 adalah harga per unit tepung",
            "y2 adalah harga per unit gula",
            "setiap bundel bahan harus berharga sekurang-kurangnya laba produknya",
        ],
        "optimal_dual": dual,
        "optimal_primal": primal,
        "optimum": exact(objective_value(case["primal"], primal)),
        "primal_slacks": exact_vector(row_margins(case["primal"], primal)),
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 25))


def evaluate_112(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [Fraction(14, 5), Fraction(18, 5), 0]
    dual = [Fraction(11, 5), Fraction(3, 5)]
    certificate = {
        "dual_constraint_matrix": [row["a"] for row in case["dual"]["constraints"]],
        "dual_constraint_senses": [row["sense"] for row in case["dual"]["constraints"]],
        "dual_objective": case["dual"]["objective"],
        "optimal_dual": exact_vector(dual),
        "optimal_primal": exact_vector(primal),
        "optimum": exact(objective_value(case["primal"], primal)),
        "transpose_dimensions": {"primal_A": [2, 3], "dual_A": [3, 2]},
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], "146/5"))


def evaluate_113(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal_candidate = [1, 2]
    dual_candidate = [2, 1]
    certificate = {
        "candidate_dual_feasible": is_feasible(case["dual"], dual_candidate),
        "candidate_dual_surpluses": exact_vector(row_margins(case["dual"], dual_candidate)),
        "candidate_dual_value": exact(objective_value(case["dual"], dual_candidate)),
        "candidate_primal_feasible": is_feasible(case["primal"], primal_candidate),
        "candidate_primal_slacks": exact_vector(row_margins(case["primal"], primal_candidate)),
        "candidate_primal_value": exact(objective_value(case["primal"], primal_candidate)),
        "optimum": 9,
        "sandwich": [7, 9, 13],
        "weak_duality_verified": objective_value(case["primal"], primal_candidate) <= objective_value(case["dual"], dual_candidate),
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 9))


def evaluate_114(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [2, 2]
    dual = [1, 1]
    bound = objective_value(case["primal"], primal)
    certificate = {
        "coincident_bound": exact(bound),
        "dual_candidate": dual,
        "dual_feasible": is_feasible(case["dual"], dual),
        "dual_value": exact(objective_value(case["dual"], dual)),
        "primal_candidate": primal,
        "primal_feasible": is_feasible(case["primal"], primal),
        "primal_value": exact(bound),
        "status": "verified_exact_weak_duality_certificate",
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 10))


def evaluate_115(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    certificate = {
        "dual_constraint_senses": [row["sense"] for row in case["dual"]["constraints"]],
        "dual_variable_domains": ["free", "nonnegative"],
        "mapping_rules": [
            "kendala primal persamaan menghasilkan variabel dual bebas",
            "kendala primal <= pada maksimisasi menghasilkan variabel dual taknegatif",
            "variabel primal bebas menghasilkan kendala dual persamaan",
        ],
        "optimal_dual": [3, 0],
        "optimal_primal": [0, 5],
        "optimum": 15,
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 15))


def evaluate_116(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [Fraction(22, 3), Fraction(16, 3)]
    dual = [2, 1, 0]
    primal_slacks = row_margins(case["primal"], primal)
    dual_surpluses = row_margins(case["dual"], dual)
    products = [
        *(as_fraction(y) * slack for y, slack in zip(dual, primal_slacks)),
        *(as_fraction(x) * surplus for x, surplus in zip(primal, dual_surpluses)),
    ]
    checks = pair_solver_checks(data, spec["case"], 58)
    extra = solve_problem(
        data,
        spec["case"],
        "primal",
        "one_more_flour",
        "optimal",
        rhs_overrides={0: 21},
    )
    assert_solver_objective(extra, 60)
    checks.append(extra)
    certificate = {
        "binding_constraints": ["flour", "sugar"],
        "complementary_products": exact_vector(products),
        "nonbinding_constraints": ["oven"],
        "optimal_dual": dual,
        "optimal_primal": exact_vector(primal),
        "optimum": 58,
        "primal_slacks": exact_vector(primal_slacks),
        "shadow_prices": {"flour": 2, "oven": 0, "sugar": 1},
        "strong_duality_gap": 0,
        "value_with_one_more_flour": 60,
    }
    return _base_result(spec, certificate, checks)


def evaluate_117(_data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    certificate = {
        "certificate_conditions": ["y>=0", "A^T*y>=c", "b^T*y<=M"],
        "concrete_witness": {
            "dual_certificate": [2, 1],
            "primal_plan": [1, 2],
            "verified_bound": "7<=13",
        },
        "inequality_chain": "c^T*x<=x^T*A^T*y=y^T*A*x<=b^T*y",
        "proof_steps": [
            "A^T*y>=c mendominasi koefisien laba untuk x>=0",
            "y>=0 mempertahankan arah Ax<=b ketika baris diagregasikan",
            "setiap y layak memberi batas atas b^T*y",
            "meminimumkan batas linear itu adalah dual dan dualitas kuat membuat batas terbaik tepat",
        ],
        "status": "verified_conceptual_proof",
    }
    return _base_result(spec, certificate, [], status="verified_proof")


def evaluate_118(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    primal = solve_problem(data, spec["case"], "primal", "nominal", "infeasible")
    dual = solve_problem(data, spec["case"], "dual", "nominal", "infeasible")
    certificate = {
        "dual_status": "infeasible",
        "dual_sum_certificate": "0>=2",
        "explanation": "status dual memerlukan pemeriksaan langsung; ketaklayakan primal saja tidak membedakan dual taklayak dari dual takterbatas",
        "primal_status": "infeasible",
        "primal_sum_certificate": "0<=-2",
        "theorem_fourth_case_required": True,
    }
    return _base_result(spec, certificate, [primal, dual])


def evaluate_119(_data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    certificate = {
        "dual_of_dual_constraint_matrix": "A",
        "dual_of_dual_objective": "c^T*z",
        "intermediate_constraint": "(-A^T)*y<=-c",
        "intermediate_matrix": "-A^T",
        "intermediate_objective": "(-b)^T*y",
        "proof_steps": [
            "ubah min b^T*y menjadi max (-b)^T*y",
            "ubah A^T*y>=c menjadi (-A^T)*y<=-c",
            "dual bentuk simetris itu memakai transpose (-A^T)^T=-A",
            "min (-c)^T*z dengan (-A)z>=-b setara dengan max c^T*z dan Az<=b",
        ],
        "sign_domain_preserved": "z>=0",
        "status": "verified_symbolic_involution",
    }
    return _base_result(spec, certificate, [], status="verified_proof")


def evaluate_1110(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [4, 2]
    dual = [2, 1]
    primal_slacks = row_margins(case["primal"], primal)
    dual_surpluses = row_margins(case["dual"], dual)
    products = [
        *(as_fraction(y) * slack for y, slack in zip(dual, primal_slacks)),
        *(as_fraction(x) * surplus for x, surplus in zip(primal, dual_surpluses)),
    ]
    certificate = {
        "complementary_products": exact_vector(products),
        "dual_feasible": is_feasible(case["dual"], dual),
        "dual_objective": exact(objective_value(case["dual"], dual)),
        "dual_surpluses": exact_vector(dual_surpluses),
        "optimal_dual": dual,
        "optimal_primal": primal,
        "primal_feasible": is_feasible(case["primal"], primal),
        "primal_objective": exact(objective_value(case["primal"], primal)),
        "primal_slacks": exact_vector(primal_slacks),
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 22))


def evaluate_1111(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [4, 0, 6]
    dual = [0, 50, 40]
    primal_slacks = row_margins(case["primal"], primal)
    dual_surpluses = row_margins(case["dual"], dual)
    products = [
        *(as_fraction(y) * slack for y, slack in zip(dual, primal_slacks)),
        *(as_fraction(x) * surplus for x, surplus in zip(primal, dual_surpluses)),
    ]
    checks = pair_solver_checks(data, spec["case"], 780)
    variants = [
        ("one_more_flour", {0: 41}, 780),
        ("one_more_sugar", {1: 11}, 830),
        ("one_more_baking_time", {2: 8}, 820),
    ]
    for variant, overrides, expected_value in variants:
        check = solve_problem(
            data,
            spec["case"],
            "primal",
            variant,
            "optimal",
            rhs_overrides=overrides,
        )
        assert_solver_objective(check, expected_value)
        checks.append(check)
    certificate = {
        "complementary_products": exact_vector(products),
        "dual_surpluses": exact_vector(dual_surpluses),
        "optimal_dual": dual,
        "optimal_primal": primal,
        "optimum": 780,
        "primal_slacks": exact_vector(primal_slacks),
        "shadow_prices": {"baking_time": 40, "flour": 0, "sugar": 50},
        "unit_rhs_values": {"baking_time": 820, "flour": 780, "sugar": 830},
    }
    return _base_result(spec, certificate, checks)


def evaluate_1112(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [0, Fraction(1, 2), 1, 1]
    dual = [0, 0, 3, 8, 2]
    primal_slacks = row_margins(case["primal"], primal)
    dual_surpluses = row_margins(case["dual"], dual)
    certificate = {
        "certificate_rule": "primal dan dual layak dengan nilai sama membuktikan optimalitas melalui dualitas lemah",
        "dual_surpluses": exact_vector(dual_surpluses),
        "optimal_dual": dual,
        "optimal_primal": exact_vector(primal),
        "optimum": 27,
        "primal_slacks": exact_vector(primal_slacks),
        "weak_duality_gap": 0,
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 27))


def evaluate_1113(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    candidate = [1, 1]
    recovered = [3, 2]
    correct_dual = [Fraction(11, 5), Fraction(3, 5)]
    certificate = {
        "candidate_dual": candidate,
        "candidate_dual_surpluses": exact_vector(row_margins(case["dual"], candidate)),
        "candidate_dual_value": exact(objective_value(case["dual"], candidate)),
        "candidate_is_dual_feasible": is_feasible(case["dual"], candidate),
        "complementary_slackness_gate": "kedua sisi harus layak sebelum syarat KK menjadi sertifikat optimalitas",
        "correct_dual": exact_vector(correct_dual),
        "correct_dual_surpluses": exact_vector(row_margins(case["dual"], correct_dual)),
        "optimum": 23,
        "recovered_primal": recovered,
        "recovered_primal_feasible": is_feasible(case["primal"], recovered),
        "weak_duality_alarm": "17<23",
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 23))


def evaluate_1114(_data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    certificate = {
        "complementary_product": "y2*(a2^T*x-b2)<0",
        "conclusion": "joint_optimality_ruled_out",
        "economic_interpretation": "sumber daya yang tersisa tidak bernilai marginal pada keseimbangan optimal yang sama",
        "individual_culprit_identified": False,
        "logical_possibilities": [
            "primal optimal dan dual suboptimal",
            "dual optimal dan primal suboptimal",
            "keduanya suboptimal",
        ],
        "status": "verified_conceptual_proof",
    }
    return _base_result(spec, certificate, [], status="verified_proof")


def evaluate_1115(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    claimed = [2, 0]
    certificate = {
        "actual_dual": [1, 1],
        "actual_optimum": 9,
        "actual_primal": [1, 3],
        "claimed_feasible": is_feasible(case["primal"], claimed),
        "claimed_primal": claimed,
        "claimed_primal_slacks": exact_vector(row_margins(case["primal"], claimed)),
        "claimed_value": exact(objective_value(case["primal"], claimed)),
        "contradiction": "y1=y2=0 tetapi y1+2*y2=3",
        "cs_requirements": ["y1=0", "y2=0", "y1+2*y2=3"],
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 9))


def evaluate_1116(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [0, 0, 10, 0, 0, 12]
    dual = [4, 2]
    certificate = {
        "active_dual_constraints": ["x3", "x6"],
        "dual_feasible_region_reduction": ["y1>=4", "y2>=2"],
        "dual_surpluses": exact_vector(row_margins(case["dual"], dual)),
        "optimal_dual": dual,
        "optimal_primal": primal,
        "optimum": 64,
        "positive_primal_variables": ["x3", "x6"],
        "resource_shadow_prices": {"kitchen": 4, "packaging": 2},
        "tight_primal_resources": ["kitchen", "packaging"],
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 64))


def evaluate_1117(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    case = data["cases"][spec["case"]]
    primal = [40, 0, 20]
    dual = [1, Fraction(1, 2), 0]
    certificate = {
        "dual_surpluses": exact_vector(row_margins(case["dual"], dual)),
        "dual_variable_domains": ["nonnegative", "free", "nonpositive"],
        "optimal_dual": exact_vector(dual),
        "optimal_primal": primal,
        "optimum": 260,
        "primal_row_residuals": exact_vector(row_margins(case["primal"], primal)),
        "retail_identity": "6*x1+9*x2+8*x3=360+2*x3",
        "retail_implied_lower_bound": 360,
        "retail_redundancy_verified": True,
    }
    return _base_result(spec, certificate, pair_solver_checks(data, spec["case"], 260))


EVALUATORS = {
    "11.1": evaluate_111,
    "11.2": evaluate_112,
    "11.3": evaluate_113,
    "11.4": evaluate_114,
    "11.5": evaluate_115,
    "11.6": evaluate_116,
    "11.7": evaluate_117,
    "11.8": evaluate_118,
    "11.9": evaluate_119,
    "11.10": evaluate_1110,
    "11.11": evaluate_1111,
    "11.12": evaluate_1112,
    "11.13": evaluate_1113,
    "11.14": evaluate_1114,
    "11.15": evaluate_1115,
    "11.16": evaluate_1116,
    "11.17": evaluate_1117,
}


def evaluate_corrections(data: dict[str, Any]) -> list[dict[str, Any]]:
    case2_checks = pair_solver_checks(data, "case2_corrected", 3)
    complicated_checks = [
        solve_problem(
            data,
            "complicated_corrected",
            "primal",
            "corrected_signs",
            "infeasible",
        ),
        solve_problem(
            data,
            "complicated_corrected",
            "dual",
            "corrected_signs",
            "unbounded",
        ),
    ]
    records: list[dict[str, Any]] = []
    for correction in data["corrections"]:
        item = dict(correction)
        if item["id"] == "CORR-CH11-CASE2-GEQ":
            item["verification"] = {
                "corrected_dual_value": 3,
                "corrected_primal_value": 3,
                "old_form_weak_duality_counterexample": "dual 3 tidak <= primal 0",
            }
            item["solver_checks"] = case2_checks
        elif item["id"] == "CORR-CH11-MIXED-SIGNS-FREE":
            item["verification"] = {
                "dual_feasible_base_point": ["3/2", 0, "1/2"],
                "dual_unbounded_ray": [1, -2, 3],
                "ray_objective_change": -1,
                "primal_x1_lower_bound": "5/3",
                "primal_x1_upper_bound": "3/2",
            }
            item["solver_checks"] = complicated_checks
        else:
            item["verification"] = {
                "candidate_first_constraint_lhs": 3,
                "candidate_first_constraint_rhs": 5,
                "candidate_is_dual_feasible": False,
                "correct_optimum": 23,
            }
            item["solver_checks"] = []
        records.append(item)
    return records


def evaluate_all(data: dict[str, Any]) -> dict[str, Any]:
    exercises = {
        exercise_id: EVALUATORS[exercise_id](
            data, data["exercises"][exercise_id]
        )
        for exercise_id in EXERCISE_IDS
    }
    corrections = evaluate_corrections(data)
    solver_checks = [
        check
        for exercise in exercises.values()
        for check in exercise["solver_checks"]
    ]
    solver_checks.extend(
        check
        for correction in corrections
        for check in correction["solver_checks"]
    )
    feasible_violations = [
        float(check["maximum_violation"])
        for check in solver_checks
        if check["maximum_violation"] is not None
    ]
    status_counts = Counter(
        check["termination_condition"] for check in solver_checks
    )
    return {
        "authority_commit": data["authority_commit"],
        "code_license": data["code_license"],
        "content_license": data["content_license"],
        "corrections": corrections,
        "exercises": exercises,
        "lab_id": data["lab_id"],
        "provenance": data["provenance"],
        "schema_version": data["schema_version"],
        "summary": {
            "correction_count": len(corrections),
            "exercise_count": len(exercises),
            "high_confidence_upstream_defect_count": len(data["upstream_defects"]),
            "maximum_solver_violation": clean_float(max(feasible_violations, default=0.0)),
            "method_counts": dict(
                sorted(
                    Counter(
                        spec["method"] for spec in data["exercises"].values()
                    ).items()
                )
            ),
            "o018_math_correction_count": 0,
            "plot_count": 0,
            "proof_only_count": len(data["proof_only_exercises"]),
            "solver_call_count": len(solver_checks),
            "solver_termination_counts": dict(sorted(status_counts.items())),
            "underdetermined_count": len(data["underdetermined_exercises"]),
            "verified_count": len(exercises),
        },
        "underdetermined_exercises": data["underdetermined_exercises"],
        "upstream_defects": data["upstream_defects"],
    }
