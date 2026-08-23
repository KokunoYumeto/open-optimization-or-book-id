"""Model Pyomo terbuka untuk keluarga operasional Bab 4.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path
from typing import Any, Sequence

from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    NonNegativeIntegers,
    NonNegativeReals,
    Objective,
    RangeSet,
    Reals,
    Set,
    SolverFactory,
    UnitInterval,
    Var,
    maximize,
    minimize,
    value,
)
from pyomo.opt import SolverStatus, TerminationCondition


TOLERANCE = 1e-7
LAB_ID = "o018.ch04.compact-modeling-replacements"
CASE_IDS = (
    "absolute_deviation",
    "airline_max_flow",
    "assignment_generic",
    "assignment_machine",
    "assignment_school_bus",
    "investment_multi_period",
    "min_cost_flow_unstructured",
    "min_cost_flow_warehouses",
    "multicommodity_fractional",
    "multicommodity_integer",
    "production_10period",
    "production_overtime",
)


class IncompleteModelError(ValueError):
    """Data atau semantik model belum cukup untuk eksekusi yang jujur."""


def load_data(path: Path) -> dict[str, Any]:
    """Membaca data dan menolak perubahan cakupan, domain, atau status kasus."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("lab_id") != LAB_ID:
        raise ValueError("lab_id tidak sesuai kontrak")
    cases = data.get("cases")
    if not isinstance(cases, dict) or tuple(sorted(cases)) != CASE_IDS:
        raise ValueError("data harus memuat tepat 12 kasus Bab 4 yang dibekukan")
    executable = {
        case_id
        for case_id, spec in cases.items()
        if spec.get("status") == "executable"
    }
    if executable != set(CASE_IDS) - {
        "production_overtime",
        "investment_multi_period",
    }:
        raise ValueError("status kasus executable berubah")
    if cases["production_overtime"].get("status") != "parameter_required":
        raise ValueError("kasus lembur harus tetap parameter_required")
    if cases["investment_multi_period"].get("status") != "design_unresolved":
        raise ValueError("kasus investasi harus tetap design_unresolved")
    if cases["multicommodity_integer"].get("domain") != "NonNegativeIntegers":
        raise ValueError("aliran multikomoditas pertama harus tetap bilangan bulat")
    if cases["multicommodity_fractional"].get("domain") != "UnitInterval":
        raise ValueError("aliran sumber-tujuan harus tetap pecahan dalam [0,1]")
    return data


def _clean(number: float) -> float:
    number = float(number)
    if abs(number) <= 1e-10:
        return 0.0
    return round(number, 10)


def _arc(label: str) -> tuple[str, str]:
    origin, separator, destination = label.partition("->")
    if separator != "->" or not origin or not destination:
        raise ValueError(f"label busur tidak sah: {label}")
    return origin, destination


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


def build_production_10period(spec: dict[str, Any]) -> ConcreteModel:
    period_count = len(spec["demand"])
    model = ConcreteModel(name="ch04_production_10period")
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


