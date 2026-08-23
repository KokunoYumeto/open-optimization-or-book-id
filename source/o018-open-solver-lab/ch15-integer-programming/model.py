"""Model dan sertifikat untuk laboratorium pemrograman bilangan bulat Bab 15.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable

import pyomo.environ as pyo


TOL = 1e-7


def load_data(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "authority_commit",
        "cases",
        "exercise_order",
        "exercises",
        "lab_id",
        "provenance",
        "schema_version",
        "source_defects",
        "unresolved_exercises",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"data.json tidak lengkap: {sorted(missing)}")
    if data["exercise_order"] != list(data["exercises"]):
        raise ValueError("urutan exercises tidak cocok dengan exercise_order")
    if len(data["exercise_order"]) != 16:
        raise ValueError("Bab 15 harus memiliki tepat 16 latihan")
    return data


def _clean_number(value: float, digits: int = 9) -> int | float:
    value = float(value)
    nearest = round(value)
    if abs(value - nearest) <= TOL:
        return int(nearest)
    cleaned = round(value, digits)
    return 0 if cleaned == 0 else cleaned


def _fraction(value: float, maximum_denominator: int = 1_000_000) -> str | int:
    candidate = Fraction(float(value)).limit_denominator(maximum_denominator)
    if abs(float(candidate) - float(value)) > TOL:
        raise ValueError(f"nilai {value!r} tidak dapat disertifikasi sebagai rasional")
    return candidate.numerator if candidate.denominator == 1 else str(candidate)


def _constraint_and_domain_violation(model: pyo.ConcreteModel) -> float:
    maximum = 0.0
    for constraint in model.component_data_objects(pyo.Constraint, active=True):
        body = float(pyo.value(constraint.body))
        if constraint.has_lb():
            maximum = max(maximum, float(pyo.value(constraint.lower)) - body)
        if constraint.has_ub():
            maximum = max(maximum, body - float(pyo.value(constraint.upper)))
    for variable in model.component_data_objects(pyo.Var, active=True):
        if variable.value is None:
            continue
        value = float(variable.value)
        if variable.has_lb():
            maximum = max(maximum, float(pyo.value(variable.lb)) - value)
        if variable.has_ub():
            maximum = max(maximum, value - float(pyo.value(variable.ub)))
        if variable.is_binary() or variable.is_integer():
            maximum = max(maximum, abs(value - round(value)))
    return 0.0 if maximum <= TOL else round(maximum, 12)


class SolverLedger:
    """Satu antarmuka solver dan catatan deterministik untuk semua pemanggilan."""

    def __init__(self) -> None:
        self.solver = pyo.SolverFactory("appsi_highs")
        if not self.solver.available(exception_flag=False):
            raise RuntimeError("appsi_highs tidak tersedia")
        self.records: list[dict[str, Any]] = []

    def solve(self, model: pyo.ConcreteModel, tag: str) -> None:
        result = self.solver.solve(model)
        termination = str(result.solver.termination_condition).lower()
        if termination != "optimal":
            raise RuntimeError(f"{tag}: terminasi solver {termination}")
        record = {
            "call": len(self.records) + 1,
            "maximum_violation": _constraint_and_domain_violation(model),
            "tag": tag,
            "termination_condition": termination,
        }
        self.records.append(record)


def _metadata(data: dict[str, Any], exercise_id: str) -> dict[str, Any]:
    spec = data["exercises"][exercise_id]
    return {
        "book_label": spec["book_label"],
        "difficulty": spec["difficulty"],
        "group": spec["group"],
        "manual_mapping": spec["manual_mapping"],
        "method": spec["method"],
        "title": spec["title"],
    }


def _attach_checks(
    payload: dict[str, Any], ledger: SolverLedger, start: int
) -> dict[str, Any]:
    payload["solver_checks"] = ledger.records[start:]
    return payload


def _binary_knapsack_model(
    weights: list[int],
    values: list[int],
    capacity: int,
    implication: tuple[int, int] | None = None,
) -> pyo.ConcreteModel:
    model = pyo.ConcreteModel()
    model.I = pyo.RangeSet(0, len(weights) - 1)
    model.x = pyo.Var(model.I, domain=pyo.Binary)
    model.capacity = pyo.Constraint(
        expr=sum(weights[i] * model.x[i] for i in model.I) <= capacity
    )
    if implication is not None:
        antecedent, consequent = implication
        model.implication = pyo.Constraint(
            expr=model.x[antecedent] <= model.x[consequent]
        )
    model.objective = pyo.Objective(
        expr=sum(values[i] * model.x[i] for i in model.I),
        sense=pyo.maximize,
    )
    return model


def _binary_vector(variable: Any, indices: Iterable[Any]) -> list[int]:
    return [int(round(float(pyo.value(variable[index])))) for index in indices]


def _enumerate_knapsack(
    weights: list[int],
    values: list[int],
    capacity: int,
    implication: tuple[int, int] | None = None,
) -> dict[str, Any]:
    feasible: list[tuple[int, tuple[int, ...], int]] = []
    for vector in itertools.product((0, 1), repeat=len(weights)):
        weight = sum(a * x for a, x in zip(weights, vector))
        if weight > capacity:
            continue
        if implication is not None and vector[implication[0]] > vector[implication[1]]:
            continue
        objective = sum(c * x for c, x in zip(values, vector))
        feasible.append((objective, vector, weight))
    optimum = max(item[0] for item in feasible)
    optima = sorted(item for item in feasible if item[0] == optimum)
    return {
        "objective": optimum,
        "optimal_vectors": [list(item[1]) for item in optima],
        "weights": [item[2] for item in optima],
    }


def _exercise_15_1(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["hiker_knapsack"]
    answers: dict[str, Any] = {}
    for key, implication, tag in (
        ("base", None, "15.1.base"),
        ("with_implication", (2, 3), "15.1.kompor_mengharuskan_makanan"),
    ):
        model = _binary_knapsack_model(
            case["weights"], case["values"], case["capacity"], implication
        )
        ledger.solve(model, tag)
        certificate = _enumerate_knapsack(
            case["weights"], case["values"], case["capacity"], implication
        )
        vector = certificate["optimal_vectors"][0]
        solver_vector = _binary_vector(model.x, model.I)
        if solver_vector not in certificate["optimal_vectors"]:
            raise RuntimeError(f"{tag}: solusi solver bukan optimum pencacahan")
        answers[key] = {
            "objective": certificate["objective"],
            "selected": [
                name for name, selected in zip(case["items"], vector) if selected
            ],
            "vector": vector,
            "weight": certificate["weights"][0],
        }
    answers["implication_constraint"] = "x_Kompor <= x_Makanan"
    return _attach_checks(answers, ledger, start)


def _exercise_15_2(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["van_knapsack"]
    model = _binary_knapsack_model(
        case["weights"], case["rewards"], case["capacity"]
    )
    ledger.solve(model, "15.2.ransel_mobil_kurir")
    certificate = _enumerate_knapsack(
        case["weights"], case["rewards"], case["capacity"]
    )
    vector = certificate["optimal_vectors"][0]
    if _binary_vector(model.x, model.I) not in certificate["optimal_vectors"]:
        raise RuntimeError("15.2: solusi solver bukan optimum pencacahan")
    payload = {
        "objective": certificate["objective"],
        "selected_packages": [
            item for item, selected in zip(case["items"], vector) if selected
        ],
        "unique_optimum": len(certificate["optimal_vectors"]) == 1,
        "vector": vector,
        "weight": certificate["weights"][0],
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_3(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["small_town"]
    districts = case["districts"]
    neighborhoods = {
        int(key): values for key, values in case["neighborhoods"].items()
    }
    model = pyo.ConcreteModel()
    model.D = pyo.Set(initialize=districts, ordered=True)
    model.x = pyo.Var(model.D, domain=pyo.Binary)
    model.cover = pyo.Constraint(
        model.D,
        rule=lambda m, district: sum(
            m.x[station]
            for station in districts
            if district in neighborhoods[station]
        )
        >= 1,
    )
    model.objective = pyo.Objective(
        expr=sum(model.x[district] for district in model.D), sense=pyo.minimize
    )
    ledger.solve(model, "15.3.penutupan_kota")
    minimum = int(round(pyo.value(model.objective)))
    optimal_placements: list[list[int]] = []
    for count in range(len(districts) + 1):
        for placement in itertools.combinations(districts, count):
            covered = set().union(*(set(neighborhoods[d]) for d in placement))
            if covered == set(districts):
                if count == minimum:
                    optimal_placements.append(list(placement))
        if optimal_placements:
            break
    payload = {
        "minimum_station_count": minimum,
        "neighborhoods": case["neighborhoods"],
        "optimal_placements": optimal_placements,
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_4(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["big_m_activation"]
    maximum_lhs = sum(case["upper_bounds"])
    payload = {
        "constraint": "x1+x2+x3 <= 40+M*delta",
        "maximum_lhs": maximum_lhs,
        "minimum_valid_M": maximum_lhs - case["inactive_rhs"],
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_5(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["terminal_location"]
    model = pyo.ConcreteModel()
    model.I = pyo.RangeSet(0, 4)
    model.y = pyo.Var(model.I, domain=pyo.Binary)
    model.limit = pyo.Constraint(
        expr=sum(model.y[i] for i in model.I) <= case["maximum_terminals"]
    )
    model.halifax_moncton = pyo.Constraint(expr=model.y[0] + model.y[1] >= 1)
    model.central = pyo.Constraint(
        expr=sum(model.y[i - 1] for i in case["central_canada"]) >= 1
    )
    model.objective = pyo.Objective(
        expr=sum(case["costs"][i] * model.y[i] for i in model.I),
        sense=pyo.minimize,
    )
    ledger.solve(model, "15.5.lokasi_terminal")
    vector = _binary_vector(model.y, model.I)
    payload = {
        "cities": [
            city for city, selected in zip(case["cities"], vector) if selected
        ],
        "objective": _clean_number(pyo.value(model.objective)),
        "vector": vector,
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_6(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["warehouse_cover"]
    warehouses = case["warehouses"]
    regions = case["regions"]
    model = pyo.ConcreteModel()
    model.W = pyo.Set(initialize=warehouses, ordered=True)
    model.y = pyo.Var(model.W, domain=pyo.Binary)
    model.cover = pyo.Constraint(
        regions,
        rule=lambda m, region: sum(
            m.y[warehouse]
            for warehouse in warehouses
            if region in case["serves"][warehouse]
        )
        >= 1,
    )
    model.objective = pyo.Objective(
        expr=sum(case["costs"][w] * model.y[w] for w in model.W),
        sense=pyo.minimize,
    )
    ledger.solve(model, "15.6.lokasi_gudang")
    vector = _binary_vector(model.y, warehouses)
    payload = {
        "classic_problem": "penutupan himpunan berbobot",
        "objective": _clean_number(pyo.value(model.objective)),
        "open_warehouses": [
            warehouse
            for warehouse, selected in zip(warehouses, vector)
            if selected
        ],
        "vector": vector,
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_7(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["capital_budgeting"]
    count = len(case["projects"])
    model = pyo.ConcreteModel()
    model.I = pyo.RangeSet(0, count - 1)
    model.x = pyo.Var(model.I, domain=pyo.Binary)
    model.budget = pyo.Constraint(
        range(2),
        rule=lambda m, year: sum(
            case["cash_outlays"][year][i] * m.x[i] for i in m.I
        )
        <= case["budgets"][year],
    )
    model.dependencies = pyo.ConstraintList()
    for project, prerequisite in case["dependencies"]:
        model.dependencies.add(model.x[project - 1] <= model.x[prerequisite - 1])
    model.exclusions = pyo.ConstraintList()
    for first, second in case["exclusive_pairs"]:
        model.exclusions.add(model.x[first - 1] + model.x[second - 1] <= 1)
    model.objective = pyo.Objective(
        expr=sum(case["npv"][i] * model.x[i] for i in model.I),
        sense=pyo.maximize,
    )
    ledger.solve(model, "15.7.penganggaran_modal")
    vector = _binary_vector(model.x, model.I)
    spending = [
        sum(outlay * selected for outlay, selected in zip(year, vector))
        for year in case["cash_outlays"]
    ]
    payload = {
        "funded_projects": [
            project
            for project, selected in zip(case["projects"], vector)
            if selected
        ],
        "npv": _clean_number(pyo.value(model.objective)),
        "spending": spending,
        "vector": vector,
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_8(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["facility"]
    model = pyo.ConcreteModel()
    model.I = pyo.RangeSet(0, 1)
    model.J = pyo.RangeSet(0, 2)
    model.y = pyo.Var(model.I, domain=pyo.Binary)
    model.x = pyo.Var(model.I, model.J, domain=pyo.NonNegativeReals)
    model.demand = pyo.Constraint(
        model.J,
        rule=lambda m, j: sum(m.x[i, j] for i in m.I) == case["demands"][j],
    )
    model.capacity = pyo.Constraint(
        model.I,
        rule=lambda m, i: sum(m.x[i, j] for j in m.J)
        <= case["capacities"][i] * m.y[i],
    )
    model.objective = pyo.Objective(
        expr=sum(case["fixed_costs"][i] * model.y[i] for i in model.I)
        + sum(
            case["service_costs"][i][j] * model.x[i, j]
            for i in model.I
            for j in model.J
        ),
        sense=pyo.minimize,
    )
    ledger.solve(model, "15.8.lokasi_fasilitas")
    vector = _binary_vector(model.y, model.I)
    allocation = [
        [_clean_number(pyo.value(model.x[i, j])) for j in model.J]
        for i in model.I
    ]
    payload = {
        "allocation": allocation,
        "cost": _clean_number(pyo.value(model.objective)),
        "open_centers": [i + 1 for i, selected in enumerate(vector) if selected],
        "total_capacity": sum(case["capacities"]),
        "total_demand": sum(case["demands"]),
        "vector": vector,
    }
    return _attach_checks(payload, ledger, start)


def _canonical_graph_coloring(
    vertices: list[str], edges: list[list[str]]
) -> tuple[int, dict[str, int]]:
    edge_indices = [
        (vertices.index(first), vertices.index(second)) for first, second in edges
    ]
    for color_count in range(1, len(vertices) + 1):
        candidates: list[tuple[int, ...]] = []
        for assignment in itertools.product(range(1, color_count + 1), repeat=len(vertices)):
            if set(assignment) != set(range(1, color_count + 1)):
                continue
            if all(assignment[i] != assignment[j] for i, j in edge_indices):
                candidates.append(assignment)
        if candidates:
            chosen = min(candidates)
            return color_count, dict(zip(vertices, chosen))
    raise RuntimeError("graf tidak dapat diwarnai")


def _exercise_15_9(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["graph_coloring"]
    vertices = case["vertices"]
    colors = list(range(1, len(vertices) + 1))
    model = pyo.ConcreteModel()
    model.V = pyo.Set(initialize=vertices, ordered=True)
    model.C = pyo.Set(initialize=colors, ordered=True)
    model.x = pyo.Var(model.V, model.C, domain=pyo.Binary)
    model.w = pyo.Var(model.C, domain=pyo.Binary)
    model.one_color = pyo.Constraint(
        model.V, rule=lambda m, vertex: sum(m.x[vertex, c] for c in m.C) == 1
    )
    model.link = pyo.Constraint(
        model.V,
        model.C,
        rule=lambda m, vertex, color: m.x[vertex, color] <= m.w[color],
    )
    model.edge = pyo.ConstraintList()
    for first, second in case["edges"]:
        for color in colors:
            model.edge.add(model.x[first, color] + model.x[second, color] <= 1)
    model.symmetry = pyo.ConstraintList()
    for color in colors[:-1]:
        model.symmetry.add(model.w[color] >= model.w[color + 1])
    model.objective = pyo.Objective(
        expr=sum(model.w[color] for color in model.C), sense=pyo.minimize
    )
    ledger.solve(model, "15.9.pewarnaan_graf")
    chromatic_number, canonical = _canonical_graph_coloring(
        vertices, case["edges"]
    )
    solver_value = int(round(pyo.value(model.objective)))
    if solver_value != chromatic_number:
        raise RuntimeError("15.9: solver dan pencacahan memberi bilangan kromatik berbeda")
    payload = {
        "canonical_coloring": canonical,
        "chromatic_number": chromatic_number,
        "lower_bound_certificate": "segitiga A-B-C",
    }
    return _attach_checks(payload, ledger, start)


def _either_or_model(
    case: dict[str, Any], m1: int, m2: int
) -> pyo.ConcreteModel:
    model = pyo.ConcreteModel()
    model.x = pyo.Var(range(2), domain=pyo.NonNegativeReals)
    model.delta = pyo.Var(domain=pyo.Binary)
    a, b = case["constraints"]
    model.mode_a = pyo.Constraint(
        expr=sum(a["coefficients"][i] * model.x[i] for i in range(2))
        <= a["rhs"] + m1 * model.delta
    )
    model.mode_b = pyo.Constraint(
        expr=sum(b["coefficients"][i] * model.x[i] for i in range(2))
        <= b["rhs"] + m2 * (1 - model.delta)
    )
    model.objective = pyo.Objective(
        expr=sum(case["objective"][i] * model.x[i] for i in range(2)),
        sense=pyo.maximize,
    )
    return model


def _exercise_15_10(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["either_or"]
    m1, m2 = case["tight_big_m"]
    model = _either_or_model(case, m1, m2)
    ledger.solve(model, "15.10.salah_satu_big_m_ketat")
    payload = {
        "delta": int(round(pyo.value(model.delta))),
        "objective": _clean_number(pyo.value(model.objective)),
        "point": [_clean_number(pyo.value(model.x[i])) for i in range(2)],
        "semantics": "formulasi Big-M menerapkan sedikitnya satu kendala, bukan tepat satu",
        "tight_big_m": [m1, m2],
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_11(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["fixed_charge"]
    model = pyo.ConcreteModel()
    model.x = pyo.Var(domain=pyo.NonNegativeReals)
    model.y = pyo.Var(domain=pyo.Binary)
    model.link = pyo.Constraint(expr=model.x <= case["capacity"] * model.y)
    unit_margin = case["price"] - case["variable_cost"]
    model.objective = pyo.Objective(
        expr=unit_margin * model.x - case["fixed_cost"] * model.y,
        sense=pyo.maximize,
    )
    ledger.solve(model, "15.11.biaya_tetap")
    payload = {
        "linking_constraint": "x <= 200*y",
        "production": _clean_number(pyo.value(model.x)),
        "profit": _clean_number(pyo.value(model.objective)),
        "startup": int(round(pyo.value(model.y))),
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_12(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["lp_rounding_knapsack"]
    lp = pyo.ConcreteModel()
    lp.I = pyo.RangeSet(0, 4)
    lp.x = pyo.Var(lp.I, bounds=(0, 1))
    lp.capacity = pyo.Constraint(
        expr=sum(case["weights"][i] * lp.x[i] for i in lp.I) <= case["capacity"]
    )
    lp.objective = pyo.Objective(
        expr=sum(case["values"][i] * lp.x[i] for i in lp.I),
        sense=pyo.maximize,
    )
    ledger.solve(lp, "15.12.relaksasi_lp")
    lp_vector = [pyo.value(lp.x[i]) for i in lp.I]

    integer = _binary_knapsack_model(
        case["weights"], case["values"], case["capacity"]
    )
    ledger.solve(integer, "15.12.optimum_bilangan_bulat")
    integer_certificate = _enumerate_knapsack(
        case["weights"], case["values"], case["capacity"]
    )
    integer_vector = integer_certificate["optimal_vectors"][0]

    round_up = [math.ceil(value - TOL) for value in lp_vector]
    round_down = [math.floor(value + TOL) for value in lp_vector]

    def summary(vector: list[int]) -> dict[str, Any]:
        weight = sum(a * x for a, x in zip(case["weights"], vector))
        objective = sum(c * x for c, x in zip(case["values"], vector))
        return {
            "feasible": weight <= case["capacity"],
            "objective": objective,
            "weight": weight,
        }

    payload = {
        "integer_optimum": {
            "objective": integer_certificate["objective"],
            "vector": integer_vector,
            "weight": integer_certificate["weights"][0],
        },
        "lp_relaxation": {
            "objective": _fraction(pyo.value(lp.objective)),
            "vector": [_fraction(value) for value in lp_vector],
            "weight": _clean_number(
                sum(a * x for a, x in zip(case["weights"], lp_vector))
            ),
        },
        "round_down": summary(round_down),
        "round_up": summary(round_up),
    }
    return _attach_checks(payload, ledger, start)


def _auxiliary_big_m_model(
    active_coefficients: list[int],
    active_rhs: int,
    relaxed_coefficients: list[int],
    relaxed_rhs: int,
) -> pyo.ConcreteModel:
    model = pyo.ConcreteModel()
    model.x = pyo.Var(range(2), domain=pyo.NonNegativeReals)
    model.active_constraint = pyo.Constraint(
        expr=sum(active_coefficients[i] * model.x[i] for i in range(2))
        <= active_rhs
    )
    model.objective = pyo.Objective(
        expr=sum(relaxed_coefficients[i] * model.x[i] for i in range(2))
        - relaxed_rhs,
        sense=pyo.maximize,
    )
    return model


def _exercise_15_13(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["either_or"]
    model_20 = _either_or_model(case, 20, 20)
    ledger.solve(model_20, "15.13.perbandingan_M_20")
    model_large = _either_or_model(case, 1_000_000, 1_000_000)
    ledger.solve(model_large, "15.13.perbandingan_M_1000000")

    mode_a, mode_b = case["constraints"]
    auxiliary_m1 = _auxiliary_big_m_model(
        mode_b["coefficients"],
        mode_b["rhs"],
        mode_a["coefficients"],
        mode_a["rhs"],
    )
    ledger.solve(auxiliary_m1, "15.13.turunan_M1")
    auxiliary_m2 = _auxiliary_big_m_model(
        mode_a["coefficients"],
        mode_a["rhs"],
        mode_b["coefficients"],
        mode_b["rhs"],
    )
    ledger.solve(auxiliary_m2, "15.13.turunan_M2")
    payload = {
        "large_M_delta_example": {
            "M": 1_000_000,
            "delta": "1/100000",
            "relaxation_added_to_A": 10,
        },
        "minimum_M1": _clean_number(pyo.value(auxiliary_m1.objective)),
        "minimum_M2": _clean_number(pyo.value(auxiliary_m2.objective)),
        "objective_with_M_1000000": _clean_number(
            pyo.value(model_large.objective)
        ),
        "objective_with_M_20": _clean_number(pyo.value(model_20.objective)),
        "numerical_hazard": (
            "koefisien berskala sangat berbeda memperburuk pengondisian dan "
            "mengubah toleransi keutuhan menjadi kelonggaran logis"
        ),
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_14(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    payload = {
        "altruistic_extension": (
            "tambahkan himpunan rantai H, variabel biner x_h, kendala "
            "pengepakan bersama siklus, kendala paling banyak satu rantai per "
            "donor altruistik, dan batas panjang L"
        ),
        "cycle_limit_reason": (
            "operasi serentak memerlukan 2k ruang operasi dan tim; jumlah "
            "calon siklus tumbuh kombinatorial"
        ),
        "objective_reason": (
            "siklus terpilih c melakukan tepat |c| transplantasi tanpa hitung ganda"
        ),
        "packing_meaning": (
            "setiap pasangan pasien-donor boleh berada dalam paling banyak "
            "satu siklus terpilih"
        ),
    }
    return _attach_checks(payload, ledger, start)


def _exercise_15_15(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["piecewise_cost"]
    breakpoints = case["breakpoints"]
    costs = case["costs"]
    model = pyo.ConcreteModel()
    model.K = pyo.RangeSet(0, 3)
    model.S = pyo.RangeSet(0, 2)
    model.lam = pyo.Var(model.K, domain=pyo.NonNegativeReals)
    model.z = pyo.Var(model.S, domain=pyo.Binary)
    model.convexity = pyo.Constraint(
        expr=sum(model.lam[k] for k in model.K) == 1
    )
    model.one_segment = pyo.Constraint(expr=sum(model.z[s] for s in model.S) == 1)
    model.adjacency_0 = pyo.Constraint(expr=model.lam[0] <= model.z[0])
    model.adjacency_1 = pyo.Constraint(
        expr=model.lam[1] <= model.z[0] + model.z[1]
    )
    model.adjacency_2 = pyo.Constraint(
        expr=model.lam[2] <= model.z[1] + model.z[2]
    )
    model.adjacency_3 = pyo.Constraint(expr=model.lam[3] <= model.z[2])
    model.production = pyo.Expression(
        expr=sum(breakpoints[k] * model.lam[k] for k in model.K)
    )
    model.cost = pyo.Expression(
        expr=sum(costs[k] * model.lam[k] for k in model.K)
    )
    model.objective = pyo.Objective(
        expr=case["revenue_per_ton"] * model.production - model.cost,
        sense=pyo.maximize,
    )
    ledger.solve(model, "15.15.biaya_linier_sepenggal")
    production = _clean_number(pyo.value(model.production))
    if production != 20:
        raise RuntimeError("15.15: produksi optimum tidak cocok dengan sertifikat")
    payload = {
        "breakpoint_costs": {
            str(point): cost for point, cost in zip(breakpoints, costs)
        },
        "cost": _clean_number(pyo.value(model.cost)),
        "lambda": [0, 0, 1, 0],
        "nonconvex_certificate": "C(10)=50 > (C(0)+C(20))/2=40",
        "production": production,
        "profit": _clean_number(pyo.value(model.objective)),
        "segment_selector": [0, 1, 0],
    }
    return _attach_checks(payload, ledger, start)


def _flowshop_model(case: dict[str, Any]) -> pyo.ConcreteModel:
    processing = case["processing_times"]
    big_m = case["big_m"]
    model = pyo.ConcreteModel()
    model.J = pyo.RangeSet(0, 1)
    model.K = pyo.RangeSet(0, 2)
    model.s = pyo.Var(model.J, model.K, domain=pyo.NonNegativeReals)
    model.delta = pyo.Var(model.K, domain=pyo.Binary)
    model.cmax = pyo.Var(domain=pyo.NonNegativeReals)
    model.precedence = pyo.Constraint(
        model.J,
        pyo.RangeSet(0, 1),
        rule=lambda m, j, k: m.s[j, k + 1] >= m.s[j, k] + processing[j][k],
    )
    model.machine_first = pyo.Constraint(
        model.K,
        rule=lambda m, k: m.s[1, k]
        >= m.s[0, k] + processing[0][k] - big_m * (1 - m.delta[k]),
    )
    model.machine_second = pyo.Constraint(
        model.K,
        rule=lambda m, k: m.s[0, k]
        >= m.s[1, k] + processing[1][k] - big_m * m.delta[k],
    )
    model.finish = pyo.Constraint(
        model.J,
        rule=lambda m, j: m.cmax >= m.s[j, 2] + processing[j][2],
    )
    model.objective = pyo.Objective(expr=model.cmax, sense=pyo.minimize)
    return model


def _exercise_15_16(data: dict[str, Any], ledger: SolverLedger) -> dict[str, Any]:
    start = len(ledger.records)
    case = data["cases"]["flowshop"]
    model = _flowshop_model(case)
    ledger.solve(model, "15.16.makespan")
    makespan = _clean_number(pyo.value(model.cmax))
    if makespan != 12:
        raise RuntimeError("15.16: makespan optimum bukan 12")

    model.canonical_makespan = pyo.Constraint(expr=model.cmax == makespan)
    model.canonical_order = pyo.ConstraintList()
    for machine in model.K:
        model.canonical_order.add(model.delta[machine] == 1)
    model.objective.deactivate()
    model.earliest = pyo.Objective(
        expr=sum(model.s[j, k] for j in model.J for k in model.K),
        sense=pyo.minimize,
    )
    ledger.solve(model, "15.16.jadwal_kanonik")
    processing = case["processing_times"]
    schedule: dict[str, list[list[int | float]]] = {}
    for j, job in enumerate(case["jobs"]):
        schedule[job] = []
        for k in range(3):
            begin = _clean_number(pyo.value(model.s[j, k]))
            finish = _clean_number(float(begin) + processing[j][k])
            schedule[job].append([begin, finish])
    machine_order = {
        machine: case["jobs"][:] for machine in case["machines"]
    }
    payload = {
        "big_m": case["big_m"],
        "machine_order": machine_order,
        "makespan": makespan,
        "schedule": schedule,
    }
    return _attach_checks(payload, ledger, start)


EVALUATORS = {
    "15.1": _exercise_15_1,
    "15.2": _exercise_15_2,
    "15.3": _exercise_15_3,
    "15.4": _exercise_15_4,
    "15.5": _exercise_15_5,
    "15.6": _exercise_15_6,
    "15.7": _exercise_15_7,
    "15.8": _exercise_15_8,
    "15.9": _exercise_15_9,
    "15.10": _exercise_15_10,
    "15.11": _exercise_15_11,
    "15.12": _exercise_15_12,
    "15.13": _exercise_15_13,
    "15.14": _exercise_15_14,
    "15.15": _exercise_15_15,
    "15.16": _exercise_15_16,
}


def evaluate_all(data: dict[str, Any]) -> dict[str, Any]:
    ledger = SolverLedger()
    exercises: dict[str, Any] = {}
    for exercise_id in data["exercise_order"]:
        result = _metadata(data, exercise_id)
        result["answer"] = EVALUATORS[exercise_id](data, ledger)
        exercises[exercise_id] = result

    termination_counts = Counter(
        record["termination_condition"] for record in ledger.records
    )
    maximum_violation = max(
        (record["maximum_violation"] for record in ledger.records), default=0
    )
    manual_status_counts = Counter(
        data["exercises"][exercise_id]["manual_mapping"]["status"]
        for exercise_id in data["exercise_order"]
    )
    return {
        "authority_commit": data["authority_commit"],
        "exercises": exercises,
        "lab_id": data["lab_id"],
        "manual_alignment": {
            "book_primary_ids": data["exercise_order"],
            "manual_status_counts": dict(sorted(manual_status_counts.items())),
        },
        "provenance": data["provenance"],
        "schema_version": data["schema_version"],
        "solver_ledger": ledger.records,
        "source_defects": data["source_defects"],
        "summary": {
            "exercise_count": len(exercises),
            "manual_alignment_count": len(data["exercise_order"]),
            "maximum_solver_violation": maximum_violation,
            "o018_math_correction_count": 0,
            "solver_call_count": len(ledger.records),
            "solver_termination_counts": dict(sorted(termination_counts.items())),
            "source_defect_count": len(data["source_defects"]),
            "unresolved_count": len(data["unresolved_exercises"]),
            "verified_count": len(exercises),
        },
        "unresolved_exercises": data["unresolved_exercises"],
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
