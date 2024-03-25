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

    scenarios = args[3]
    inputs_updated['scenarios'] = pd.DataFrame.from_dict(scenarios) \
        .set_index(['scenario', 'commodity']) \
        .astype('float32') \
        .apply(lambda x: x/100.0)

    volumes = args[4]
    inputs_updated['volumes'] = pd.DataFrame.from_dict(volumes) \
        .set_index(['commodity'])['volume'] \
        .astype('float32')
