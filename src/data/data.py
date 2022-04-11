import pandas as pd

from src.data.calc.calc_cost_bf import calcCostComponentsBF
from src.data.calc.calc_cost_h2 import calcCostComponentsH2
from src.data.calc.calc_cost_ng import calcCostComponentsNG
from src.data.params.full_params import getFullParamsAll
from src.config_load import units, ref_data, cp_data


# obtain all required data for a scenario
def getFullData(input_data: dict, assumptions: dict):
    options, cost_data = (input_data['options'], input_data['cost_data'])

    # convert basic inputs to complete dataframes
    fullParams = getFullParamsAll(cost_data, units, options['times'])

    # calculate cost
    costDataBF = calcCostComponentsBF(ref_data, options['times'])
    costDataNG = calcCostComponentsNG(fullParams, assumptions['share_secondary'], assumptions['elec_price_importer'], assumptions['ng_price'], options['times'])
    costDataH2 = calcCostComponentsH2(fullParams, assumptions['share_secondary'], assumptions['elec_price_importer'], assumptions['elec_price_exporter'], options['times'])

    costData = pd.concat([costDataBF, costDataNG, costDataH2])
    costData = __applyCarbonPrice(costData, pd.DataFrame.from_records(cp_data))

    #print(costData.query(f"type!='carbon' & year==2025").groupby(['case', 'year']).sum())
    #print(costData.query(f"type=='carbon' & year==2025"))
    #print(costData.query(f"type=='energy' & name=='h2' & case==1 & year==2025"))
    #print(costData.query(f"type=='capital' & name=='electrolyser' & case==1 & year==2025"))

    return fullParams, costData


def __applyCarbonPrice(costData: pd.DataFrame, carbon_price: pd.DataFrame):
    carbonCost = costData.query("type=='carbon'").merge(carbon_price).assign(val=lambda x: x.val * x.cp, unit='EUR/t').drop(columns='cp')

    return pd.concat([costData.query("type!='carbon'"), carbonCost]).reset_index(drop=True)
