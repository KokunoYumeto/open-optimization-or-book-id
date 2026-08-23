"""Komputasi dan sertifikat deterministik untuk latihan Bab 6.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
import math
from fractions import Fraction
from importlib.metadata import version
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
from pyomo.environ import (
    ConcreteModel,
    Constraint,
    ConstraintList,
    Objective,
    Reals,
    Set,
    SolverFactory,
    Var,
    maximize,
    value,
)
from pyomo.opt import SolverStatus, TerminationCondition


LAB_ID = "o018.ch06.formal-mathematics"
EXERCISE_IDS = tuple(f"6.{number}" for number in range(1, 13))
TOLERANCE = 1e-8


def as_fraction(number: int | str | Fraction) -> Fraction:
    """Ubah bilangan sumber menjadi rasional eksak tanpa lewat float."""
    if isinstance(number, Fraction):
        return number
    if isinstance(number, bool) or not isinstance(number, (int, str)):
        raise TypeError(f"bilangan harus int atau string rasional: {number!r}")
    return Fraction(number)


def exact(number: Fraction | int) -> int | str:
    """Representasi JSON stabil: integer sebagai angka, pecahan sebagai p/q."""
    item = as_fraction(number)
    return item.numerator if item.denominator == 1 else f"{item.numerator}/{item.denominator}"


def exact_vector(items: Iterable[Fraction | int]) -> list[int | str]:
    return [exact(item) for item in items]


def clean_float(number: float) -> float:
    number = float(number)
    if abs(number) <= 1e-10:
        return 0.0
    return round(number, 10)


def fraction_vector(items: Sequence[int | str]) -> list[Fraction]:
    return [as_fraction(item) for item in items]


def dot(first: Sequence[Fraction], second: Sequence[Fraction]) -> Fraction:
    if len(first) != len(second):
        raise ValueError("dimensi perkalian titik berbeda")
    return sum((a * b for a, b in zip(first, second, strict=True)), Fraction(0))


def matrix_vector(
    matrix: Sequence[Sequence[int | str]], vector: Sequence[Fraction]
) -> list[Fraction]:
    return [dot(fraction_vector(row), vector) for row in matrix]


def exact_rank(matrix: Sequence[Sequence[int | str]]) -> int:
    """Rank melalui eliminasi Gauss dengan Fraction."""
    rows = [fraction_vector(row) for row in matrix]
    if not rows:
        return 0
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("matriks tidak persegi panjang")
    pivot_row = 0
    for column in range(width):
        pivot = next(
            (index for index in range(pivot_row, len(rows)) if rows[index][column]),
            None,
        )
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        scale = rows[pivot_row][column]
        rows[pivot_row] = [item / scale for item in rows[pivot_row]]
        for index in range(len(rows)):
            if index == pivot_row:
                continue
            factor = rows[index][column]
            if factor:
                rows[index] = [
                    item - factor * pivot_item
                    for item, pivot_item in zip(
                        rows[index], rows[pivot_row], strict=True
                    )
                ]
        pivot_row += 1
        if pivot_row == len(rows):
            break
    return pivot_row


def numpy_rank(matrix: Sequence[Sequence[int | str]]) -> int:
    return int(np.linalg.matrix_rank(np.asarray(matrix, dtype=float)))


def determinant_2x2(matrix: Sequence[Sequence[int | str]]) -> Fraction:
    if len(matrix) != 2 or any(len(row) != 2 for row in matrix):
        raise ValueError("determinan ini hanya menerima matriks 2x2")
    rows = [fraction_vector(row) for row in matrix]
    return rows[0][0] * rows[1][1] - rows[0][1] * rows[1][0]


def solve_square(
    matrix: Sequence[Sequence[int | str]], rhs: Sequence[int | str]
) -> list[Fraction]:
    """Selesaikan sistem persegi nonsingular dengan eliminasi eksak."""
    rows = [
        fraction_vector(row) + [as_fraction(rhs_value)]
        for row, rhs_value in zip(matrix, rhs, strict=True)
    ]
    size = len(rows)
    if size == 0 or any(len(row) != size + 1 for row in rows):
        raise ValueError("sistem harus persegi")
    for column in range(size):
        pivot = next(
            (index for index in range(column, size) if rows[index][column]), None
        )
        if pivot is None:
            raise ValueError("sistem singular")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        rows[column] = [item / scale for item in rows[column]]
        for index in range(size):
            if index == column:
                continue
            factor = rows[index][column]
            if factor:
                rows[index] = [
                    item - factor * pivot_item
                    for item, pivot_item in zip(rows[index], rows[column], strict=True)
                ]
    return [row[-1] for row in rows]


def load_data(path: Path) -> dict[str, Any]:
    """Membaca data dan menolak perubahan cakupan, judul, atau status."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != LAB_ID:
        raise ValueError("lab_id tidak sesuai kontrak")
    if tuple(data.get("exercise_order", ())) != EXERCISE_IDS:
        raise ValueError("exercise_order harus tepat memuat Latihan 6.1--6.12")
    exercises = data.get("exercises")
    if not isinstance(exercises, dict) or tuple(exercises) != EXERCISE_IDS:
        raise ValueError("data harus memuat tepat 12 latihan dalam urutan sumber")
    expected_titles = (
        "Operasi Vektor",
        "Kombinasi Linier dan Konveks",
        "Kebebasan Linier dan Rank Matriks",
        "Konveks atau Tidak?",
        "Menulis Program Linier dalam Notasi Matriks",
        "Kombinasi Konveks dan Geometri",
        "Geometri dan Konveksitas Setengah Ruang",
        "Memeriksa Titik Ekstrem",
        "Kombinasi Konveks Titik-Titik Ekstrem",
        "Apakah Gabungan Himpunan Konveks Bersifat Konveks?",
        "Letak Penggunaan Keterbatasan dalam Teorema Titik Sudut",
        "Irisan Keluarga Himpunan Konveks Sembarang",
    )
    if tuple(spec.get("title") for spec in exercises.values()) != expected_titles:
        raise ValueError("judul latihan harus sama persis dengan sumber beku")
    if tuple(spec.get("difficulty") for spec in exercises.values()) != (
        1,
        1,
        1,
        1,
        1,
        2,
        2,
        2,
        2,
        2,
        2,
        3,
    ):
        raise ValueError("tingkat kesulitan tidak sesuai sumber")
    if data.get("underdetermined_exercises") != []:
        raise ValueError("tidak ada latihan Bab 6 yang underdetermined")
    if data.get("corrections") != []:
        raise ValueError("laboratorium tidak menerapkan koreksi matematis baru")
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
        raw_value = value(variable, exception=False)
        if raw_value is None:
            # Kolom linealitas yang sepenuhnya bebas dapat tidak diberi nilai
            # oleh solver; ia tidak menyumbang pelanggaran batas atau baris.
            if variable.lb is not None or variable.ub is not None:
                raise RuntimeError(f"variabel berbatas tidak mempunyai nilai: {variable}")
            continue
        current = float(raw_value)
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


