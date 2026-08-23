"""Model dan pemeriksa geometri LP grafis Bab 5.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
import math
from importlib.metadata import version
from pathlib import Path
from typing import Any, Iterable

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
    minimize,
    value,
)
from pyomo.opt import SolverStatus, TerminationCondition


LAB_ID = "o018.ch05.graphical-lp"
EXERCISE_IDS = tuple(f"5.{number}" for number in range(1, 18))
TOLERANCE = 1e-7


class ParameterRequiredError(ValueError):
    """Instans tidak boleh dibangun sebelum parameter sumber tersedia."""


def _clean(number: float) -> float:
    number = float(number)
    if abs(number) <= 1e-10:
        return 0.0
    return round(number, 10)


def load_data(path: Path) -> dict[str, Any]:
    """Membaca data dan menolak perubahan cakupan atau status latihan."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != LAB_ID:
        raise ValueError("lab_id tidak sesuai kontrak")
    if tuple(data.get("exercise_order", ())) != EXERCISE_IDS:
        raise ValueError("exercise_order harus tepat memuat Latihan 5.1--5.17")
    exercises = data.get("exercises")
    if not isinstance(exercises, dict) or tuple(exercises) != EXERCISE_IDS:
        raise ValueError("data harus memuat tepat 17 latihan dalam urutan sumber")
    if exercises["5.11"].get("model_status") != "parameter_required":
        raise ValueError("Latihan 5.11 harus tetap parameter_required")
    executable = {
        exercise_id
        for exercise_id, spec in exercises.items()
        if spec.get("model_status") == "executable"
    }
    if executable != set(EXERCISE_IDS) - {"5.11"}:
        raise ValueError("tepat 16 latihan harus executable")
    if exercises["5.8"]["constraints"][1] != {
        "coefficients": {"x": 1, "y": 3},
        "id": "c2",
        "rhs": 3,
        "sense": ">=",
    }:
        raise ValueError("Latihan 5.8 harus terikat pada x+3y>=3")
    if exercises["5.9"]["scenarios"]["as_written"]["expected"][
        "classification"
    ] != "unbounded":
        raise ValueError("divergensi Latihan 5.9 harus tetap eksplisit")
    return data


def _variable_ids(spec: dict[str, Any]) -> tuple[str, ...]:
    return tuple(variable["id"] for variable in spec["variables"])


def build_model(
    exercise_id: str,
    spec: dict[str, Any],
    scenario_id: str,
) -> ConcreteModel:
    """Membangun satu skenario tanpa mengisi data yang tidak diberikan sumber."""
    if spec.get("model_status") != "executable":
        required = "; ".join(spec.get("required_parameters", ()))
        raise ParameterRequiredError(
            f"Latihan {exercise_id} memerlukan parameter: {required}"
        )
    if scenario_id not in spec["scenarios"]:
        raise KeyError(f"skenario tidak dikenal: {exercise_id}/{scenario_id}")
    scenario = spec["scenarios"][scenario_id]
    variables = tuple(spec["variables"])
    variable_by_id = {variable["id"]: variable for variable in variables}
    ids = tuple(variable_by_id)

    model = ConcreteModel(name=f"ch05_ex{exercise_id}_{scenario_id}")
    model.V = Set(initialize=ids, ordered=True)

    def bounds_rule(_model: ConcreteModel, variable_id: str):
        variable = variable_by_id[variable_id]
        return variable.get("lower"), variable.get("upper")

    model.x = Var(model.V, domain=Reals, bounds=bounds_rule)
    model.linear_constraints = ConstraintList()
    for constraint in spec["constraints"]:
        expression = sum(
            float(constraint["coefficients"].get(variable_id, 0.0))
            * model.x[variable_id]
            for variable_id in model.V
        )
        rhs = float(constraint["rhs"])
        if constraint["sense"] == "<=":
            model.linear_constraints.add(expression <= rhs)
        elif constraint["sense"] == ">=":
            model.linear_constraints.add(expression >= rhs)
        elif constraint["sense"] == "=":
            model.linear_constraints.add(expression == rhs)
        else:
            raise ValueError(f"arah kendala tidak sah: {constraint['sense']}")

    objective = scenario["objective"]
    expression = sum(
        float(objective["coefficients"].get(variable_id, 0.0))
        * model.x[variable_id]
        for variable_id in model.V
    )
    sense = maximize if objective["sense"] == "maximize" else minimize
    model.objective = Objective(expr=expression, sense=sense)
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
    return max(0.0, violation)


