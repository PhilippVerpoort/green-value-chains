import numpy as np
import pandas as pd


# update callback function
def update_inputs(inputs_updated: dict, btn_pressed: str, args: list):
    # get dataframe of updated values from table
    elec_prices = args[1]
    inputs_updated['epdcases'] = pd.DataFrame.from_dict(elec_prices) \
        .drop(columns=['epdcaseDisplay', 'processDisplay']) \
        .astype({c: 'pint[EUR/MWh]' for c in ('RE-scarce', 'RE-rich')})

    transp_cost = args[2]
    inputs_updated['transp_cost'] = pd.DataFrame.from_dict(transp_cost) \
        .drop(columns=['tradedDisplay']) \
        .astype({'assump': 'float'}) \
        .fillna(np.nan)
