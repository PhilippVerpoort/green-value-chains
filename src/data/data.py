import pandas as pd

from src.data.calc.calc_cost import calcCost
from src.data.params.full_params import getFullTechData
from src.load.load_default_data import process_routes


# obtain all required data for a scenario
def getFullData(prices: pd.DataFrame, options: dict):
    # convert basic inputs to complete dataframes
    techDataFull = getFullTechData(options['times'])


    # determine routes based on options
    costDataList = []
    for process_group in ['Steel', 'Fertiliser']:
        if process_group == 'Steel':
            routes = ['BF_BOF', 'ELEC_H2DR_EAF', 'NGDR_EAF'] if options['include_electrolysis'] else ['BF_BOF', 'H2DR_EAF', 'NGDR_EAF']
        elif process_group == 'Fertiliser':
            routes = ['SMR_HB_UREA', 'ELEC_HB_DAC_UREA']

        routes_details = {r: process_routes[process_group][r] for r in routes}

        # calculate cost from tech data
        techData = techDataFull.query(f"process_group.str.contains('{process_group}')")
        costDataList.append(calcCost(techData, prices, routes_details))


    return {
        'techDataFull': techDataFull,
        'costData': pd.concat(costDataList),
    }
