import pandas as pd

from src.data.calc.calc_cost import calcCost
from src.data.calc.calc_cost_bf import calcCostComponentsBF
from src.data.calc.calc_cost_h2 import calcCostComponentsH2
from src.data.calc.calc_cost_ng import calcCostComponentsNG
from src.data.params.full_params import getFullTechData
from src.load.load_default_data import options, process_routes


# obtain all required data for a scenario
def getFullData(assumptions: pd.DataFrame):
    process_group = 'Steel'
    routes = ['EL_H2DR_EAF', 'H2DR_EAF', 'NGDR_EAF']


    # convert basic inputs to complete dataframes
    techDataFull = getFullTechData(options['times'], process_group)


    # calculate cost from tech data
    costData = calcCost(techDataFull, assumptions, {r: process_routes[process_group][r] for r in routes})


    return {
        'techDataFull': techDataFull,
        'costData': costData,
    }

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


def __applyCarbonPrice(costData: pd.DataFrame, carbon_price: pd.DataFrame):
    carbonCost = costData.query("type=='carbon'").merge(carbon_price).assign(val=lambda x: x.val * x.cp, unit='EUR/t').drop(columns='cp')

    return pd.concat([costData.query("type!='carbon'"), carbonCost]).reset_index(drop=True)
