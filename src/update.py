import numpy as np
import pandas as pd


# update callback function
def updateScenarioInput(inputs_updated: dict, btn_pressed: str, args: list):
    # get dataframe of updated values from table
    elec_prices = args[1]
    elec_prices_df = pd.DataFrame.from_dict(elec_prices) \
        .drop(columns=['epdcaseDisplay', 'processDisplay']) \
        .astype({c: 'pint[EUR/MWh]' for c in ('RE-scarce', 'RE-rich')}) \
        .set_index(['epdcase', 'process'])

    transp_cost = args[2]
    transp_cost_df = pd.DataFrame.from_dict(transp_cost) \
        .drop(columns='tradedDisplay') \
        .astype({'assump': 'float'}) \
        .fillna(np.nan)

    # update inputs based on table data
    tmp = inputs_updated['epdcases'].set_index(['epdcase', 'process'])
    tmp.update(elec_prices_df)
    inputs_updated['epdcases'] = tmp.reset_index()

    print(inputs_updated['transp_cost'])
    print(transp_cost_df)
    inputs_updated['transp_cost'] = transp_cost_df