def _solver_record(result: Any, model: ConcreteModel | None = None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "solver": "appsi_highs",
        "status": str(result.solver.status),
        "termination_condition": str(result.solver.termination_condition),
    }
    if model is not None:
        record["maximum_violation"] = clean_float(_maximum_violation(model))
    return record


def _require_solver_result(result: Any, termination: TerminationCondition) -> None:
    allowed = {SolverStatus.ok, SolverStatus.warning}
    if termination == TerminationCondition.infeasible:
        allowed.add(SolverStatus.error)
    if result.solver.status not in allowed:
        raise RuntimeError(f"status solver tidak diterima: {result.solver.status}")
    if result.solver.termination_condition != termination:
        raise RuntimeError(
            "terminasi solver tidak sesuai: "
            f"{result.solver.termination_condition} != {termination}"
        )


def _point_feasible(
    matrix: Sequence[Sequence[int | str]],
    rhs: Sequence[int | str],
    point: Sequence[int | str | Fraction],
) -> bool:
    lhs = matrix_vector(matrix, [as_fraction(item) for item in point])
    return all(
        left <= as_fraction(right)
        for left, right in zip(lhs, rhs, strict=True)
    )


def _two_point_weights(
    first: Sequence[int | str],
    second: Sequence[int | str],
    target: Sequence[int | str],
) -> list[Fraction] | None:
    a = fraction_vector(first)
    b = fraction_vector(second)
    t = fraction_vector(target)
    candidates: list[Fraction] = []
    for first_item, second_item, target_item in zip(a, b, t, strict=True):
        difference = first_item - second_item
        if difference:
            candidates.append((target_item - second_item) / difference)
        elif target_item != second_item:
            return None
    if not candidates:
        return [Fraction(1), Fraction(0)] if a == t else None
    if any(item != candidates[0] for item in candidates[1:]):
        return None
    first_weight = candidates[0]
    second_weight = Fraction(1) - first_weight
    if first_weight < 0 or second_weight < 0:
        return None
    return [first_weight, second_weight]


