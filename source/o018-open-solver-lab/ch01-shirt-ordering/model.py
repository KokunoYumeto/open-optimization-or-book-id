"""Model Pyomo untuk Latihan ex:shirt-full-lp.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pyomo.environ import (
    ConcreteModel,
    Constraint,
    NonNegativeIntegers,
    NonNegativeReals,
    Objective,
    RangeSet,
    SolverFactory,
    Var,
    minimize,
    value,
)
from pyomo.opt import SolverStatus, TerminationCondition


def load_data(path: Path) -> dict[str, Any]:
    """Membaca data terstruktur dan memeriksa bentuk minimum yang diperlukan."""
    data = json.loads(path.read_text(encoding="utf-8"))
    periods = data.get("periods")
    if not isinstance(periods, list) or not periods:
        raise ValueError("data harus memuat daftar periods yang tidak kosong")
    required = {
        "id",
        "display_id",
        "order_day_id",
        "order_day_display_id",
        "demand",
        "order_cost",
        "holding_cost",
    }
    for index, period in enumerate(periods):
        if not isinstance(period, dict) or not required.issubset(period):
            raise ValueError(f"periods[{index}] tidak lengkap")
    if float(data.get("initial_inventory", 0.0)) != 0.0:
        raise ValueError("laboratorium pertama membekukan persediaan awal pada nol")
    return data


def build_model(data: dict[str, Any], *, integer: bool = False) -> ConcreteModel:
    """Membangun LP atau padanan bilangan bulat tanpa mengubah persamaannya."""
    periods = data["periods"]
    model = ConcreteModel(name=str(data["lab_id"]))
    model.P = RangeSet(0, len(periods) - 1)
    domain = NonNegativeIntegers if integer else NonNegativeReals
    model.order = Var(model.P, domain=domain)
    model.inventory = Var(model.P, domain=domain)

    def balance_rule(current: ConcreteModel, period_index: int):
        previous = (
            float(data["initial_inventory"])
            if period_index == 0
            else current.inventory[period_index - 1]
        )
        return (
            previous + current.order[period_index]
            == float(periods[period_index]["demand"])
            + current.inventory[period_index]
        )

    model.balance = Constraint(model.P, rule=balance_rule)
    model.total_cost = Objective(
        expr=sum(
            float(periods[index]["order_cost"]) * model.order[index]
            + float(periods[index]["holding_cost"]) * model.inventory[index]
            for index in model.P
        ),
        sense=minimize,
    )
    return model


def solve_model(data: dict[str, Any], *, integer: bool = False) -> dict[str, Any]:
    """Menyelesaikan model dengan antarmuka Appsi–HiGHS dan mengembalikan JSON."""
    model = build_model(data, integer=integer)
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

    period_ids = [str(period["id"]) for period in data["periods"]]
    order_day_ids = [str(period["order_day_id"]) for period in data["periods"]]
    return {
        "mode": "integer" if integer else "lp",
        "objective": float(value(model.total_cost)),
        "orders": {
            order_day_id: float(value(model.order[index]))
            for index, order_day_id in enumerate(order_day_ids)
        },
        "inventory": {
            period_id: float(value(model.inventory[index]))
            for index, period_id in enumerate(period_ids)
        },
        "solver": "appsi_highs",
        "termination_condition": str(result.solver.termination_condition),
    }
