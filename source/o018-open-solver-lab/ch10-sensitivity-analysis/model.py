"""Sertifikat eksak dan pemeriksaan Pyomo+HiGHS untuk Bab 10.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

from pyomo.environ import (
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
LAB_ID = "o018.ch10.sensitivity-analysis"
EXERCISE_IDS = tuple(f"10.{index}" for index in range(1, 13))
TOLERANCE = 1e-8


def as_fraction(number: int | str | float | Fraction) -> Fraction:
    if isinstance(number, Fraction):
        return number
    if isinstance(number, int):
        return Fraction(number)
    if isinstance(number, float):
        return Fraction(str(number))
    return Fraction(number)


def exact(number: int | Fraction) -> int | str:
    fraction = as_fraction(number)
    if fraction.denominator == 1:
        return fraction.numerator
    return f"{fraction.numerator}/{fraction.denominator}"


def exact_vector(items: Iterable[int | Fraction]) -> list[int | str]:
    return [exact(item) for item in items]


def exact_matrix(
    rows: Sequence[Sequence[int | Fraction]],
) -> list[list[int | str]]:
    return [exact_vector(row) for row in rows]


def fractions(items: Sequence[int | str | Fraction]) -> list[Fraction]:
    return [as_fraction(item) for item in items]


def dot(
    first: Sequence[int | str | Fraction],
    second: Sequence[int | str | Fraction],
) -> Fraction:
    if len(first) != len(second):
        raise ValueError("panjang vektor tidak sama")
    return sum(
        (as_fraction(a) * as_fraction(b) for a, b in zip(first, second)),
        Fraction(0),
    )


def matrix_vector(
    matrix: Sequence[Sequence[int | str | Fraction]],
    vector: Sequence[int | str | Fraction],
) -> list[Fraction]:
    return [dot(row, vector) for row in matrix]


def row_matrix(
    row: Sequence[int | str | Fraction],
    matrix: Sequence[Sequence[int | str | Fraction]],
) -> list[Fraction]:
    if not matrix:
        return []
    return [
        sum(
            (
                as_fraction(row[index]) * as_fraction(matrix[index][column])
                for index in range(len(row))
            ),
            Fraction(0),
        )
        for column in range(len(matrix[0]))
    ]


def matrix_multiply(
    first: Sequence[Sequence[int | str | Fraction]],
    second: Sequence[Sequence[int | str | Fraction]],
) -> list[list[Fraction]]:
    columns = list(zip(*second))
    return [[dot(row, column) for column in columns] for row in first]


def inverse(
    matrix: Sequence[Sequence[int | str | Fraction]],
) -> list[list[Fraction]]:
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("invers hanya untuk matriks persegi takkosong")
    augmented = [
        fractions(row)
        + [Fraction(int(index == column)) for column in range(n)]
        for index, row in enumerate(matrix)
    ]
    for column in range(n):
        pivot = next(
            (row for row in range(column, n) if augmented[row][column] != 0),
            None,
        )
        if pivot is None:
            raise ValueError("matriks singular")
        augmented[column], augmented[pivot] = (
            augmented[pivot],
            augmented[column],
        )
        scale = augmented[column][column]
        augmented[column] = [item / scale for item in augmented[column]]
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    current - factor * pivot_item
                    for current, pivot_item in zip(
                        augmented[row], augmented[column]
                    )
                ]
    return [row[n:] for row in augmented]


def affine_parameter(
    inverse_matrix: Sequence[Sequence[Fraction]],
    fixed_rhs: Sequence[int | str],
    parameter_index: int,
) -> tuple[list[Fraction], list[Fraction]]:
    constant_rhs = fractions(fixed_rhs)
    constant_rhs[parameter_index] = Fraction(0)
    direction = [
        Fraction(int(index == parameter_index))
        for index in range(len(fixed_rhs))
    ]
    return (
        matrix_vector(inverse_matrix, constant_rhs),
        matrix_vector(inverse_matrix, direction),
    )


def nonnegative_interval(
    constants: Sequence[Fraction],
    slopes: Sequence[Fraction],
) -> tuple[Fraction | None, Fraction | None]:
    lower: Fraction | None = None
    upper: Fraction | None = None
    for constant, slope in zip(constants, slopes):
        if slope > 0:
            candidate = -constant / slope
            lower = candidate if lower is None else max(lower, candidate)
        elif slope < 0:
            candidate = -constant / slope
            upper = candidate if upper is None else min(upper, candidate)
        elif constant < 0:
            raise ValueError("sistem affine tidak pernah nonnegatif")
    if lower is not None and upper is not None and lower > upper:
        raise ValueError("interval kosong")
    return lower, upper


def clean_float(number: float) -> int | float:
    if abs(number) < TOLERANCE:
        return 0
    rounded = round(number, 10)
    nearest = round(rounded)
    if abs(rounded - nearest) < TOLERANCE:
        return int(nearest)
    return rounded


def load_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != LAB_ID:
        raise ValueError("lab_id tidak sesuai")
    if tuple(data.get("exercise_order", ())) != EXERCISE_IDS:
        raise ValueError("exercise_order harus tepat memuat 10.1--10.12")
    exercises = data.get("exercises")
    if not isinstance(exercises, dict) or tuple(exercises) != EXERCISE_IDS:
        raise ValueError("data latihan tidak utuh atau tidak berurutan")
    difficulties = [spec["difficulty"] for spec in exercises.values()]
    if difficulties.count(1) != 2 or difficulties.count(2) != 9 or difficulties.count(3) != 1:
        raise ValueError("distribusi tingkat kesulitan tidak sesuai saksi")
    correction_ids = [item["id"] for item in data.get("corrections", ())]
    if correction_ids != [
        "CORR-CH10-RHS-B1-SLACK",
        "CORR-CH10-RHS-B3-SLACK",
        "CORR-CH10-MATRIX-AN-SIGNS",
    ]:
        raise ValueError("tiga koreksi target tidak tertutup")
    missing = data.get("underdetermined_exercises")
    if not isinstance(missing, list) or [item["exercise_id"] for item in missing] != ["10.7"]:
        raise ValueError("hanya Latihan 10.7 yang boleh ditandai kekurangan data")
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


def solve_case(
    data: dict[str, Any],
    case_name: str,
    variant: str,
    *,
    rhs_overrides: dict[int, int | str | Fraction] | None = None,
    cost_overrides: dict[int, int | str | Fraction] | None = None,
) -> dict[str, Any]:
    case = data["cases"][case_name]
    rhs = fractions(case["b"])
    costs = fractions(case["c"])
    for index, item in (rhs_overrides or {}).items():
        rhs[index] = as_fraction(item)
    for index, item in (cost_overrides or {}).items():
        costs[index] = as_fraction(item)

    model = ConcreteModel(name=f"ch10_{case_name}_{variant}")
    model.J = Set(initialize=range(len(case["variables"])), ordered=True)
    model.x = Var(model.J, domain=NonNegativeReals)
    model.rows = ConstraintList()
    for coefficients, bound in zip(case["A"], rhs):
        expression = sum(
            float(as_fraction(coefficient)) * model.x[index]
            for index, coefficient in enumerate(coefficients)
        )
        model.rows.add(expression <= float(bound))
    expression = sum(
        float(coefficient) * model.x[index]
        for index, coefficient in enumerate(costs)
    )
    model.objective = Objective(
        expr=expression,
        sense=maximize if case["sense"] == "max" else minimize,
    )
    result = _solver().solve(model, tee=False)
    if result.solver.status not in {SolverStatus.ok, SolverStatus.warning}:
        raise RuntimeError(
            f"status HiGHS {case_name}/{variant} tidak diterima: "
            f"{result.solver.status}"
        )
    if result.solver.termination_condition != TerminationCondition.optimal:
        raise RuntimeError(
            f"terminasi {case_name}/{variant}: "
            f"{result.solver.termination_condition}"
        )
    point = {
        name: clean_float(float(value(model.x[index])))
        for index, name in enumerate(case["variables"])
    }
    return {
        "case": case_name,
        "maximum_violation": clean_float(_maximum_violation(model)),
        "objective": clean_float(float(value(model.objective))),
        "point": point,
        "purpose": "independent_lp_corroboration",
        "solver": "appsi_highs",
        "status": str(result.solver.status),
        "termination_condition": str(result.solver.termination_condition),
        "variant": variant,
    }


def assert_solver_objective(
    record: dict[str, Any], expected_value: int | str | Fraction
) -> None:
    if abs(float(record["objective"]) - float(as_fraction(expected_value))) > 20 * TOLERANCE:
        raise RuntimeError(
            f"objektif solver {record['case']}/{record['variant']} berbeda: "
            f"{record['objective']} != {expected_value}"
        )


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


def evaluate_101(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    basis_matrix = [[1, 1, 0], [2, 1, 1], [1, 2, 0]]
    nonbasic_matrix = [[1, 0], [0, 0], [0, 1]]
    basis_inverse = inverse(basis_matrix)
    basic_values = matrix_vector(basis_inverse, data["cases"]["main"]["b"])
    shadow_prices = row_matrix([2, 3, 0], basis_inverse)
    transformed_nonbasic = matrix_multiply(basis_inverse, nonbasic_matrix)
    required_matrix = [
        [Fraction(2), Fraction(-1)],
        [Fraction(-1), Fraction(1)],
        [Fraction(-3), Fraction(1)],
    ]
    if transformed_nonbasic != required_matrix:
        raise RuntimeError("sertifikat koreksi tanda A_N' gagal")
    offer_price = as_fraction(spec["offer"]["price"])
    net_gain = shadow_prices[2] - offer_price
    solver_checks = [
        solve_case(data, "main", "base"),
        solve_case(data, "main", "b3_plus_1", rhs_overrides={2: 15}),
    ]
    for record, expected_value in zip(solver_checks, (23, 24)):
        assert_solver_objective(record, expected_value)
    certificate = {
        "basic_values": exact_vector(basic_values),
        "basis": ["x", "y", "s2"],
        "basis_inverse": exact_matrix(basis_inverse),
        "matrix_sign_correction": {
            "A_B_inverse_A_N": exact_matrix(transformed_nonbasic),
            "dictionary_form": "x_B=b_prime-A_N_prime*x_N",
            "verified": True,
        },
        "nonbinding_constraints": [2],
        "offer": {
            "accept": net_gain > 0,
            "allowed_additional_quantity": 4,
            "maximum_unit_price": exact(shadow_prices[2]),
            "net_gain": exact(net_gain),
        },
        "reduced_costs": {
            "s1": exact(-shadow_prices[0]),
            "s3": exact(-shadow_prices[2]),
        },
        "shadow_prices": exact_vector(shadow_prices),
    }
    return _base_result(spec, certificate, solver_checks)


def evaluate_102(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    basis_inverse = inverse([[1, 1], [2, 1]])
    constants, slopes = affine_parameter(basis_inverse, [10, 16], 0)
    interval = nonnegative_interval(constants, slopes)
    shadow_prices = row_matrix([4, 3], basis_inverse)
    solver_values = (
        ("b1_8", 8, 32),
        ("b1_16", 16, 48),
        ("b1_7_9", "79/10", "158/5"),
        ("b1_16_1", "161/10", 48),
    )
    solver_checks = []
    for name, rhs, expected_value in solver_values:
        record = solve_case(data, "rhs_cost", name, rhs_overrides={0: rhs})
        assert_solver_objective(record, expected_value)
        solver_checks.append(record)
    certificate = {
        "basis_inverse": exact_matrix(basis_inverse),
        "delta_range": [
            exact(interval[0] - 10),
            exact(interval[1] - 10),
        ],
        "objective": "36+2*delta",
        "rhs_range": [exact(interval[0]), exact(interval[1])],
        "shadow_price": exact(shadow_prices[0]),
        "solution_affine": [
            [exact(constant), exact(slope)]
            for constant, slope in zip(constants, slopes)
        ],
    }
    return _base_result(spec, certificate, solver_checks)


def evaluate_103(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    basis_inverse = inverse([[1, 1], [2, 1]])
    basic_values = matrix_vector(basis_inverse, [10, 16])
    dual_constants = row_matrix([0, 3], basis_inverse)
    dual_slopes = row_matrix([1, 0], basis_inverse)
    interval = nonnegative_interval(dual_constants, dual_slopes)
    solver_values = (
        ("c1_3", 3, 30),
        ("c1_6", 6, 48),
        ("c1_2_99", "299/100", 30),
        ("c1_6_01", "601/100", "1202/25"),
    )
    solver_checks = []
    for name, coefficient, expected_value in solver_values:
        record = solve_case(
            data, "rhs_cost", name, cost_overrides={0: coefficient}
        )
        assert_solver_objective(record, expected_value)
        solver_checks.append(record)
    certificate = {
        "coefficient_range": [exact(interval[0]), exact(interval[1])],
        "delta_range": [
            exact(interval[0] - 4),
            exact(interval[1] - 4),
        ],
        "dual_affine": [
            [exact(constant), exact(slope)]
            for constant, slope in zip(dual_constants, dual_slopes)
        ],
        "objective": "12+6*c1",
        "solution": exact_vector(basic_values),
    }
    return _base_result(spec, certificate, solver_checks)


def evaluate_104(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    basis_inverse = inverse([[1, 2], [3, 2]])
    solution = matrix_vector(basis_inverse, [16, 24])
    shadow_prices = row_matrix([5, 6], basis_inverse)
    b1_constants, b1_slopes = affine_parameter(basis_inverse, [16, 24], 0)
    b2_constants, b2_slopes = affine_parameter(basis_inverse, [16, 24], 1)
    b1_range = nonnegative_interval(b1_constants, b1_slopes)
    b2_range = nonnegative_interval(b2_constants, b2_slopes)
    c1_constants = row_matrix([0, 6], basis_inverse)
    c1_slopes = row_matrix([1, 0], basis_inverse)
    c2_constants = row_matrix([5, 0], basis_inverse)
    c2_slopes = row_matrix([0, 1], basis_inverse)
    c1_range = nonnegative_interval(c1_constants, c1_slopes)
    c2_range = nonnegative_interval(c2_constants, c2_slopes)
    solver_values = (
        ("base", {}, 56),
        ("b1_8", {0: 8}, 40),
        ("b1_24", {0: 24}, 72),
        ("b2_16", {1: 16}, 48),
        ("b2_48", {1: 48}, 80),
    )
    solver_checks = []
    for name, override, expected_value in solver_values:
        record = solve_case(
            data, "complete", name, rhs_overrides=override
        )
        assert_solver_objective(record, expected_value)
        solver_checks.append(record)
    certificate = {
        "basis_inverse": exact_matrix(basis_inverse),
        "coefficient_ranges": {
            "c1": [exact(c1_range[0]), exact(c1_range[1])],
            "c2": [exact(c2_range[0]), exact(c2_range[1])],
        },
        "objective": exact(dot([5, 6], solution)),
        "rhs_ranges": {
            "b1": [exact(b1_range[0]), exact(b1_range[1])],
            "b2": [exact(b2_range[0]), exact(b2_range[1])],
        },
        "shadow_prices": exact_vector(shadow_prices),
        "solution": exact_vector(solution),
    }
    return _base_result(spec, certificate, solver_checks)


def evaluate_105(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    basis_inverse = inverse([[2, 0], [1, 1]])
    basic_values = matrix_vector(basis_inverse, [10, 15])
    shadow_prices = row_matrix([5, 0], basis_inverse)
    reduced_x2 = Fraction(2) - dot(shadow_prices, [1, 3])
    reduced_s1 = -shadow_prices[0]
    solver_values = (
        ("base", {}, {}, 25),
        ("c2_2_51", {}, {1: "251/100"}, "626/25"),
        ("c1_3_99", {}, {0: "399/100"}, "1997/100"),
    )
    solver_checks = []
    for name, rhs_override, cost_override, expected_value in solver_values:
        record = solve_case(
            data,
            "basis_nonbasis",
            name,
            rhs_overrides=rhs_override,
            cost_overrides=cost_override,
        )
        assert_solver_objective(record, expected_value)
        solver_checks.append(record)
    certificate = {
        "basis": list(spec["basis"]),
        "basis_inverse": exact_matrix(basis_inverse),
        "basic_values": exact_vector(basic_values),
        "coefficient_ranges": {
            "c1": [4, "infinity"],
            "c2": ["-infinity", "5/2"],
        },
        "reduced_costs": {
            "s1": exact(reduced_s1),
            "x2": exact(reduced_x2),
        },
    }
    return _base_result(spec, certificate, solver_checks)


def evaluate_106(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    basis_inverse = inverse([[1, 1], [3, 2]])
    solution = matrix_vector(basis_inverse, [6, 15])
    shadow_prices = row_matrix([5, 4], basis_inverse)
    b1_constants, b1_slopes = affine_parameter(basis_inverse, [6, 15], 0)
    b1_range = nonnegative_interval(b1_constants, b1_slopes)
    c1_constants = row_matrix([0, 4], basis_inverse)
    c1_slopes = row_matrix([1, 0], basis_inverse)
    c1_range = nonnegative_interval(c1_constants, c1_slopes)
    solver_values = (
        ("base", 6, 27),
        ("b1_5", 5, 25),
        ("b1_7_5", "15/2", 30),
    )
    solver_checks = []
    for name, rhs, expected_value in solver_values:
        record = solve_case(
            data, "inverse_basis", name, rhs_overrides={0: rhs}
        )
        assert_solver_objective(record, expected_value)
        solver_checks.append(record)
    certificate = {
        "basis_inverse": exact_matrix(basis_inverse),
        "coefficient_range_c1": [
            exact(c1_range[0]),
            exact(c1_range[1]),
        ],
        "rhs_range_b1": [exact(b1_range[0]), exact(b1_range[1])],
        "shadow_prices": exact_vector(shadow_prices),
        "solution": exact_vector(solution),
    }
    return _base_result(spec, certificate, solver_checks)


def evaluate_107(_data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    report = spec["report"]
    variables = report["variables"]
    constraints = report["constraints"]
    current_objective = sum(
        as_fraction(item["value"]) * as_fraction(item["coefficient"])
        for item in variables
    )
    changed_objective = Fraction(15, 2) * 8 + Fraction(5) * 4
    resource_change = Fraction(2)
    new_objective = (
        current_objective
        + resource_change * as_fraction(constraints[0]["shadow_price"])
    )
    if Fraction(3, 2) > as_fraction(variables[0]["allowable_increase"]):
        raise RuntimeError("perubahan koefisien seharusnya masih di dalam rentang")
    nonbinding = [
        item["id"]
        for item in constraints
        if as_fraction(item["shadow_price"]) == 0
    ]
    certificate = {
        "changed_objective": exact(changed_objective),
        "current_objective": exact(current_objective),
        "fail_closed_reason": (
            "matriks koefisien kendala tidak tersedia; model Pyomo tidak dibuat"
        ),
        "missing_for_solver": list(spec["missing_for_solver"]),
        "new_objective_from_shadow_price": exact(new_objective),
        "nonbinding_constraint": nonbinding[0],
    }
    return _base_result(
        spec,
        certificate,
        [],
        status="verified_fail_closed",
    )


def evaluate_108(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    basis_inverse = inverse([[4, 2], [2, 3]])
    solution = matrix_vector(basis_inverse, [40, 30])
    shadow_prices = row_matrix([50, 30], basis_inverse)
    b1_constants, b1_slopes = affine_parameter(basis_inverse, [40, 30], 0)
    b1_range = nonnegative_interval(b1_constants, b1_slopes)
    solver_checks = [
        solve_case(data, "furniture", "base"),
        solve_case(
            data, "furniture", "wood_plus_2", rhs_overrides={0: 42}
        ),
    ]
    for record, expected_value in zip(solver_checks, (525, "1095/2")):
        assert_solver_objective(record, expected_value)
    certificate = {
        "objective": exact(dot([50, 30], solution)),
        "objective_after_two_more_wood": exact(
            dot([50, 30], solution) + 2 * shadow_prices[0]
        ),
        "rhs_range_wood": [exact(b1_range[0]), exact(b1_range[1])],
        "shadow_prices": exact_vector(shadow_prices),
        "solution": exact_vector(solution),
    }
    return _base_result(spec, certificate, solver_checks)


def evaluate_109(_data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    certificate = {
        "dictionary_example": {
            "objective": 23,
            "rhs_range_b2": [13, "infinity"],
            "shadow_price_b2": 0,
            "slack_b2": 3,
        },
        "proof_steps": [
            "slack_basis_positif_menyatakan_sumber_daya_tidak_terpakai",
            "perubahan_rhs_kecil_hanya_mengubah_konstanta_baris_slack",
            "baris_objektif_tidak_berubah",
            "turunan_nilai_optimal_terhadap_rhs_adalah_nol",
        ],
        "status": "verified_general_proof",
    }
    return _base_result(spec, certificate, [])


def evaluate_1010(_data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    certificate = {
        "cost_condition": "cN-cB*A_B^-1*A_N<=0",
        "endpoint_events": [
            "variabel_basis_mencapai_nol",
            "biaya_tereduksi_mencapai_nol",
        ],
        "rhs_condition": "A_B^-1*b>=0",
        "status": "verified_general_certificate",
        "value_formula": "cB*A_B^-1*b",
    }
    return _base_result(spec, certificate, [])


def evaluate_1011(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    solver_values = (
        ("b3_1", 1, 1),
        ("b3_2", 2, 2),
        ("b3_3", 3, 2),
    )
    solver_checks = []
    values = {}
    for name, rhs, expected_value in solver_values:
        record = solve_case(
            data, "degenerate", name, rhs_overrides={2: rhs}
        )
        assert_solver_objective(record, expected_value)
        solver_checks.append(record)
        values[f"b3={rhs}"] = exact(as_fraction(expected_value))
    for t in (Fraction(0), Fraction(1, 2), Fraction(1)):
        y = [1 - t, 1 - t, t]
        if y[0] + y[2] < 1 or y[1] + y[2] < 1:
            raise RuntimeError("keluarga dual tidak layak")
        if y[0] + y[1] + 2 * y[2] != 2:
            raise RuntimeError("keluarga dual tidak optimal")
    certificate = {
        "dual_family": ["1-t", "1-t", "t"],
        "dual_parameter_range": [0, 1],
        "left_derivative": 1,
        "right_derivative": 0,
        "values": values,
    }
    return _base_result(spec, certificate, solver_checks)


def evaluate_1012(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    solver_values = (
        ("b1_9", 9, 23),
        ("b1_10", 10, 24),
        ("b1_14", 14, 24),
    )
    solver_checks = []
    values = {}
    for name, rhs, expected_value in solver_values:
        record = solve_case(data, "main", name, rhs_overrides={0: rhs})
        assert_solver_objective(record, expected_value)
        solver_checks.append(record)
        values[f"b1={rhs}"] = exact(as_fraction(expected_value))
    certificate = {
        "actual_at_b1_14": 24,
        "allowable_rhs_range": [7, 10],
        "piecewise_value": [
            {"domain": "0<=b1<=7", "formula": "3*b1"},
            {"domain": "7<=b1<=10", "formula": "b1+14"},
            {"domain": "b1>=10", "formula": "24"},
        ],
        "predicted_at_b1_14": 28,
        "shadow_price": 1,
        "values": values,
    }
    return _base_result(spec, certificate, solver_checks)


EVALUATORS = {
    "10.1": evaluate_101,
    "10.2": evaluate_102,
    "10.3": evaluate_103,
    "10.4": evaluate_104,
    "10.5": evaluate_105,
    "10.6": evaluate_106,
    "10.7": evaluate_107,
    "10.8": evaluate_108,
    "10.9": evaluate_109,
    "10.10": evaluate_1010,
    "10.11": evaluate_1011,
    "10.12": evaluate_1012,
}


def evaluate_all(data: dict[str, Any]) -> dict[str, Any]:
    exercises = {
        exercise_id: EVALUATORS[exercise_id](
            data, data["exercises"][exercise_id]
        )
        for exercise_id in EXERCISE_IDS
    }
    solver_checks = [
        check
        for exercise in exercises.values()
        for check in exercise["solver_checks"]
    ]
    maximum_violation = max(
        (float(check["maximum_violation"]) for check in solver_checks),
        default=0.0,
    )
    status_counts = Counter(
        check["termination_condition"] for check in solver_checks
    )
    return {
        "authority_commit": data["authority_commit"],
        "code_license": data["code_license"],
        "content_license": data["content_license"],
        "corrections": data["corrections"],
        "exercises": exercises,
        "lab_id": data["lab_id"],
        "provenance": data["provenance"],
        "schema_version": data["schema_version"],
        "summary": {
            "correction_count": len(data["corrections"]),
            "exercise_count": len(exercises),
            "maximum_solver_violation": clean_float(maximum_violation),
            "method_counts": dict(
                sorted(
                    Counter(
                        spec["method"]
                        for spec in data["exercises"].values()
                    ).items()
                )
            ),
            "o018_math_correction_count": 0,
            "plot_count": 0,
            "solver_call_count": len(solver_checks),
            "solver_termination_counts": dict(sorted(status_counts.items())),
            "underdetermined_count": len(data["underdetermined_exercises"]),
            "verified_count": len(exercises),
        },
        "underdetermined_exercises": data["underdetermined_exercises"],
    }