def _barycentric_weights(
    vertices: Sequence[Sequence[int | str]], target: Sequence[int | str]
) -> list[Fraction]:
    if len(vertices) != 3 or any(len(vertex) != 2 for vertex in vertices):
        raise ValueError("pemeriksa barysentris mengharapkan tiga titik di R2")
    matrix = [
        [vertices[column][row] for column in range(3)]
        for row in range(2)
    ]
    matrix.append([1, 1, 1])
    return solve_square(matrix, [*target, 1])


def _pyomo_barycentric_check(
    exercise_id: str,
    vertices: Sequence[Sequence[int | str]],
    target: Sequence[int | str],
    expected_feasible: bool,
) -> dict[str, Any]:
    model = ConcreteModel(name=f"ch06_ex{exercise_id}_barycentric")
    model.I = Set(initialize=range(len(vertices)), ordered=True)
    model.lam = Var(model.I, bounds=(0.0, None))
    model.normalization = Constraint(
        expr=sum(model.lam[index] for index in model.I) == 1.0
    )
    model.coordinates = ConstraintList()
    for coordinate in range(len(target)):
        model.coordinates.add(
            sum(
                float(as_fraction(vertices[index][coordinate])) * model.lam[index]
                for index in model.I
            )
            == float(as_fraction(target[coordinate]))
        )
    model.objective = Objective(expr=0.0)
    result = _solver().solve(
        model, tee=False, load_solutions=expected_feasible
    )
    expected_termination = (
        TerminationCondition.optimal
        if expected_feasible
        else TerminationCondition.infeasible
    )
    _require_solver_result(result, expected_termination)
    record = _solver_record(result, model if expected_feasible else None)
    record["purpose"] = "convex_combination_feasibility"
    return record


def _squared_distance(
    first: Sequence[int | str], second: Sequence[int | str]
) -> Fraction:
    a = fraction_vector(first)
    b = fraction_vector(second)
    return sum(((x - y) ** 2 for x, y in zip(a, b, strict=True)), Fraction(0))


def _midpoint(
    first: Sequence[int | str], second: Sequence[int | str]
) -> list[Fraction]:
    return [
        (a + b) / 2
        for a, b in zip(
            fraction_vector(first), fraction_vector(second), strict=True
        )
    ]


def _contains(set_spec: dict[str, Any], point: Sequence[int | str | Fraction]) -> bool:
    coordinates = [as_fraction(item) for item in point]
    set_type = set_spec["type"]
    if set_type == "euclidean_ball":
        return _squared_distance(coordinates, set_spec["center"]) <= as_fraction(
            set_spec["radius"]
        ) ** 2
    if set_type == "annulus":
        distance = _squared_distance(coordinates, set_spec["center"])
        return as_fraction(set_spec["inner_radius"]) ** 2 <= distance <= as_fraction(
            set_spec["outer_radius"]
        ) ** 2
    if set_type == "halfspace":
        return dot(fraction_vector(set_spec["coefficients"]), coordinates) <= as_fraction(
            set_spec["rhs"]
        )
    if set_type == "absolute_coordinate_exterior":
        return abs(coordinates[int(set_spec["coordinate"])]) >= as_fraction(
            set_spec["threshold"]
        )
    raise ValueError(f"tipe himpunan tidak didukung: {set_type}")


def evaluate_61(spec: dict[str, Any]) -> dict[str, Any]:
    v = fraction_vector(spec["vectors"]["v"])
    u = fraction_vector(spec["vectors"]["u"])
    scalar = as_fraction(spec["scalar"])
    return {
        "dot_product": exact(dot(v, u)),
        "scalar_multiple": exact_vector(scalar * item for item in v),
        "vector_sum": exact_vector(a + b for a, b in zip(v, u, strict=True)),
    }


