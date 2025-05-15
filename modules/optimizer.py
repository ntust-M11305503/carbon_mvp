
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.factory import get_sampling, get_crossover, get_mutation
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
    algorithm = NSGA2(pop_size=pop_size,
                      sampling=get_sampling("bin_random"),
                      crossover=get_crossover("bin_two_point"),
                      mutation=get_mutation("bin_bitflip"))
    res = minimize(problem,
                   algorithm,
                   ('n_gen', n_gen),
                   verbose=False)
    # pick first 3 non-dominated sols
    sols = []
    for i, x in enumerate(res.X[:3]):
        mask = x.astype(bool)
        sel = df[mask]
        sols.append({
            "id": i,
            "items": sel['item'].tolist(),
            "total_cost": sel['unit_price'].sum(),
            "total_carbon": (sel['gwp'] * sel['qty']).sum(),
            "total_eta": sel['eta'].sum()
        })
    return {"solutions": sols}
