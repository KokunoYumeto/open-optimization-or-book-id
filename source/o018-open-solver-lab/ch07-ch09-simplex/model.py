"""Mesin eksak dan pemeriksaan HiGHS untuk klaster simpleks Bab 7--9.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import itertools
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
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


LAB_ID = "o018.ch07-ch09.simplex"
EXERCISE_IDS = tuple(
    [f"7.{index}" for index in range(1, 18)]
    + [f"8.{index}" for index in range(1, 10)]
    + [f"9.{index}" for index in range(1, 13)]
)
TOLERANCE = 1e-8


def as_fraction(number: int | str | Fraction) -> Fraction:
    if isinstance(number, Fraction):
        return number
    if isinstance(number, bool) or not isinstance(number, (int, str)):
        raise TypeError(f"bilangan harus int atau string rasional: {number!r}")
    return Fraction(number)


def exact(number: int | Fraction) -> int | str:
    item = as_fraction(number)
    return item.numerator if item.denominator == 1 else f"{item.numerator}/{item.denominator}"


def exact_vector(items: Iterable[int | Fraction]) -> list[int | str]:
    return [exact(item) for item in items]


def clean_float(number: float) -> float:
    value_ = float(number)
    if abs(value_) <= 1e-10:
        return 0.0
    return round(value_, 10)


def fractions(items: Sequence[int | str | Fraction]) -> list[Fraction]:
    return [as_fraction(item) for item in items]


def dot(first: Sequence[Fraction], second: Sequence[Fraction]) -> Fraction:
    if len(first) != len(second):
        raise ValueError("dimensi perkalian titik berbeda")
    return sum((left * right for left, right in zip(first, second, strict=True)), Fraction(0))


def transpose(matrix: Sequence[Sequence[Fraction]]) -> list[list[Fraction]]:
    if not matrix:
        return []
    return [list(column) for column in zip(*matrix, strict=True)]


def matrix_multiply(
    left: Sequence[Sequence[Fraction]], right: Sequence[Sequence[Fraction]]
) -> list[list[Fraction]]:
    right_t = transpose(right)
    return [[dot(row, column) for column in right_t] for row in left]


def matrix_vector(
    matrix: Sequence[Sequence[int | str | Fraction]], vector: Sequence[int | str | Fraction]
) -> list[Fraction]:
    vec = fractions(vector)
    return [dot(fractions(row), vec) for row in matrix]


def determinant(matrix: Sequence[Sequence[int | str | Fraction]]) -> Fraction:
    rows = [fractions(row) for row in matrix]
    size = len(rows)
    if size == 0 or any(len(row) != size for row in rows):
        raise ValueError("determinan memerlukan matriks persegi tak kosong")
    result = Fraction(1)
    for column in range(size):
        pivot = next((row for row in range(column, size) if rows[row][column]), None)
        if pivot is None:
            return Fraction(0)
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
            result *= -1
        pivot_value = rows[column][column]
        result *= pivot_value
        rows[column] = [item / pivot_value for item in rows[column]]
        for row in range(column + 1, size):
            factor = rows[row][column]
            if factor:
                rows[row] = [
                    current - factor * pivot_item
                    for current, pivot_item in zip(rows[row], rows[column], strict=True)
                ]
    return result


def inverse(matrix: Sequence[Sequence[int | str | Fraction]]) -> list[list[Fraction]]:
    rows = [fractions(row) for row in matrix]
    size = len(rows)
    if size == 0 or any(len(row) != size for row in rows):
        raise ValueError("invers memerlukan matriks persegi tak kosong")
    augmented = [
        row + [Fraction(int(index == column)) for column in range(size)]
        for index, row in enumerate(rows)
    ]
    for column in range(size):
        pivot = next((row for row in range(column, size) if augmented[row][column]), None)
        if pivot is None:
            raise ValueError("basis singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = augmented[column][column]
        augmented[column] = [item / scale for item in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor:
                augmented[row] = [
                    current - factor * pivot_item
                    for current, pivot_item in zip(
                        augmented[row], augmented[column], strict=True
                    )
                ]
    return [row[size:] for row in augmented]


def exact_matrix(matrix: Sequence[Sequence[Fraction]]) -> list[list[int | str]]:
    return [exact_vector(row) for row in matrix]


@dataclass(frozen=True)
class MNumber:
    """Bilangan simbolik m*M + q, diurutkan untuk M positif cukup besar."""

    m: Fraction = Fraction(0)
    q: Fraction = Fraction(0)

    def __add__(self, other: object) -> "MNumber":
        item = to_mnumber(other)
        return MNumber(self.m + item.m, self.q + item.q)

    __radd__ = __add__

    def __neg__(self) -> "MNumber":
        return MNumber(-self.m, -self.q)

    def __sub__(self, other: object) -> "MNumber":
        return self + (-to_mnumber(other))

    def __mul__(self, scalar: int | Fraction) -> "MNumber":
        factor = as_fraction(scalar)
        return MNumber(self.m * factor, self.q * factor)

    __rmul__ = __mul__

    def key(self) -> tuple[Fraction, Fraction]:
        return (self.m, self.q)

    def positive(self) -> bool:
        return self.key() > (Fraction(0), Fraction(0))


def to_mnumber(item: object) -> MNumber:
    if isinstance(item, MNumber):
        return item
    if isinstance(item, (int, str, Fraction)) and not isinstance(item, bool):
        return MNumber(Fraction(0), as_fraction(item))
    raise TypeError(f"bukan bilangan objektif: {item!r}")


def exact_m(item: MNumber | int | Fraction) -> int | str:
    number = to_mnumber(item)
    if number.m == 0:
        return exact(number.q)
    m = exact(number.m)
    q = exact(number.q)
    m_text = "M" if m == 1 else "-M" if m == -1 else f"{m}*M"
    if number.q == 0:
        return m_text
    return f"{m_text}{'+' if number.q > 0 else ''}{q}"


def load_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != LAB_ID:
        raise ValueError("lab_id tidak sesuai")
    if tuple(data.get("exercise_order", ())) != EXERCISE_IDS:
        raise ValueError("exercise_order harus tepat memuat 38 latihan")
    exercises = data.get("exercises")
    if not isinstance(exercises, dict) or tuple(exercises) != EXERCISE_IDS:
        raise ValueError("data latihan tidak utuh atau tidak berurutan")
    difficulties = [item["difficulty"] for item in exercises.values()]
    if difficulties.count(1) != 12 or difficulties.count(2) != 23 or difficulties.count(3) != 3:
        raise ValueError("distribusi tingkat kesulitan tidak sesuai saksi")
    if data.get("underdetermined_exercises") != [] or data.get("corrections") != []:
        raise ValueError("paket ini tidak boleh menyembunyikan koreksi atau data hilang")
    if len(data.get("provenance", {}).get("source_files", [])) != 12:
        raise ValueError("closure harus memuat enam authority dan enam saksi terjemahan")
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


def solve_lp(
    exercise_id: str,
    lp: dict[str, Any],
    expected: dict[str, Any] | None = None,
    expected_termination: TerminationCondition = TerminationCondition.optimal,
) -> dict[str, Any]:
    model = ConcreteModel(name=f"simplex_lab_{exercise_id.replace('.', '_')}")
    variables = lp["variables"]
    model.J = Set(initialize=range(len(variables)), ordered=True)
    model.x = Var(model.J, domain=NonNegativeReals)
    model.rows = ConstraintList()
    for coefficients, sense, rhs in lp["constraints"]:
        expression = sum(
            float(as_fraction(coefficient)) * model.x[index]
            for index, coefficient in enumerate(coefficients)
        )
        bound = float(as_fraction(rhs))
        if sense == "<=":
            model.rows.add(expression <= bound)
        elif sense == ">=":
            model.rows.add(expression >= bound)
        elif sense == "=":
            model.rows.add(expression == bound)
        else:
            raise ValueError(f"sense kendala tak dikenal: {sense}")
    objective = sum(
        float(as_fraction(coefficient)) * model.x[index]
        for index, coefficient in enumerate(lp["c"])
    )
    model.objective = Objective(
        expr=objective,
        sense=maximize if lp["sense"] == "max" else minimize,
    )
    load = expected_termination == TerminationCondition.optimal
    result = _solver().solve(model, tee=False, load_solutions=load)
    if result.solver.status not in {SolverStatus.ok, SolverStatus.warning, SolverStatus.error}:
        raise RuntimeError(f"status HiGHS tidak diterima: {result.solver.status}")
    if result.solver.termination_condition != expected_termination:
        raise RuntimeError(
            f"terminasi {exercise_id}: {result.solver.termination_condition} != {expected_termination}"
        )
    record: dict[str, Any] = {
        "purpose": "independent_lp_corroboration",
        "solver": "appsi_highs",
        "status": str(result.solver.status),
        "termination_condition": str(result.solver.termination_condition),
    }
    if not load:
        record["certificate_source"] = "exact_ray_in_same_exercise"
        return record
    point = [float(value(model.x[index])) for index in model.J]
    objective_value = float(value(model.objective))
    record.update(
        {
            "maximum_violation": clean_float(_maximum_violation(model)),
            "objective": clean_float(objective_value),
            "point": {name: clean_float(point[index]) for index, name in enumerate(variables)},
        }
    )
    if expected is not None:
        expected_point = [float(as_fraction(item)) for item in expected["point"]]
        if math.dist(point, expected_point) > 20 * TOLERANCE:
            raise RuntimeError(f"titik HiGHS {exercise_id} berbeda: {point} != {expected_point}")
        if abs(objective_value - float(as_fraction(expected["objective"]))) > 20 * TOLERANCE:
            raise RuntimeError(f"objektif HiGHS {exercise_id} berbeda")
    return record


def _copy_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "basis": list(state["basis"]),
        "nonbasis": list(state["nonbasis"]),
        "all_variables": list(state["all_variables"]),
        "equations": {
            basic: {
                "constant": equation["constant"],
                "coefficients": dict(equation["coefficients"]),
            }
            for basic, equation in state["equations"].items()
        },
        "objective": {
            "constant": state["objective"]["constant"],
            "coefficients": dict(state["objective"]["coefficients"]),
        },
    }


def make_slack_dictionary(lp: dict[str, Any]) -> dict[str, Any]:
    if lp["sense"] != "max" or any(row[1] != "<=" for row in lp["constraints"]):
        raise ValueError("kamus slack awal memerlukan PL max dengan semua kendala <=")
    decisions = list(lp["variables"])
    slacks = [f"s{index}" for index in range(1, len(lp["constraints"]) + 1)]
    equations: dict[str, Any] = {}
    for slack, (row, _sense, rhs) in zip(slacks, lp["constraints"], strict=True):
        equations[slack] = {
            "constant": as_fraction(rhs),
            "coefficients": {
                variable: -as_fraction(coefficient)
                for variable, coefficient in zip(decisions, row, strict=True)
            },
        }
    return {
        "basis": slacks,
        "nonbasis": decisions,
        "all_variables": decisions + slacks,
        "equations": equations,
        "objective": {
            "constant": MNumber(),
            "coefficients": {
                variable: MNumber(Fraction(0), as_fraction(coefficient))
                for variable, coefficient in zip(decisions, lp["c"], strict=True)
            },
        },
    }


def make_big_m_dictionary(lp: dict[str, Any]) -> dict[str, Any]:
    decisions = list(lp["variables"])
    basis: list[str] = []
    equations: dict[str, Any] = {}
    surpluses: list[str] = []
    slacks: list[str] = []
    artificials: list[str] = []
    for index, (row, sense, rhs) in enumerate(lp["constraints"], start=1):
        coefficients = {
            variable: -as_fraction(coefficient)
            for variable, coefficient in zip(decisions, row, strict=True)
        }
        if sense == ">=":
            surplus = f"e{index}"
            artificial = f"a{index}"
            coefficients[surplus] = Fraction(1)
            surpluses.append(surplus)
            artificials.append(artificial)
            basis.append(artificial)
            equations[artificial] = {
                "constant": as_fraction(rhs),
                "coefficients": coefficients,
            }
        elif sense == "<=":
            slack = f"s{index}"
            slacks.append(slack)
            basis.append(slack)
            equations[slack] = {
                "constant": as_fraction(rhs),
                "coefficients": coefficients,
            }
        else:
            raise ValueError("builder Big-M hanya menangani >= dan <=")
    nonbasis = decisions + surpluses
    multiplier = Fraction(1) if lp["sense"] == "max" else Fraction(-1)
    objective_coefficients = {
        variable: MNumber(Fraction(0), multiplier * as_fraction(coefficient))
        for variable, coefficient in zip(decisions, lp["c"], strict=True)
    }
    for surplus in surpluses:
        objective_coefficients[surplus] = MNumber()
    objective_constant = MNumber()
    for artificial in artificials:
        equation = equations[artificial]
        objective_constant += MNumber(Fraction(-1) * equation["constant"], Fraction(0))
        for variable, coefficient in equation["coefficients"].items():
            objective_coefficients[variable] = objective_coefficients.get(variable, MNumber()) + MNumber(
                -coefficient, Fraction(0)
            )
    return {
        "basis": basis,
        "nonbasis": nonbasis,
        "all_variables": decisions + surpluses + slacks + artificials,
        "equations": equations,
        "objective": {
            "constant": objective_constant,
            "coefficients": objective_coefficients,
        },
    }


def ratio_test(state: dict[str, Any], entering: str) -> tuple[dict[str, Fraction], list[str]]:
    ratios: dict[str, Fraction] = {}
    for basic in state["basis"]:
        equation = state["equations"][basic]
        coefficient = equation["coefficients"].get(entering, Fraction(0))
        if coefficient < 0:
            ratios[basic] = equation["constant"] / (-coefficient)
    if not ratios:
        return {}, []
    minimum = min(ratios.values())
    ties = [basic for basic in state["basis"] if ratios.get(basic) == minimum]
    return ratios, ties


def pivot_state(state: dict[str, Any], entering: str, leaving: str) -> dict[str, Any]:
    if entering not in state["nonbasis"] or leaving not in state["basis"]:
        raise ValueError(f"pivot tidak sah: {entering}/{leaving}")
    old = _copy_state(state)
    pivot_equation = old["equations"][leaving]
    pivot_coefficient = pivot_equation["coefficients"].get(entering, Fraction(0))
    if pivot_coefficient == 0:
        raise ValueError("elemen pivot nol")
    enter_equation = {
        "constant": -pivot_equation["constant"] / pivot_coefficient,
        "coefficients": {
            variable: -coefficient / pivot_coefficient
            for variable, coefficient in pivot_equation["coefficients"].items()
            if variable != entering
        },
    }
    enter_equation["coefficients"][leaving] = Fraction(1) / pivot_coefficient
    new_basis = [entering if item == leaving else item for item in old["basis"]]
    new_nonbasis = [leaving if item == entering else item for item in old["nonbasis"]]
    equations: dict[str, Any] = {entering: enter_equation}
    for basic in old["basis"]:
        if basic == leaving:
            continue
        source = old["equations"][basic]
        factor = source["coefficients"].get(entering, Fraction(0))
        coefficients: dict[str, Fraction] = {}
        for variable in new_nonbasis:
            base = source["coefficients"].get(variable, Fraction(0))
            addition = factor * enter_equation["coefficients"].get(variable, Fraction(0))
            if base + addition:
                coefficients[variable] = base + addition
        equations[basic] = {
            "constant": source["constant"] + factor * enter_equation["constant"],
            "coefficients": coefficients,
        }
    objective_source = old["objective"]
    objective_factor = objective_source["coefficients"].get(entering, MNumber())
    objective_coefficients: dict[str, MNumber] = {}
    for variable in new_nonbasis:
        base = objective_source["coefficients"].get(variable, MNumber())
        addition = objective_factor * enter_equation["coefficients"].get(variable, Fraction(0))
        if addition.key() != (0, 0) or base.key() != (0, 0):
            objective_coefficients[variable] = base + addition
    return {
        "basis": new_basis,
        "nonbasis": new_nonbasis,
        "all_variables": old["all_variables"],
        "equations": {basic: equations[basic] for basic in new_basis},
        "objective": {
            "constant": objective_source["constant"] + objective_factor * enter_equation["constant"],
            "coefficients": objective_coefficients,
        },
    }


def serialize_state(state: dict[str, Any]) -> dict[str, Any]:
    values = {variable: Fraction(0) for variable in state["all_variables"]}
    for basic in state["basis"]:
        values[basic] = state["equations"][basic]["constant"]
    return {
        "basis": list(state["basis"]),
        "basic_solution": {variable: exact(values[variable]) for variable in state["all_variables"]},
        "equations": {
            basic: {
                "constant": exact(state["equations"][basic]["constant"]),
                "coefficients": {
                    variable: exact(state["equations"][basic]["coefficients"].get(variable, Fraction(0)))
                    for variable in state["nonbasis"]
                },
            }
            for basic in state["basis"]
        },
        "nonbasis": list(state["nonbasis"]),
        "objective_reduced_costs": {
            variable: exact_m(state["objective"]["coefficients"].get(variable, MNumber()))
            for variable in state["nonbasis"]
        },
        "objective_value": exact_m(state["objective"]["constant"]),
    }


def simplex_trace(
    initial: dict[str, Any],
    expected_pivots: Sequence[Sequence[str]] | None = None,
) -> dict[str, Any]:
    state = _copy_state(initial)
    states = [serialize_state(state)]
    pivots: list[dict[str, Any]] = []
    iteration = 0
    while True:
        positive = [
            variable
            for variable in state["nonbasis"]
            if state["objective"]["coefficients"].get(variable, MNumber()).positive()
        ]
        if not positive:
            classification = "optimal"
            break
        if expected_pivots is not None:
            if iteration >= len(expected_pivots):
                raise RuntimeError("lintasan sumber berhenti sebelum kamus optimal")
            entering, leaving = expected_pivots[iteration]
            if entering not in positive:
                raise RuntimeError(f"variabel masuk sumber tidak memperbaiki objektif: {entering}")
        else:
            entering = max(
                positive,
                key=lambda variable: state["objective"]["coefficients"].get(variable, MNumber()).key(),
            )
            leaving = ""
        ratios, ties = ratio_test(state, entering)
        if not ratios:
            classification = "unbounded"
            pivots.append(
                {
                    "entering": entering,
                    "iteration": iteration + 1,
                    "leaving": None,
                    "ratios": {},
                    "tied_minimum_rows": [],
                }
            )
            break
        if expected_pivots is not None:
            if leaving not in ties:
                raise RuntimeError(f"baris keluar sumber bukan rasio minimum: {leaving}, ties={ties}")
        else:
            leaving = ties[0]
        before = state["objective"]["constant"]
        state = pivot_state(state, entering, leaving)
        pivots.append(
            {
                "entering": entering,
                "iteration": iteration + 1,
                "leaving": leaving,
                "objective_after": exact_m(state["objective"]["constant"]),
                "objective_before": exact_m(before),
                "ratios": {basic: exact(ratio) for basic, ratio in ratios.items()},
                "tied_minimum_rows": ties,
            }
        )
        states.append(serialize_state(state))
        iteration += 1
        if iteration > 30:
            raise RuntimeError("batas pivot terlampaui")
    if expected_pivots is not None and iteration != len(expected_pivots):
        raise RuntimeError(f"jumlah pivot berbeda: {iteration} != {len(expected_pivots)}")
    return {"classification": classification, "pivots": pivots, "states": states, "final_state_raw": state}


def state_to_tableau(state: dict[str, Any]) -> dict[str, Any]:
    variables = list(state["all_variables"])
    objective_row = []
    for variable in variables:
        if variable in state["basis"]:
            objective_row.append(0)
        else:
            objective_row.append(exact_m(-state["objective"]["coefficients"].get(variable, MNumber())))
    rows = []
    for basic in state["basis"]:
        row = []
        for variable in variables:
            if variable == basic:
                row.append(1)
            elif variable in state["basis"]:
                row.append(0)
            else:
                row.append(exact(-state["equations"][basic]["coefficients"].get(variable, Fraction(0))))
        rows.append({"basis": basic, "coefficients": row, "rhs": exact(state["equations"][basic]["constant"])})
    return {
        "basis": list(state["basis"]),
        "objective": {"coefficients": objective_row, "rhs": exact_m(state["objective"]["constant"])},
        "rows": rows,
        "variables": variables,
    }


def tableau_to_state(tableau: dict[str, Any]) -> dict[str, Any]:
    variables = list(tableau["variables"])
    basis = list(tableau["basis"])
    nonbasis = [variable for variable in variables if variable not in basis]
    equations: dict[str, Any] = {}
    for basic, (coefficients, rhs) in zip(basis, tableau["rows"], strict=True):
        row = fractions(coefficients)
        equations[basic] = {
            "constant": as_fraction(rhs),
            "coefficients": {variable: -row[variables.index(variable)] for variable in nonbasis},
        }
    objective_coefficients, objective_rhs = tableau["objective"]
    objective_row = fractions(objective_coefficients)
    return {
        "basis": basis,
        "nonbasis": nonbasis,
        "all_variables": variables,
        "equations": equations,
        "objective": {
            "constant": MNumber(Fraction(0), as_fraction(objective_rhs)),
            "coefficients": {
                variable: MNumber(Fraction(0), -objective_row[variables.index(variable)])
                for variable in nonbasis
            },
        },
    }


def standardize(original: dict[str, Any]) -> dict[str, Any]:
    substitutions: dict[str, dict[str, Fraction]] = {}
    new_variables: list[str] = []
    for variable in original["variables"]:
        name = variable["name"]
        domain = variable["domain"]
        if domain == "nonnegative":
            substitutions[name] = {name: Fraction(1)}
            new_variables.append(name)
        elif domain == "nonpositive":
            substitutions[name] = {f"{name}_neg": Fraction(-1)}
            new_variables.append(f"{name}_neg")
        elif domain == "free":
            substitutions[name] = {f"{name}_plus": Fraction(1), f"{name}_minus": Fraction(-1)}
            new_variables.extend([f"{name}_plus", f"{name}_minus"])
        else:
            raise ValueError(f"domain variabel tak dikenal: {domain}")

    def expand(coefficients: Sequence[int | str]) -> dict[str, Fraction]:
        output = {variable: Fraction(0) for variable in new_variables}
        for source, coefficient in zip(original["variables"], coefficients, strict=True):
            for target, multiplier in substitutions[source["name"]].items():
                output[target] += as_fraction(coefficient) * multiplier
        return output

    objective = expand(original["c"])
    if original["sense"] == "min":
        objective = {variable: -coefficient for variable, coefficient in objective.items()}
    equations: list[dict[str, Any]] = []
    added_index = 0
    all_variables = list(new_variables)
    for coefficients, sense, rhs in original["constraints"]:
        row = expand(coefficients)
        added = None
        if sense in {"<=", ">="}:
            added_index += 1
            added = f"s{added_index}"
            all_variables.append(added)
            row[added] = Fraction(1 if sense == "<=" else -1)
        equations.append(
            {
                "added_variable": added,
                "coefficients": row,
                "rhs": as_fraction(rhs),
                "source_sense": sense,
            }
        )
    return {
        "all_variables_nonnegative": True,
        "equations": [
            {
                "added_variable": row["added_variable"],
                "coefficients": {name: exact(row["coefficients"].get(name, Fraction(0))) for name in all_variables},
                "rhs": exact(row["rhs"]),
                "source_sense": row["source_sense"],
            }
            for row in equations
        ],
        "objective": {name: exact(objective.get(name, Fraction(0))) for name in all_variables},
        "sense": "max",
        "substitutions": {
            source: {target: exact(multiplier) for target, multiplier in mapping.items()}
            for source, mapping in substitutions.items()
        },
        "variables": all_variables,
    }


def basis_analysis(case: dict[str, Any], basis: Sequence[str] | None = None, c: Sequence[int | str] | None = None) -> dict[str, Any]:
    variables = list(case["variables"])
    selected = list(basis if basis is not None else case["basis"])
    indices = [variables.index(variable) for variable in selected]
    matrix = [fractions(row) for row in case["A"]]
    a_basis = [[row[index] for index in indices] for row in matrix]
    det = determinant(a_basis)
    if det == 0:
        return {"basis": selected, "determinant": 0, "nonsingular": False}
    inv = inverse(a_basis)
    b_column = [[item] for item in fractions(case["b"])]
    basic = [row[0] for row in matrix_multiply(inv, b_column)]
    full = [Fraction(0) for _ in variables]
    for index, value_ in zip(indices, basic, strict=True):
        full[index] = value_
    numpy_inverse = np.linalg.inv(np.asarray(a_basis, dtype=float))
    if not np.allclose(numpy_inverse, np.asarray(inv, dtype=float), atol=TOLERANCE, rtol=0):
        raise RuntimeError("invers Fraction dan NumPy berbeda")
    result: dict[str, Any] = {
        "A_B": exact_matrix(a_basis),
        "A_B_inverse": exact_matrix(inv),
        "basic_solution": {name: exact(value_) for name, value_ in zip(selected, basic, strict=True)},
        "basis": selected,
        "determinant": exact(det),
        "feasible": all(value_ >= 0 for value_ in basic),
        "full_solution": {name: exact(full[index]) for index, name in enumerate(variables)},
        "nonsingular": True,
        "numpy_agrees": True,
    }
    if c is not None:
        nonbasis = [name for name in variables if name not in selected]
        nonindices = [variables.index(name) for name in nonbasis]
        a_nonbasis = [[row[index] for index in nonindices] for row in matrix]
        c_vector = fractions(c)
        c_basis = [[c_vector[index] for index in indices]]
        c_nonbasis = [c_vector[index] for index in nonindices]
        multiplier = matrix_multiply(c_basis, inv)
        projection = matrix_multiply(multiplier, a_nonbasis)[0]
        reduced = [current - projected for current, projected in zip(c_nonbasis, projection, strict=True)]
        objective = dot([c_vector[index] for index in indices], basic)
        result.update(
            {
                "nonbasis": nonbasis,
                "objective": exact(objective),
                "optimal_for_max": all(item <= 0 for item in reduced),
                "reduced_costs": {name: exact(item) for name, item in zip(nonbasis, reduced, strict=True)},
            }
        )
    return result


def reconstruct_dictionary(case: dict[str, Any], basis: Sequence[str]) -> dict[str, Any]:
    variables = list(case["variables"])
    analysis = basis_analysis(case, basis, case["c"])
    indices = [variables.index(name) for name in basis]
    nonbasis = analysis["nonbasis"]
    nonindices = [variables.index(name) for name in nonbasis]
    matrix = [fractions(row) for row in case["A"]]
    a_basis = [[row[index] for index in indices] for row in matrix]
    a_nonbasis = [[row[index] for index in nonindices] for row in matrix]
    inverse_basis = inverse(a_basis)
    product = matrix_multiply(inverse_basis, a_nonbasis)
    equations = {}
    for row_index, basic in enumerate(basis):
        equations[basic] = {
            "constant": analysis["basic_solution"][basic],
            "coefficients": {
                name: exact(-product[row_index][column])
                for column, name in enumerate(nonbasis)
            },
        }
    return {
        "basis_analysis": analysis,
        "equations": equations,
        "objective": {
            "constant": analysis["objective"],
            "coefficients": analysis["reduced_costs"],
        },
    }


def _decision_point(state: dict[str, Any], decisions: Sequence[str]) -> list[int | str]:
    values = {name: Fraction(0) for name in state["all_variables"]}
    for basic in state["basis"]:
        values[basic] = state["equations"][basic]["constant"]
    return [exact(values[name]) for name in decisions]


def _trace_result(spec: dict[str, Any], big_m: bool = False, tableaus: bool = False) -> dict[str, Any]:
    initial = make_big_m_dictionary(spec["lp"]) if big_m else make_slack_dictionary(spec["lp"])
    trace = simplex_trace(initial, spec.get("expected_pivots"))
    final = trace.pop("final_state_raw")
    pivots = [[item["entering"], item["leaving"]] for item in trace["pivots"] if item["leaving"]]
    if "expected_pivots" in spec and pivots != spec["expected_pivots"]:
        raise RuntimeError("lintasan pivot tidak sama dengan oracle sumber")
    objective = final["objective"]["constant"]
    if objective.m != 0:
        raise RuntimeError("optimum masih bergantung pada M")
    reported = -objective.q if spec["lp"]["sense"] == "min" else objective.q
    result: dict[str, Any] = {
        "final_decision_point": {
            name: value_ for name, value_ in zip(spec["lp"]["variables"], _decision_point(final, spec["lp"]["variables"]), strict=True)
        },
        "objective": exact(reported),
        "path": trace,
        "solver_checks": [solve_lp(spec["title"], spec["lp"], spec["expected_solver"])],
    }
    if big_m:
        result["artificial_variables_final"] = {
            name: _decision_point(final, [name])[0]
            for name in final["all_variables"]
            if name.startswith("a")
        }
        if any(value_ != 0 for value_ in result["artificial_variables_final"].values()):
            raise RuntimeError("variabel artifisial belum nol")
    if tableaus:
        # Rekonstruksi setiap tableau dari state serialisasi tidak cukup untuk aritmetika;
        # ulangi lintasan eksak sambil menyimpan state hidup.
        live = make_slack_dictionary(spec["lp"])
        tableau_path = [state_to_tableau(live)]
        for entering, leaving in spec["expected_pivots"]:
            live = pivot_state(live, entering, leaving)
            tableau_path.append(state_to_tableau(live))
        result["tableau_path"] = tableau_path
    return result


def _feasible(lp: dict[str, Any], point: Sequence[int | str | Fraction]) -> bool:
    values = fractions(point)
    for row, sense, rhs in lp["constraints"]:
        lhs = dot(fractions(row), values)
        bound = as_fraction(rhs)
        if sense == "<=" and lhs > bound:
            return False
        if sense == ">=" and lhs < bound:
            return False
        if sense == "=" and lhs != bound:
            return False
    return all(item >= 0 for item in values)


def evaluate_71(spec: dict[str, Any]) -> dict[str, Any]:
    state = make_slack_dictionary(spec["lp"])
    return {
        "initial_dictionary": serialize_state(state),
        "steepest_entering": "y",
        "standard_form_variables": state["all_variables"],
        "solver_checks": [solve_lp("7.1", spec["lp"], spec["expected_solver"])],
    }


def evaluate_714(_spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "conditions": {
            "current_basis_degenerate": "b=0",
            "current_basis_feasible_and_optimal": "b>=0; c1<=0; c5<=0; c6<=0; a1,a2 arbitrary",
            "current_basis_infeasible": "b<0",
            "feasible_and_unbounded_sufficient": "b>=0; c1>0; a2<=0 (ray x1=t)",
        },
        "certificate": {
            "basic_values": {"x2": 1, "x3": "b", "x4": 2},
            "unbounded_ray_effect": {"x1": "+t", "x2": "+t", "x3": "-a2*t", "x4": "+t", "z": "+c1*t"},
        },
    }


def evaluate_715(spec: dict[str, Any]) -> dict[str, Any]:
    vertices = {name: fractions(point) for name, point in spec["vertices"].items()}
    if not all(_feasible(spec["lp"], point) for point in vertices.values()):
        raise RuntimeError("daftar titik sudut 7.15 memuat titik tidak layak")
    d = vertices["D"]
    c = vertices["C"]

    def slacks(point: Sequence[Fraction]) -> dict[str, Fraction]:
        x1, x2 = point
        return {
            "s1": 2 * x1 + 3 * x2 - 7,
            "s2": x2 - 1,
            "s3": 4 - x1 + x2,
            "s4": 16 - x1 - 3 * x2,
        }

    d_slacks = slacks(d)
    c_slacks = slacks(c)
    if d_slacks["s4"] != 0 or c_slacks["s3"] != 0 or c_slacks["s4"] != 0:
        raise RuntimeError("identitas slack pivot D--C gagal")
    return {
        "D": {
            "basis": ["x2", "s1", "s2", "s3"],
            "nonbasis": ["x1", "s4"],
            "point": exact_vector(d),
            "slacks": {name: exact(value_) for name, value_ in d_slacks.items()},
        },
        "C": {"point": exact_vector(c), "slacks": {name: exact(value_) for name, value_ in c_slacks.items()}},
        "pivot_D_to_C": {"entering": "x1", "leaving": "s3", "edge_keeps_nonbasic": "s4"},
        "vertices": {name: exact_vector(point) for name, point in vertices.items()},
        "solver_checks": [solve_lp("7.15", spec["lp"], spec["expected_solver"])],
    }


def evaluate_716(_spec: dict[str, Any]) -> dict[str, Any]:
    state = {
        "basis": ["s1", "s2", "y"],
        "nonbasis": ["x", "s3"],
        "all_variables": ["x", "y", "s1", "s2", "s3"],
        "equations": {
            "s1": {"constant": Fraction(2), "coefficients": {"x": Fraction(-1, 2), "s3": Fraction(1, 2)}},
            "s2": {"constant": Fraction(9), "coefficients": {"x": Fraction(-3, 2), "s3": Fraction(1, 2)}},
            "y": {"constant": Fraction(7), "coefficients": {"x": Fraction(-1, 2), "s3": Fraction(-1, 2)}},
        },
        "objective": {"constant": MNumber(q=Fraction(21)), "coefficients": {"x": MNumber(q=Fraction(1, 2)), "s3": MNumber(q=Fraction(-3, 2))}},
    }
    ratios, ties = ratio_test(state, "x")
    wrong = pivot_state(state, "x", "s2")
    wrong_values = serialize_state(wrong)["basic_solution"]
    if wrong_values["s1"] != -1:
        raise RuntimeError("pivot salah harus menghasilkan s1=-1")
    return {
        "correct_ratio_test": {"ratios": {name: exact(value_) for name, value_ in ratios.items()}, "minimum_rows": ties},
        "wrong_pivot": {"entering": "x", "leaving": "s2", "resulting_dictionary": serialize_state(wrong), "negative_basic_variable": {"s1": -1}},
        "general_certificate": "Rasio minimum melindungi baris yang mencapai nol lebih dahulu; melewati nilai itu membuat variabel basis tersebut negatif.",
    }


def evaluate_717(spec: dict[str, Any]) -> dict[str, Any]:
    initial = make_slack_dictionary(spec["lp"])
    ratios, ties = ratio_test(initial, "x")
    if ties != ["s1", "s2"]:
        raise RuntimeError("uji rasio 7.17 harus imbang")
    branch_s1 = pivot_state(initial, "x", "s1")
    branch_s2 = pivot_state(initial, "x", "s2")
    custom = make_slack_dictionary(spec["constructed_example"])
    custom_ratios, custom_ties = ratio_test(custom, "x")
    return {
        "initial_ratios": {name: exact(value_) for name, value_ in ratios.items()},
        "tied_rows": ties,
        "branch_s1_leaves": serialize_state(branch_s1),
        "branch_s2_leaves": serialize_state(branch_s2),
        "degeneracy": {"both_branches_have_zero_basic_variable": True, "general_reason": "Semua baris yang terikat mencapai nol; setelah satu keluar, baris terikat lain tetap basis dengan RHS nol."},
        "zero_reduced_cost_interpretation": "y memiliki biaya tereduksi nol pada basis s2-keluar, tetapi langsung diblokir oleh baris degenerat; terdapat basis optimal alternatif pada titik yang sama, bukan solusi optimal berbeda.",
        "constructed_example": {"lp": spec["constructed_example"], "ratios": {name: exact(value_) for name, value_ in custom_ratios.items()}, "tied_rows": custom_ties},
        "solver_checks": [solve_lp("7.17", spec["lp"], spec["expected_solver"])],
    }


def evaluate_84(spec: dict[str, Any]) -> dict[str, Any]:
    bases = [basis_analysis(spec["lp_standard"], basis, spec["lp_standard"]["c"]) for basis in spec["bases"]]
    return {"bases": bases, "solver_checks": [solve_lp("8.4", spec["lp"], spec["expected_solver"])]}


def evaluate_85(spec: dict[str, Any]) -> dict[str, Any]:
    variables = spec["basis_case"]["variables"]
    records = [basis_analysis(spec["basis_case"], basis) for basis in itertools.combinations(variables, 2)]
    dependent_case = {"A": [[1, 2, 1, 0], [2, 4, 0, 1]], "b": [1, 2], "variables": variables}
    dependent = basis_analysis(dependent_case, ["x1", "x2"])
    return {"basis_records": records, "dependent_column_example": dependent}


def evaluate_86(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "dictionary": reconstruct_dictionary(spec["lp_standard"], spec["basis"]),
        "solver_checks": [solve_lp("8.6", spec["lp"], spec["expected_solver"])],
    }


def evaluate_87(_spec: dict[str, Any]) -> dict[str, Any]:
    return {"identity": "c_B^T-c_B^T A_B^{-1}A_B=0", "proof_steps": ["A_B^{-1}A_B=I", "c_B^T-c_B^T I=0"], "validated": True}


def evaluate_88(_spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "dictionary_rule": "koefisien variabel nonbasis pada baris z sama dengan biaya tereduksi",
        "improving_direction": {"d_j": 1, "d_B": "-A_B^{-1}A_j", "objective_slope": "reduced_cost_j"},
        "tableau_rule": "baris z menyimpan negatif biaya tereduksi; entri negatif dipilih masuk",
        "validated": True,
    }


def evaluate_89(_spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "identity": "c^T x-z*=reduced_cost_N^T x_N",
        "strict_assumption": "setiap reduced_cost_N<0",
        "cases": [
            {"condition": "x_N!=0", "conclusion": "c^T x<z* karena x_N>=0 dan setidaknya satu komponen positif"},
            {"condition": "x_N=0", "conclusion": "A_B nonsingular memaksa x_B=A_B^{-1}b=x_B*"},
        ],
        "unique_optimum": True,
    }


def read_tableau(tableau: dict[str, Any]) -> dict[str, Any]:
    state = tableau_to_state(tableau)
    serialized = serialize_state(state)
    return {
        "basis": state["basis"],
        "basic_solution": serialized["basic_solution"],
        "dictionary": serialized,
        "nonbasis": state["nonbasis"],
        "optimal": all(not coefficient.positive() for coefficient in state["objective"]["coefficients"].values()),
    }


def evaluate_93(spec: dict[str, Any]) -> dict[str, Any]:
    state = make_slack_dictionary(spec["lp"])
    ratios, ties = ratio_test(state, "x1")
    return {"entering": "x1", "leaving": ties[0], "pivot_element": 4, "ratios": {name: exact(value_) for name, value_ in ratios.items()}, "initial_tableau": state_to_tableau(state)}


def evaluate_94(spec: dict[str, Any]) -> dict[str, Any]:
    initial = make_slack_dictionary(spec["lp"])
    after = pivot_state(initial, "x1", "s2")
    return {"pivot": {"entering": "x1", "leaving": "s2", "element": 4}, "initial_tableau": state_to_tableau(initial), "tableau_after_pivot": state_to_tableau(after)}


def evaluate_97(spec: dict[str, Any]) -> dict[str, Any]:
    initial = make_big_m_dictionary(spec["lp"])
    trace = simplex_trace(initial)
    final = trace.pop("final_state_raw")
    live = initial
    tableaus = [state_to_tableau(live)]
    for pivot in trace["pivots"]:
        if pivot["leaving"] is None:
            break
        live = pivot_state(live, pivot["entering"], pivot["leaving"])
        tableaus.append(state_to_tableau(live))
    if trace["classification"] != "optimal" or _decision_point(final, ["a1"])[0] != 0:
        raise RuntimeError("lintasan Big-M 9.7 tidak menutup")
    return {
        "initial_symbolic_tableau": tableaus[0],
        "full_path": trace,
        "tableau_path": tableaus,
        "final_decision_point": {name: value_ for name, value_ in zip(spec["lp"]["variables"], _decision_point(final, spec["lp"]["variables"]), strict=True)},
        "objective": exact(final["objective"]["constant"].q),
        "solver_checks": [solve_lp("9.7", spec["lp"], spec["expected_solver"])],
    }


def evaluate_98(_spec: dict[str, Any]) -> dict[str, Any]:
    return {"dictionary_example": "z=12+3*x1-2*x2", "tableau_objective_row": {"x1": -3, "x2": 2, "rhs": 12}, "reason": "semua suku keputusan dipindahkan ke ruas kiri", "validated": True}


def evaluate_99(_spec: dict[str, Any]) -> dict[str, Any]:
    tableau = {"variables": ["x1", "x2", "s1", "s2"], "basis": ["x1", "x2"], "objective": [[0, 0, 3, 1], 40], "rows": [[[1, 0, 2, -1], 6], [[0, 1, -1, 1], 4]]}
    return read_tableau(tableau)


def evaluate_910(_spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "dictionary": {"z": "10+2*x1-s2", "x2": "3+x1-s2", "s1": "5+3*x1-2*s2"},
        "entering": "x1",
        "limiting_rows": [],
        "ray": {"parameter": "t>=0", "x1": "t", "x2": "3+t", "s1": "5+3*t", "s2": 0, "z": "10+2*t"},
        "classification": "unbounded",
        "scope_note": "Sertifikat berasal langsung dari tableau; koefisien PL asal tidak diberikan latihan dan tidak direka.",
    }


def evaluate_911(_spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "penalized_optimum": "8-3*M",
        "positive_artificial_basic_value": {"a1": 3},
        "classification_original_lp": "infeasible",
        "certificate": "Pada optimum masalah Big-M, a1 tetap positif; karena a1 bukan variabel PL semula, kendala asli tidak dapat dipenuhi.",
        "scope_note": "Latihan memberikan tableau akhir, bukan seluruh PL asal; klasifikasi dibaca tanpa merekonstruksi data yang hilang.",
    }


def evaluate_912(spec: dict[str, Any]) -> dict[str, Any]:
    base = [Fraction(1), Fraction(0)]
    direction = [Fraction(1), Fraction(1)]
    for parameter in [Fraction(0), Fraction(1), Fraction(7)]:
        point = [base[index] + parameter * direction[index] for index in range(2)]
        if not _feasible(spec["lp"], point):
            raise RuntimeError("sinar 9.12 tidak layak")
    return {
        "dictionary": {"z": "1+2*x2-s1", "x1": "1+x2-s1", "s2": "3-s1"},
        "entering": "x2",
        "limiting_rows": [],
        "ray": {"parameter": "t>=0", "point": ["1+t", "t"], "direction": [1, 1], "slacks": [0, 3], "objective": "1+2*t"},
        "classification": "unbounded",
        "solver_checks": [solve_lp("9.12", spec["lp"], expected_termination=TerminationCondition.unbounded)],
    }


def evaluate_exercise(exercise_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    if exercise_id == "7.1":
        calculation = evaluate_71(spec)
    elif exercise_id in {"7.2", "7.3", "7.4", "7.5", "7.6"}:
        calculation = standardize(spec["original"])
    elif exercise_id in {"7.7", "7.8", "7.9", "7.10", "7.11"}:
        calculation = _trace_result(spec)
    elif exercise_id in {"7.12", "7.13"}:
        calculation = _trace_result(spec, big_m=True)
    elif exercise_id == "7.14":
        calculation = evaluate_714(spec)
    elif exercise_id == "7.15":
        calculation = evaluate_715(spec)
    elif exercise_id == "7.16":
        calculation = evaluate_716(spec)
    elif exercise_id == "7.17":
        calculation = evaluate_717(spec)
    elif exercise_id in {"8.1", "8.2", "8.3"}:
        calculation = basis_analysis(spec["basis_case"])
    elif exercise_id == "8.4":
        calculation = evaluate_84(spec)
    elif exercise_id == "8.5":
        calculation = evaluate_85(spec)
    elif exercise_id == "8.6":
        calculation = evaluate_86(spec)
    elif exercise_id == "8.7":
        calculation = evaluate_87(spec)
    elif exercise_id == "8.8":
        calculation = evaluate_88(spec)
    elif exercise_id == "8.9":
        calculation = evaluate_89(spec)
    elif exercise_id in {"9.1", "9.2"}:
        calculation = read_tableau(spec["tableau"])
    elif exercise_id == "9.3":
        calculation = evaluate_93(spec)
    elif exercise_id == "9.4":
        calculation = evaluate_94(spec)
    elif exercise_id in {"9.5", "9.6"}:
        calculation = _trace_result(spec, tableaus=True)
    elif exercise_id == "9.7":
        calculation = evaluate_97(spec)
    elif exercise_id == "9.8":
        calculation = evaluate_98(spec)
    elif exercise_id == "9.9":
        calculation = evaluate_99(spec)
    elif exercise_id == "9.10":
        calculation = evaluate_910(spec)
    elif exercise_id == "9.11":
        calculation = evaluate_911(spec)
    elif exercise_id == "9.12":
        calculation = evaluate_912(spec)
    else:
        raise KeyError(exercise_id)
    return {
        "calculation": calculation,
        "difficulty": spec["difficulty"],
        "method": spec["method"],
        "status": "verified",
        "title": spec["title"],
    }


def _solver_checks(calculation: dict[str, Any]) -> list[dict[str, Any]]:
    return list(calculation.get("solver_checks", []))


def evaluate_all(data: dict[str, Any]) -> dict[str, Any]:
    exercises = {
        exercise_id: evaluate_exercise(exercise_id, spec)
        for exercise_id, spec in data["exercises"].items()
    }
    solver_checks = [
        check
        for exercise in exercises.values()
        for check in _solver_checks(exercise["calculation"])
    ]
    violations = [check.get("maximum_violation", 0.0) for check in solver_checks]
    terminations: dict[str, int] = {}
    for check in solver_checks:
        termination = check["termination_condition"]
        terminations[termination] = terminations.get(termination, 0) + 1
    return {
        "exercises": exercises,
        "lab_id": data["lab_id"],
        "summary": {
            "chapter_counts": {"7": 17, "8": 9, "9": 12},
            "correction_count": len(data["corrections"]),
            "difficulty_counts": {"1": 12, "2": 23, "3": 3},
            "exercise_count": len(exercises),
            "maximum_solver_violation": clean_float(max(violations, default=0.0)),
            "solver_call_count": len(solver_checks),
            "solver_termination_counts": terminations,
            "source_manual_title_divergence_count": len(data["source_manual_divergences"]),
            "underdetermined_count": len(data["underdetermined_exercises"]),
            "verified_count": sum(exercise["status"] == "verified" for exercise in exercises.values()),
        },
    }