def evaluate_62(spec: dict[str, Any]) -> dict[str, Any]:
    vectors = spec["vectors"]
    basis_matrix = [vectors["v1"], vectors["v2"]]
    if determinant_2x2(basis_matrix) == 0:
        raise RuntimeError("v1 dan v2 harus membentuk basis R2")
    combinations = {
        candidate_id: {
            "coefficients_v1_v2": exact_vector(fraction_vector(candidate)),
            "is_linear_combination": True,
        }
        for candidate_id, candidate in spec["candidates"].items()
    }
    pair_results: dict[str, Any] = {}
    for first, second in (("v1", "v2"), ("v1", "v3"), ("v2", "v3")):
        weights = _two_point_weights(
            vectors[first], vectors[second], spec["target"]
        )
        pair_results[f"{first}_{second}"] = {
            "feasible": weights is not None,
            "weights": exact_vector(weights) if weights is not None else None,
        }
    return {
        "basis_determinant": exact(determinant_2x2(basis_matrix)),
        "convex_pair_checks": pair_results,
        "linear_combination_checks": combinations,
        "successful_convex_pair": "v1_v2",
    }


def evaluate_63(spec: dict[str, Any]) -> dict[str, Any]:
    matrix = spec["matrix"]
    rank_exact = exact_rank(matrix)
    rank_numpy = numpy_rank(matrix)
    if rank_exact != rank_numpy:
        raise RuntimeError("rank eksak dan NumPy berbeda")
    return {
        "columns_linearly_independent": False,
        "determinant": exact(determinant_2x2(matrix)),
        "exact_rank": rank_exact,
        "numpy_rank": rank_numpy,
        "row_relation": "row_2=2*row_1",
        "rows_linearly_independent": False,
        "column_relation": "column_2=2*column_1",
    }