def _point_violation(spec: dict[str, Any], point: Iterable[float]) -> float:
    ids = _variable_ids(spec)
    coordinates = dict(zip(ids, (float(item) for item in point), strict=True))
    violation = 0.0
    for variable in spec["variables"]:
        current = coordinates[variable["id"]]
        if variable.get("lower") is not None:
            violation = max(violation, float(variable["lower"]) - current)
        if variable.get("upper") is not None:
            violation = max(violation, current - float(variable["upper"]))
    for constraint in spec["constraints"]:
        lhs = sum(
            float(coefficient) * coordinates[variable_id]
            for variable_id, coefficient in constraint["coefficients"].items()
        )
        rhs = float(constraint["rhs"])
        if constraint["sense"] == "<=":
            violation = max(violation, lhs - rhs)
        elif constraint["sense"] == ">=":
            violation = max(violation, rhs - lhs)
        else:
            violation = max(violation, abs(lhs - rhs))
    return max(0.0, violation)


def _objective_value(
    spec: dict[str, Any], scenario: dict[str, Any], point: Iterable[float]
) -> float:
    ids = _variable_ids(spec)
    coordinates = dict(zip(ids, (float(item) for item in point), strict=True))
    return sum(
        float(coefficient) * coordinates[variable_id]
        for variable_id, coefficient in scenario["objective"]["coefficients"].items()
    )


def _boundaries_2d(spec: dict[str, Any]) -> list[tuple[float, float, float]]:
    ids = _variable_ids(spec)
    if len(ids) != 2:
        raise ValueError("enumerasi titik ekstrem hanya untuk dua variabel")
    first, second = ids
    boundaries = [
        (
            float(constraint["coefficients"].get(first, 0.0)),
            float(constraint["coefficients"].get(second, 0.0)),
            float(constraint["rhs"]),
        )
        for constraint in spec["constraints"]
    ]
    for index, variable in enumerate(spec["variables"]):
        for bound_name in ("lower", "upper"):
            bound = variable.get(bound_name)
            if bound is None:
                continue
            coefficient = [0.0, 0.0]
            coefficient[index] = 1.0
            boundaries.append((coefficient[0], coefficient[1], float(bound)))
    return boundaries


def enumerate_vertices_2d(spec: dict[str, Any]) -> list[list[float]]:
    """Enumerasi semua perpotongan batas yang layak, tanpa memakai solver."""
    boundaries = _boundaries_2d(spec)
    candidates: list[list[float]] = []
    for first_index, first in enumerate(boundaries):
        for second in boundaries[first_index + 1 :]:
            a1, b1, c1 = first
            a2, b2, c2 = second
            determinant = a1 * b2 - a2 * b1
            if abs(determinant) <= TOLERANCE:
                continue
            x_value = (c1 * b2 - c2 * b1) / determinant
            y_value = (a1 * c2 - a2 * c1) / determinant
            point = [_clean(x_value), _clean(y_value)]
            if _point_violation(spec, point) > TOLERANCE:
                continue
            if not any(
                math.dist(point, existing) <= TOLERANCE for existing in candidates
            ):
                candidates.append(point)
    return sorted(candidates, key=lambda point: (point[0], point[1]))


def _compare_point_sets(
    expected: list[list[float]], actual: list[list[float]], *, label: str
) -> None:
    if len(expected) != len(actual):
        raise RuntimeError(
            f"jumlah titik ekstrem {label} berbeda: {len(expected)} != {len(actual)}"
        )
    remaining = [list(map(float, point)) for point in actual]
    for point in expected:
        nearest_index = min(
            range(len(remaining)),
            key=lambda index: math.dist(list(map(float, point)), remaining[index]),
            default=-1,
        )
        if nearest_index < 0 or math.dist(
            list(map(float, point)), remaining[nearest_index]
        ) > 5 * TOLERANCE:
            raise RuntimeError(f"titik ekstrem {label} tidak cocok: {point}")
        remaining.pop(nearest_index)