def solve_production_10period(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_production_10period(spec)
    execution = _solve(model)
    return {
        "ending_inventory": [_clean(value(model.inventory[t])) for t in model.T],
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "production": [_clean(value(model.production[t])) for t in model.T],
    }


def build_production_overtime(
    spec: dict[str, Any],
    *,
    regular_capacity: Sequence[float] | None = None,
    overtime_capacity: Sequence[float] | None = None,
) -> ConcreteModel:
    """Membangun ekstensi lembur hanya setelah kedua kapasitas diberikan."""
    if regular_capacity is None or overtime_capacity is None:
        raise IncompleteModelError(
            "model lembur memerlukan regular_capacity[1..10] dan "
            "overtime_capacity[1..10]; data sumber tidak memberikannya"
        )
    period_count = len(spec["demand"])
    if len(regular_capacity) != period_count or len(overtime_capacity) != period_count:
        raise IncompleteModelError("panjang kedua vektor kapasitas harus sama dengan T")
    if any(float(capacity) < 0 for capacity in (*regular_capacity, *overtime_capacity)):
        raise IncompleteModelError("kapasitas produksi tidak boleh negatif")

    model = ConcreteModel(name="ch04_production_overtime_parameterized")
    model.T = RangeSet(1, period_count)
    model.regular = Var(
        model.T,
        domain=NonNegativeReals,
        bounds=lambda _, period: (0.0, float(regular_capacity[period - 1])),
    )
    model.overtime = Var(
        model.T,
        domain=NonNegativeReals,
        bounds=lambda _, period: (0.0, float(overtime_capacity[period - 1])),
    )
    model.inventory = Var(model.T, domain=NonNegativeReals)

    def balance_rule(current: ConcreteModel, period: int):
        previous = (
            float(spec["initial_inventory"])
            if period == 1
            else current.inventory[period - 1]
        )
        return (
            previous + current.regular[period] + current.overtime[period]
            == float(spec["demand"][period - 1]) + current.inventory[period]
        )

    model.balance = Constraint(model.T, rule=balance_rule)
    model.objective = Objective(
        expr=sum(
            float(spec["regular_cost"][period - 1]) * model.regular[period]
            + float(spec["overtime_cost"][period - 1]) * model.overtime[period]
            + float(spec["holding_cost"]) * model.inventory[period]
            for period in model.T
        ),
        sense=minimize,
    )
    return model


def build_assignment(spec: dict[str, Any], *, name: str) -> ConcreteModel:
    agent_count = len(spec["agent_ids"])
    task_count = len(spec["task_ids"])
    if agent_count != task_count or len(spec["cost"]) != agent_count:
        raise ValueError("matriks penugasan harus persegi")
    if any(len(row) != task_count for row in spec["cost"]):
        raise ValueError("baris matriks biaya penugasan tidak lengkap")
    model = ConcreteModel(name=name)
    model.I = RangeSet(0, agent_count - 1)
    model.J = RangeSet(0, task_count - 1)
    model.assignment = Var(model.I, model.J, domain=Binary)
    model.agent = Constraint(
        model.I,
        rule=lambda current, agent: sum(
            current.assignment[agent, task] for task in current.J
        )
        == 1,
    )
    model.task = Constraint(
        model.J,
        rule=lambda current, task: sum(
            current.assignment[agent, task] for agent in current.I
        )
        == 1,
    )
    model.objective = Objective(
        expr=sum(
            float(spec["cost"][agent][task]) * model.assignment[agent, task]
            for agent in model.I
            for task in model.J
        ),
        sense=minimize,
    )
    return model


def solve_assignment(spec: dict[str, Any], *, name: str) -> dict[str, Any]:
    model = build_assignment(spec, name=name)
    execution = _solve(model)
    assignments = {
        spec["agent_ids"][agent]: spec["task_ids"][task]
        for agent in model.I
        for task in model.J
        if value(model.assignment[agent, task]) > 0.5
    }
    return {
        "assignment": assignments,
        "execution": execution,
        "objective": _clean(value(model.objective)),
    }


def build_absolute_deviation(spec: dict[str, Any]) -> ConcreteModel:
    points = tuple(float(point) for point in spec["points"])
    model = ConcreteModel(name="ch04_absolute_deviation")
    model.I = RangeSet(0, len(points) - 1)
    model.x = Var(domain=Reals)
    model.deviation = Var(model.I, domain=NonNegativeReals)
    model.upper = Constraint(
        model.I,
        rule=lambda current, index: current.x - points[index]
        <= current.deviation[index],
    )
    model.lower = Constraint(
        model.I,
        rule=lambda current, index: points[index] - current.x
        <= current.deviation[index],
    )
    model.objective = Objective(
        expr=sum(model.deviation[index] for index in model.I),
        sense=minimize,
    )
    return model


def solve_absolute_deviation(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_absolute_deviation(spec)
    execution = _solve(model)
    return {
        "deviation": [_clean(value(model.deviation[i])) for i in model.I],
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "x": _clean(value(model.x)),
    }


def build_min_cost_flow_warehouses(spec: dict[str, Any]) -> ConcreteModel:
    warehouses = tuple(spec["supply_capacity"])
    stores = tuple(spec["demand"])
    model = ConcreteModel(name="ch04_min_cost_flow_warehouses")
    model.W = Set(initialize=warehouses, ordered=True)
    model.S = Set(initialize=stores, ordered=True)
    model.flow = Var(
        model.W,
        model.S,
        domain=NonNegativeReals,
        bounds=lambda _, warehouse, store: (
            0.0,
            float(spec["arc_capacity"][f"{warehouse}->{store}"]),
        ),
    )
    model.supply = Constraint(
        model.W,
        rule=lambda current, warehouse: sum(
            current.flow[warehouse, store] for store in current.S
        )
        <= float(spec["supply_capacity"][warehouse]),
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
            float(spec["arc_cost"][f"{warehouse}->{store}"])
            * model.flow[warehouse, store]
            for warehouse in model.W
            for store in model.S
        ),
        sense=minimize,
    )
    return model


def solve_min_cost_flow_warehouses(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_min_cost_flow_warehouses(spec)
    execution = _solve(model)
    return {
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "route_flow": {
            f"{warehouse}->{store}": _clean(value(model.flow[warehouse, store]))
            for warehouse in model.W
            for store in model.S
        },
    }


def build_min_cost_flow_unstructured(spec: dict[str, Any]) -> ConcreteModel:
    if spec.get("finite_arc_capacities") is not None:
        raise ValueError("kontrak kasus ini membekukan ketiadaan kapasitas busur hingga")
    arcs = tuple(_arc(label) for label in spec["arc_cost"])
    nodes = tuple(spec["net_demand"])
    model = ConcreteModel(name="ch04_min_cost_flow_unstructured")
    model.V = Set(initialize=nodes, ordered=True)
    model.A = Set(initialize=arcs, dimen=2, ordered=True)
    model.flow = Var(model.A, domain=NonNegativeReals)
    model.balance = Constraint(
        model.V,
        rule=lambda current, node: sum(
            current.flow[origin, destination]
            for origin, destination in current.A
            if destination == node
        )
        - sum(
            current.flow[origin, destination]
            for origin, destination in current.A
            if origin == node
        )
        == float(spec["net_demand"][node]),
    )
    model.objective = Objective(
        expr=sum(
            float(spec["arc_cost"][f"{origin}->{destination}"])
            * model.flow[origin, destination]
            for origin, destination in model.A
        ),
        sense=minimize,
    )
    return model


def solve_min_cost_flow_unstructured(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_min_cost_flow_unstructured(spec)
    execution = _solve(model)
    return {
        "balance_convention": spec["balance_convention"],
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "route_flow": {
            f"{origin}->{destination}": _clean(value(model.flow[origin, destination]))
            for origin, destination in model.A
        },
    }


def build_airline_max_flow(spec: dict[str, Any]) -> ConcreteModel:
    arcs = tuple(_arc(label) for label in spec["arc_capacity"])
    nodes = tuple(dict.fromkeys(node for arc in arcs for node in arc))
    source = spec["source"]
    sink = spec["sink"]
    model = ConcreteModel(name="ch04_airline_max_flow_corrected")
    model.V = Set(initialize=nodes, ordered=True)
    model.A = Set(initialize=arcs, dimen=2, ordered=True)
    model.flow = Var(
        model.A,
        domain=NonNegativeReals,
        bounds=lambda _, origin, destination: (
            0.0,
            float(spec["arc_capacity"][f"{origin}->{destination}"]),
        ),
    )
    model.balance = Constraint(
        tuple(node for node in nodes if node not in {source, sink}),
        rule=lambda current, node: sum(
            current.flow[origin, destination]
            for origin, destination in current.A
            if origin == node
        )
        - sum(
            current.flow[origin, destination]
            for origin, destination in current.A
            if destination == node
        )
        == 0,
    )
    model.objective = Objective(
        expr=sum(
            model.flow[origin, destination]
            for origin, destination in model.A
            if origin == source
        ),
        sense=maximize,
    )
    return model


def solve_airline_max_flow(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_airline_max_flow(spec)
    execution = _solve(model)
    source = spec["source"]
    sink = spec["sink"]
    route_flow = {
        f"{origin}->{destination}": _clean(value(model.flow[origin, destination]))
        for origin, destination in model.A
    }
    cut_capacity = sum(
        float(spec["arc_capacity"][arc_label]) for arc_label in spec["certifying_cut"]
    )
    return {
        "certifying_cut_capacity": _clean(cut_capacity),
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "route_flow": route_flow,
        "sink_inflow": _clean(
            sum(
                value(model.flow[origin, destination])
                for origin, destination in model.A
                if destination == sink
            )
        ),
        "source_outflow": _clean(
            sum(
                value(model.flow[origin, destination])
                for origin, destination in model.A
                if origin == source
            )
        ),
    }


def build_multicommodity_integer(spec: dict[str, Any]) -> ConcreteModel:
    arcs = tuple(_arc(label) for label in spec["arc_capacity"])
    nodes = tuple(spec["net_demand"])
    commodities = tuple(spec["commodities"])
    model = ConcreteModel(name="ch04_multicommodity_integer_corrected")
    model.V = Set(initialize=nodes, ordered=True)
    model.A = Set(initialize=arcs, dimen=2, ordered=True)
    model.K = Set(initialize=commodities, ordered=True)
    model.flow = Var(model.A, model.K, domain=NonNegativeIntegers)
    model.capacity = Constraint(
        model.A,
        rule=lambda current, origin, destination: sum(
            current.flow[origin, destination, commodity]
            for commodity in current.K
        )
        <= float(spec["arc_capacity"][f"{origin}->{destination}"]),
    )
    model.balance = Constraint(
        model.V,
        model.K,
        rule=lambda current, node, commodity: sum(
            current.flow[origin, destination, commodity]
            for origin, destination in current.A
            if destination == node
        )
        - sum(
            current.flow[origin, destination, commodity]
            for origin, destination in current.A
            if origin == node
        )
        == float(spec["net_demand"][node][commodity]),
    )
    model.objective = Objective(
        expr=sum(
            float(spec["unit_cost"][f"{origin}->{destination}"][commodity])
            * model.flow[origin, destination, commodity]
            for origin, destination in model.A
            for commodity in model.K
        ),
        sense=minimize,
    )
    return model


def solve_multicommodity_integer(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_multicommodity_integer(spec)
    execution = _solve(model)
    return {
        "balance_convention": spec["balance_convention"],
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "route_flow": {
            f"{origin}->{destination}": {
                commodity: _clean(value(model.flow[origin, destination, commodity]))
                for commodity in model.K
            }
            for origin, destination in model.A
        },
    }


def build_multicommodity_fractional(spec: dict[str, Any]) -> ConcreteModel:
    arcs = tuple(_arc(label) for label in spec["arc_capacity"])
    nodes = tuple(dict.fromkeys(node for arc in arcs for node in arc))
    commodities = tuple(spec["commodities"])
    model = ConcreteModel(name="ch04_multicommodity_fractional")
    model.V = Set(initialize=nodes, ordered=True)
    model.A = Set(initialize=arcs, dimen=2, ordered=True)
    model.K = Set(initialize=commodities, ordered=True)
    model.fraction = Var(model.K, model.A, domain=UnitInterval)
    model.capacity = Constraint(
        model.A,
        rule=lambda current, origin, destination: sum(
            float(spec["commodities"][commodity]["demand"])
            * current.fraction[commodity, origin, destination]
            for commodity in current.K
        )
        <= float(spec["arc_capacity"][f"{origin}->{destination}"]),
    )

    def balance_rule(
        current: ConcreteModel,
        commodity: str,
        node: str,
    ):
        commodity_spec = spec["commodities"][commodity]
        rhs = (
            1.0
            if node == commodity_spec["source"]
            else -1.0
            if node == commodity_spec["sink"]
            else 0.0
        )
        return (
            sum(
                current.fraction[commodity, origin, destination]
                for origin, destination in current.A
                if origin == node
            )
            - sum(
                current.fraction[commodity, origin, destination]
                for origin, destination in current.A
                if destination == node
            )
            == rhs
        )

    model.balance = Constraint(model.K, model.V, rule=balance_rule)
    model.objective = Objective(
        expr=sum(
            float(spec["arc_cost"][f"{origin}->{destination}"])
            * float(spec["commodities"][commodity]["demand"])
            * model.fraction[commodity, origin, destination]
            for commodity in model.K
            for origin, destination in model.A
        ),
        sense=minimize,
    )
    return model


def solve_multicommodity_fractional(spec: dict[str, Any]) -> dict[str, Any]:
    model = build_multicommodity_fractional(spec)
    execution = _solve(model)
    aggregate_flow = {
        f"{origin}->{destination}": _clean(
            sum(
                float(spec["commodities"][commodity]["demand"])
                * value(model.fraction[commodity, origin, destination])
                for commodity in model.K
            )
        )
        for origin, destination in model.A
    }
    return {
        "aggregate_route_flow": aggregate_flow,
        "balance_convention": spec["balance_convention"],
        "execution": execution,
        "objective": _clean(value(model.objective)),
        "per_commodity_routes_omitted_due_to_degeneracy": True,
    }


def build_multi_period_investment(spec: dict[str, Any]) -> ConcreteModel:
    questions = "; ".join(spec["design_questions"])
    raise IncompleteModelError(
        "model investasi belum mempunyai semantik yang cukup untuk dieksekusi: "
        f"{questions}"
    )


def _not_run(spec: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "execution": {
            "reason": spec["status"],
            "status": "not_run",
        }
    }
    if "required_parameters" in spec:
        result["required_parameters"] = spec["required_parameters"]
    if "design_questions" in spec:
        result["design_questions"] = spec["design_questions"]
    return result


def solve_all(data: dict[str, Any]) -> dict[str, Any]:
    cases = data["cases"]
    return {
        "cases": {
            "absolute_deviation": solve_absolute_deviation(
                cases["absolute_deviation"]
            ),
            "airline_max_flow": solve_airline_max_flow(cases["airline_max_flow"]),
            "assignment_generic": solve_assignment(
                cases["assignment_generic"], name="ch04_assignment_generic"
            ),
            "assignment_machine": solve_assignment(
                cases["assignment_machine"], name="ch04_assignment_machine"
            ),
            "assignment_school_bus": solve_assignment(
                cases["assignment_school_bus"], name="ch04_assignment_school_bus"
            ),
            "investment_multi_period": _not_run(cases["investment_multi_period"]),
            "min_cost_flow_unstructured": solve_min_cost_flow_unstructured(
                cases["min_cost_flow_unstructured"]
            ),
            "min_cost_flow_warehouses": solve_min_cost_flow_warehouses(
                cases["min_cost_flow_warehouses"]
            ),
            "multicommodity_fractional": solve_multicommodity_fractional(
                cases["multicommodity_fractional"]
            ),
            "multicommodity_integer": solve_multicommodity_integer(
                cases["multicommodity_integer"]
            ),
            "production_10period": solve_production_10period(
                cases["production_10period"]
            ),
            "production_overtime": _not_run(cases["production_overtime"]),
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