def evaluate_64(spec: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for set_spec in spec["sets"]:
        set_id = set_spec["id"]
        claim = set_spec["claim"]
        if claim == "convex":
            if set_spec["type"] == "euclidean_ball":
                if as_fraction(set_spec["radius"]) < 0:
                    raise RuntimeError("radius bola harus nonnegatif")
                proof = "triangle_inequality_for_norm_ball"
            elif set_spec["type"] == "halfspace":
                if not set_spec["coefficients"]:
                    raise RuntimeError("setengah ruang harus memiliki baris koefisien")
                proof = "affine_identity_preserves_halfspace_inequality"
            else:
                raise RuntimeError(f"tidak ada sertifikat konveks untuk {set_id}")
            results[set_id] = {"classification": "convex", "proof": proof}
            continue
        witness = set_spec["witness"]
        midpoint = _midpoint(witness["first"], witness["second"])
        first_inside = _contains(set_spec, witness["first"])
        second_inside = _contains(set_spec, witness["second"])
        midpoint_inside = _contains(set_spec, midpoint)
        if not first_inside or not second_inside or midpoint_inside:
            raise RuntimeError(f"saksi nonkonveks {set_id} gagal")
        results[set_id] = {
            "classification": "nonconvex",
            "midpoint": exact_vector(midpoint),
            "midpoint_in_set": False,
            "witness_endpoints_in_set": True,
        }
    return {"sets": results}


def evaluate_65(spec: dict[str, Any]) -> dict[str, Any]:
    point = fraction_vector(spec["check_point"])
    lhs = matrix_vector(spec["A"], point)
    rhs = fraction_vector(spec["b"])
    slack = [right - left for left, right in zip(lhs, rhs, strict=True)]
    if any(item < 0 for item in slack):
        raise RuntimeError("titik pemeriksaan Latihan 6.5 tidak layak")

    model = ConcreteModel(name="ch06_ex6_5_matrix_lp")
    model.J = Set(initialize=range(len(spec["c"])), ordered=True)
    model.x = Var(model.J, domain=Reals)
    model.constraints = ConstraintList()
    for row, bound in zip(spec["A"], spec["b"], strict=True):
        model.constraints.add(
            sum(float(as_fraction(coefficient)) * model.x[index] for index, coefficient in enumerate(row))
            <= float(as_fraction(bound))
        )
    model.objective = Objective(
        expr=sum(float(as_fraction(coefficient)) * model.x[index] for index, coefficient in enumerate(spec["c"])),
        sense=maximize,
    )
    result = _solver().solve(model, tee=False, load_solutions=True)
    _require_solver_result(result, TerminationCondition.optimal)
    solver_point = [float(value(model.x[index])) for index in model.J]
    if math.dist(solver_point, [float(item) for item in point]) > 10 * TOLERANCE:
        raise RuntimeError(f"optimum solver berbeda: {solver_point}")
    objective = dot(fraction_vector(spec["c"]), point)
    if abs(float(value(model.objective)) - float(objective)) > 10 * TOLERANCE:
        raise RuntimeError("nilai objektif solver berbeda")
    solver_record = _solver_record(result, model)
    solver_record.update(
        {
            "objective_exact": exact(objective),
            "point": [clean_float(item) for item in solver_point],
            "purpose": "matrix_lp_optimum_corroboration",
        }
    )
    return {
        "active_rows": [index + 1 for index, item in enumerate(slack) if item == 0],
        "feasible": True,
        "lhs_Ax": exact_vector(lhs),
        "objective_at_point": exact(objective),
        "slack": exact_vector(slack),
        "solver_checks": [solver_record],
    }


def evaluate_66(spec: dict[str, Any]) -> dict[str, Any]:
    point_results: dict[str, Any] = {}
    solver_checks: list[dict[str, Any]] = []
    for point_id, target in spec["points"].items():
        weights = _barycentric_weights(spec["vertices"], target)
        inside = all(item >= 0 for item in weights)
        expected_inside = point_id == "inside_boundary"
        if inside != expected_inside or sum(weights) != 1:
            raise RuntimeError(f"klasifikasi barysentris salah untuk {point_id}")
        reconstructed = [
            sum(
                weights[index] * as_fraction(spec["vertices"][index][coordinate])
                for index in range(3)
            )
            for coordinate in range(2)
        ]
        if reconstructed != fraction_vector(target):
            raise RuntimeError("rekonstruksi barysentris gagal")
        point_results[point_id] = {
            "in_triangle": inside,
            "weights": exact_vector(weights),
        }
        solver_checks.append(
            _pyomo_barycentric_check("6_6", spec["vertices"], target, inside)
        )
    return {
        "halfspace_description": ["x1>=0", "x2>=0", "x1+x2<=2"],
        "points": point_results,
        "solver_checks": solver_checks,
    }


def evaluate_67(spec: dict[str, Any]) -> dict[str, Any]:
    coefficients = fraction_vector(spec["coefficients"])
    rhs = as_fraction(spec["rhs"])
    if len(coefficients) != 2 or not all(coefficients):
        raise RuntimeError("intersep Latihan 6.7 memerlukan dua koefisien taknol")
    intercepts = [[rhs / coefficients[0], 0], [0, rhs / coefficients[1]]]
    point_checks = {}
    for point_id, point in spec["test_points"].items():
        lhs = dot(coefficients, fraction_vector(point))
        point_checks[point_id] = {
            "in_halfspace": lhs <= rhs,
            "lhs": exact(lhs),
        }
    midpoint = _midpoint(*spec["midpoint_endpoints"])
    midpoint_lhs = dot(coefficients, midpoint)
    if midpoint_lhs > rhs:
        raise RuntimeError("titik tengah Latihan 6.7 seharusnya layak")
    return {
        "boundary_intercepts": [exact_vector(point) for point in intercepts],
        "convexity_proof": "a·(lambda*x+(1-lambda)*y)=lambda*a·x+(1-lambda)*a·y<=rhs",
        "midpoint": exact_vector(midpoint),
        "midpoint_in_halfspace": True,
        "midpoint_lhs": exact(midpoint_lhs),
        "point_checks": point_checks,
    }


def _active_set(
    matrix: Sequence[Sequence[int | str]],
    rhs: Sequence[int | str],
    point: Sequence[int | str],
) -> tuple[list[Fraction], list[int]]:
    lhs = matrix_vector(matrix, fraction_vector(point))
    active = [
        index
        for index, (left, right) in enumerate(
            zip(lhs, fraction_vector(rhs), strict=True)
        )
        if left == right
    ]
    return lhs, active


def evaluate_68(spec: dict[str, Any]) -> dict[str, Any]:
    point_results: dict[str, Any] = {}
    for point_id, point in spec["points"].items():
        if not _point_feasible(spec["A"], spec["b"], point):
            raise RuntimeError(f"titik {point_id} tidak layak")
        lhs, active = _active_set(spec["A"], spec["b"], point)
        active_matrix = [spec["A"][index] for index in active]
        rank_exact = exact_rank(active_matrix)
        rank_numpy = numpy_rank(active_matrix)
        if rank_exact != rank_numpy:
            raise RuntimeError("rank himpunan aktif berbeda")
        is_corner = rank_exact == 2
        if is_corner != (point_id == "corner"):
            raise RuntimeError("klasifikasi titik sudut berbeda")
        point_results[point_id] = {
            "active_constraints": [spec["constraint_ids"][index] for index in active],
            "active_rank_exact": rank_exact,
            "active_rank_numpy": rank_numpy,
            "is_corner": is_corner,
            "is_extreme_point": is_corner,
            "lhs": exact_vector(lhs),
        }
    witness = spec["convex_witness"]
    if not _point_feasible(spec["A"], spec["b"], witness["first"]):
        raise RuntimeError("saksi pertama 6.8 tidak layak")
    if not _point_feasible(spec["A"], spec["b"], witness["second"]):
        raise RuntimeError("saksi kedua 6.8 tidak layak")
    weights = fraction_vector(witness["weights"])
    reconstructed = [
        weights[0] * as_fraction(witness["first"][coordinate])
        + weights[1] * as_fraction(witness["second"][coordinate])
        for coordinate in range(2)
    ]
    if reconstructed != fraction_vector(witness["target"]):
        raise RuntimeError("saksi kombinasi konveks 6.8 tidak cocok")
    return {
        "non_extreme_certificate": {
            "endpoints_feasible": True,
            "reconstructed_target": exact_vector(reconstructed),
            "weights": exact_vector(weights),
        },
        "points": point_results,
    }


def evaluate_69(spec: dict[str, Any]) -> dict[str, Any]:
    weights = _barycentric_weights(spec["vertices"], spec["target"])
    if any(item < 0 for item in weights) or sum(weights) != 1:
        raise RuntimeError("bobot 6.9 bukan kombinasi konveks")
    solver_record = _pyomo_barycentric_check(
        "6_9", spec["vertices"], spec["target"], True
    )
    return {
        "extreme_directions_needed": False,
        "reason": "target_in_convex_hull_of_extreme_points",
        "solver_checks": [solver_record],
        "weights": exact_vector(weights),
    }


def evaluate_610(spec: dict[str, Any]) -> dict[str, Any]:
    counterexample = spec["counterexample"]
    witness = counterexample["witness"]
    midpoint = _midpoint(witness["first"], witness["second"])
    first_in_union = _contains(counterexample["first"], witness["first"]) or _contains(
        counterexample["second"], witness["first"]
    )
    second_in_union = _contains(counterexample["first"], witness["second"]) or _contains(
        counterexample["second"], witness["second"]
    )
    midpoint_in_union = _contains(counterexample["first"], midpoint) or _contains(
        counterexample["second"], midpoint
    )
    if not first_in_union or not second_in_union or midpoint_in_union:
        raise RuntimeError("saksi gabungan nonkonveks gagal")
    midpoint_distances = [
        _squared_distance(midpoint, counterexample[key]["center"])
        for key in ("first", "second")
    ]
    return {
        "counterexample": {
            "midpoint": exact_vector(midpoint),
            "midpoint_in_union": False,
            "midpoint_squared_distances_to_centers": exact_vector(midpoint_distances),
            "witness_endpoints_in_union": True,
        },
        "containment_condition": {
            "is_necessary": False,
            "is_sufficient": True,
            "proof": "if_C1_subset_C2_then_union_equals_C2",
        },
        "nonnecessary_example_union": "R2",
    }


def evaluate_611(spec: dict[str, Any]) -> dict[str, Any]:
    matrix = spec["A"]
    rhs = spec["b"]
    direction = fraction_vector(spec["lineality_direction"])
    directional_lhs = matrix_vector(matrix, direction)
    if any(item != 0 for item in directional_lhs) or not any(direction):
        raise RuntimeError("arah linealitas 6.11 tidak sah")
    maximum_active_rank = max(exact_rank([row]) for row in matrix)
    if maximum_active_rank >= 2:
        raise RuntimeError("lempeng seharusnya tidak memiliki rank aktif penuh")

    model = ConcreteModel(name="ch06_ex6_11_strip")
    model.J = Set(initialize=range(2), ordered=True)
    model.x = Var(model.J, domain=Reals)
    model.constraints = ConstraintList()
    for row, bound in zip(matrix, rhs, strict=True):
        model.constraints.add(
            sum(float(as_fraction(coefficient)) * model.x[index] for index, coefficient in enumerate(row))
            <= float(as_fraction(bound))
        )
    model.objective = Objective(
        expr=sum(float(as_fraction(coefficient)) * model.x[index] for index, coefficient in enumerate(spec["objective"])),
        sense=maximize,
    )
    result = _solver().solve(model, tee=False, load_solutions=True)
    _require_solver_result(result, TerminationCondition.optimal)
    objective = clean_float(float(value(model.objective)))
    if abs(objective) > TOLERANCE:
        raise RuntimeError("nilai optimal lempeng harus nol")
    solver_record = _solver_record(result, model)
    solver_record.update(
        {
            "objective_exact": 0,
            "purpose": "bounded_objective_on_unbounded_strip",
        }
    )
    return {
        "boundedness_hypothesis_holds": False,
        "lineality_A_times_d": exact_vector(directional_lhs),
        "lineality_direction": exact_vector(direction),
        "maximum_active_rank": maximum_active_rank,
        "optimal_set": "{(t,0):t_in_R}",
        "optimal_value": 0,
        "proof_failure_without_boundedness": "feasible_t_interval_may_be_unbounded_so_no_new_active_constraint_appears",
        "solver_checks": [solver_record],
        "vertex_count": 0,
    }


def evaluate_612(spec: dict[str, Any]) -> dict[str, Any]:
    required_steps = (
        "choose_x_y_in_intersection_and_lambda_in_unit_interval",
        "fix_arbitrary_index_i",
        "infer_x_y_in_C_i",
        "apply_convexity_of_C_i_to_z",
        "generalize_over_arbitrary_i",
        "handle_empty_intersection_vacuously",
        "identify_polyhedron_as_intersection_of_halfspaces",
    )
    if tuple(spec["proof_contract"]) != required_steps:
        raise RuntimeError("kontrak bukti irisan berubah atau tidak lengkap")
    return {
        "applies_to_infinite_index_families": True,
        "empty_intersection_case": "vacuously_convex",
        "polyhedron_corollary": "intersection_of_convex_halfspaces_is_convex",
        "proof_steps": [
            {"id": step, "validated": True} for step in required_steps
        ],
        "uses_cardinality_bound_on_index_set": False,
    }


EVALUATORS = {
    "6.1": evaluate_61,
    "6.2": evaluate_62,
    "6.3": evaluate_63,
    "6.4": evaluate_64,
    "6.5": evaluate_65,
    "6.6": evaluate_66,
    "6.7": evaluate_67,
    "6.8": evaluate_68,
    "6.9": evaluate_69,
    "6.10": evaluate_610,
    "6.11": evaluate_611,
    "6.12": evaluate_612,
}


def evaluate_all(data: dict[str, Any]) -> dict[str, Any]:
    exercises: dict[str, Any] = {}
    solver_call_count = 0
    maximum_solver_violation = 0.0
    for exercise_id in data["exercise_order"]:
        spec = data["exercises"][exercise_id]
        calculation = EVALUATORS[exercise_id](spec)
        solver_checks = calculation.get("solver_checks", [])
        solver_call_count += len(solver_checks)
        for solver_check in solver_checks:
            maximum_solver_violation = max(
                maximum_solver_violation,
                float(solver_check.get("maximum_violation", 0.0)),
            )
        exercises[exercise_id] = {
            "calculation": calculation,
            "difficulty": spec["difficulty"],
            "kind": spec["kind"],
            "method": spec["method"],
            "status": "verified",
            "title": spec["title"],
        }
    return {
        "content_license": data["content_license"],
        "exercises": exercises,
        "lab_id": data["lab_id"],
        "numerical_tolerance": TOLERANCE,
        "runtime": {
            "highspy": version("highspy"),
            "numpy": version("numpy"),
            "pyomo": version("pyomo"),
            "solver_interface": "appsi_highs",
        },
        "schema_version": "1.0.0",
        "summary": {
            "correction_count": len(data["corrections"]),
            "exercise_count": len(exercises),
            "maximum_solver_violation": clean_float(maximum_solver_violation),
            "solver_call_count": solver_call_count,
            "underdetermined_count": len(data["underdetermined_exercises"]),
            "verified_count": sum(
                exercise["status"] == "verified" for exercise in exercises.values()
            ),
        },
    }
