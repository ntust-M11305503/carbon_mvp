import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.operators.sampling.rnd import BinaryRandomSampling
from pymoo.operators.crossover.pntx import TwoPointCrossover
from pymoo.operators.mutation.bitflip import BitflipMutation
from pymoo.optimize import minimize
from pymoo.core.problem import Problem
import numpy as np

class ProcProblem(Problem):
    def __init__(self, df: pd.DataFrame):
        self.df = df
        n_var = len(df)
        super().__init__(n_var=n_var,
                         n_obj=3,
                         n_constr=0,
                         xl=np.zeros(n_var),
                         xu=np.ones(n_var))
    def _evaluate(self, X, out, *args, **kwargs):
        # X shape (pop, n_var) binary selection mask
        cost = X @ self.df['unit_price'].values
        carbon = X @ (self.df['gwp'].values * self.df['qty'].values)
        eta = X @ self.df['eta'].values  # where eta present else 0
        out["F"] = np.column_stack([cost, carbon, eta])

def optimize_materials(df: pd.DataFrame, pop_size=50, n_gen=100):
    df = df.copy()
    if 'eta' not in df.columns:
        df['eta'] = 0
    problem = ProcProblem(df)
    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=BinaryRandomSampling(),
        crossover=TwoPointCrossover(),
        mutation=BitflipMutation()
    )
    res = minimize(problem,
                   algorithm,
                   ('n_gen', n_gen),
                   verbose=False)
    # pick first 3 non-dominated sols
    sols = []
    for i, x in enumerate(res.X[:3]):
        mask = x.astype(bool)
        sel = df[mask]

        if "item" in sel.columns:
            items_col = sel["item"]
            # 若出現多欄位 item，僅取第一欄
            if hasattr(items_col, "columns"):
                items_col = items_col.iloc[:, 0]
            items = [str(item) for item in items_col.tolist()]
        else:
            items = []


        total_cost = float(sel["unit_price"].sum()) if "unit_price" in sel.columns else 0.0
        if "gwp" in sel.columns and "qty" in sel.columns:
            total_carbon = float((sel["gwp"].fillna(0) * sel["qty"].fillna(0)).sum())
        else:
            total_carbon = 0.0
        total_eta = float(sel["eta"].sum()) if "eta" in sel.columns else 0.0

        sols.append({
            "id": int(i),
            "items": items,
            "total_cost": total_cost,
            "total_carbon": total_carbon,
            "total_eta": total_eta
        })

    return {"solutions": list(sols)}