def _ray_violation(spec: dict[str, Any], ray: dict[str, Any]) -> float:
    ids = _variable_ids(spec)
    base = dict(zip(ids, map(float, ray["base"]), strict=True))
    direction = dict(zip(ids, map(float, ray["direction"]), strict=True))
    violation = _point_violation(spec, ray["base"])
    for variable in spec["variables"]:
        component = direction[variable["id"]]
        if variable.get("lower") is not None:
            violation = max(violation, -component)
        if variable.get("upper") is not None:
            violation = max(violation, component)
    for constraint in spec["constraints"]:
        directional_lhs = sum(
            float(coefficient) * direction[variable_id]
            for variable_id, coefficient in constraint["coefficients"].items()
        )
        if constraint["sense"] == "<=":
            violation = max(violation, directional_lhs)
        elif constraint["sense"] == ">=":
            violation = max(violation, -directional_lhs)
        else:
            violation = max(violation, abs(directional_lhs))
    if not all(math.isfinite(item) for item in (*base.values(), *direction.values())):
        return math.inf
    return max(0.0, violation)


def verify_geometry(exercise_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Memeriksa titik, ruas optimum, dan sertifikat arah secara mandiri."""
    if spec["model_status"] != "executable":
        return {
            "reason": spec["model_status"],
            "status": "not_run",
        }
    ids = _variable_ids(spec)
    vertices: list[list[float]] = []
    if len(ids) == 2:
        vertices = enumerate_vertices_2d(spec)
        _compare_point_sets(
            spec["expected_vertices"], vertices, label=f"Latihan {exercise_id}"
        )

    rays = []
    for ray in spec.get("recession_certificates", ()):
        violation = _ray_violation(spec, ray)
        if violation > TOLERANCE:
            raise RuntimeError(
                f"sertifikat {exercise_id}/{ray['id']} tidak layak: {violation}"
            )
        rays.append(
            {
                "base": [_clean(item) for item in ray["base"]],
                "direction": [_clean(item) for item in ray["direction"]],
                "id": ray["id"],
                "maximum_violation": _clean(violation),
            }
        )

    return {
        "dimension": len(ids),
        "ray_certificates": rays,
        "status": "verified",
        "vertices": vertices,
    }


def _solve_model(
    model: ConcreteModel, expected_classification: str
) -> tuple[Any, str, str]:
    solver = SolverFactory("appsi_highs")
    if not solver.available(exception_flag=False):
        raise RuntimeError("pemecah appsi_highs tidak tersedia")
    solver.options["output_flag"] = False
    requires_solution = expected_classification in {
        "feasible_region_unbounded",
        "optimal_nonunique",
        "optimal_unique",
    }
    result = solver.solve(model, tee=False, load_solutions=requires_solution)
    status = str(result.solver.status)
    termination = str(result.solver.termination_condition)
    accepted_statuses = {SolverStatus.ok, SolverStatus.warning}
    if expected_classification in {"infeasible", "unbounded"}:
        # Antarmuka LegacySolver appsi_highs memetakan terminasi matematis
        # non-optimal yang diharapkan ini ke SolverStatus.error. Kebenaran kasus
        # tetap diikat secara ketat oleh termination_condition di bawah.
        accepted_statuses.add(SolverStatus.error)
    if result.solver.status not in accepted_statuses:
        raise RuntimeError(f"status pemecah tidak diterima: {status}")
    expected_terminations = {
        "feasible_region_unbounded": {str(TerminationCondition.optimal)},
        "infeasible": {str(TerminationCondition.infeasible)},
        "optimal_nonunique": {str(TerminationCondition.optimal)},
        "optimal_unique": {str(TerminationCondition.optimal)},
        "unbounded": {str(TerminationCondition.unbounded)},
    }
    if termination not in expected_terminations[expected_classification]:
        raise RuntimeError(
            "terminasi tidak sesuai untuk "
            f"{expected_classification}: {termination}"
        )
    return result, status, termination


def solve_scenario(
    exercise_id: str,
    spec: dict[str, Any],
    scenario_id: str,
) -> dict[str, Any]:
    scenario = spec["scenarios"][scenario_id]
    expected = scenario["expected"]
    classification = expected["classification"]
    model = build_model(exercise_id, spec, scenario_id)
    _result, status, termination = _solve_model(model, classification)
    execution: dict[str, Any] = {
        "solver": "appsi_highs",
        "status": status,
        "termination_condition": termination,
    }
    output: dict[str, Any] = {
        "classification": classification,
        "execution": execution,
    }

    if classification in {
        "feasible_region_unbounded",
        "optimal_nonunique",
        "optimal_unique",
    }:
        maximum_violation = _maximum_violation(model)
        if maximum_violation > TOLERANCE:
            raise RuntimeError(
                f"pelanggaran solver {exercise_id}/{scenario_id}: {maximum_violation}"
            )
        execution["maximum_violation"] = _clean(maximum_violation)

    if classification in {"optimal_nonunique", "optimal_unique"}:
        solver_objective = float(value(model.objective))
        expected_objective = float(expected["objective"])
        if abs(solver_objective - expected_objective) > 5 * TOLERANCE:
            raise RuntimeError(
                f"objektif {exercise_id}/{scenario_id} berbeda: "
                f"{solver_objective} != {expected_objective}"
            )
        output["objective"] = _clean(expected_objective)
        if "objective_exact" in expected:
            output["objective_exact"] = expected["objective_exact"]

    if classification == "optimal_unique":
        point = list(map(float, expected["point"]))
        if _point_violation(spec, point) > TOLERANCE:
            raise RuntimeError(f"titik optimum {exercise_id}/{scenario_id} tidak layak")
        ids = _variable_ids(spec)
        solver_point = [float(value(model.x[variable_id])) for variable_id in ids]
        if math.dist(point, solver_point) > 5 * TOLERANCE:
            raise RuntimeError(
                f"titik optimum {exercise_id}/{scenario_id} berbeda: {solver_point}"
            )
        if abs(_objective_value(spec, scenario, point) - float(expected["objective"])) > (
            5 * TOLERANCE
        ):
            raise RuntimeError(f"nilai titik optimum {exercise_id}/{scenario_id} salah")
        output["point"] = [_clean(item) for item in point]
        if "point_exact" in expected:
            output["point_exact"] = expected["point_exact"]

    if classification == "optimal_nonunique":
        endpoints = [list(map(float, point)) for point in expected["segment"]]
        midpoint = [
            (first + second) / 2.0
            for first, second in zip(endpoints[0], endpoints[1], strict=True)
        ]
        for point in (*endpoints, midpoint):
            if _point_violation(spec, point) > TOLERANCE:
                raise RuntimeError(
                    f"ruas optimum {exercise_id}/{scenario_id} memuat titik tak layak"
                )
            if abs(
                _objective_value(spec, scenario, point) - float(expected["objective"])
            ) > 5 * TOLERANCE:
                raise RuntimeError(
                    f"ruas optimum {exercise_id}/{scenario_id} tidak bernilai sama"
                )
        output["segment"] = [
            [_clean(item) for item in endpoint] for endpoint in endpoints
        ]

    if classification == "unbounded":
        improving = []
        ids = _variable_ids(spec)
        objective = scenario["objective"]
        for ray in spec.get("recession_certificates", ()):
            direction = dict(zip(ids, map(float, ray["direction"]), strict=True))
            slope = sum(
                float(coefficient) * direction[variable_id]
                for variable_id, coefficient in objective["coefficients"].items()
            )
            improves = (
                objective["sense"] == "maximize" and slope > TOLERANCE
            ) or (objective["sense"] == "minimize" and slope < -TOLERANCE)
            if improves:
                improving.append(
                    {
                        "id": ray["id"],
                        "objective_slope": _clean(slope),
                    }
                )
        if not improving:
            raise RuntimeError(
                f"tidak ada sertifikat arah yang memperbaiki {exercise_id}/{scenario_id}"
            )
        output["improving_ray_certificates"] = improving

    return output


def solve_all(data: dict[str, Any]) -> dict[str, Any]:
    exercises: dict[str, Any] = {}
    for exercise_id in data["exercise_order"]:
        spec = data["exercises"][exercise_id]
        geometry = verify_geometry(exercise_id, spec)
        if spec["model_status"] != "executable":
            exercises[exercise_id] = {
                "execution": {
                    "reason": spec["model_status"],
                    "status": "not_run",
                },
                "geometry": geometry,
                "model_status": spec["model_status"],
                "required_parameters": spec["required_parameters"],
                "scenarios": {},
            }
            continue
        scenarios = {
            scenario_id: solve_scenario(exercise_id, spec, scenario_id)
            for scenario_id in spec["scenarios"]
        }
        exercises[exercise_id] = {
            "geometry": geometry,
            "model_status": spec["model_status"],
            "scenarios": scenarios,
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
    }
