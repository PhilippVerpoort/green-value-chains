import pandas as pd

from src.data.calc.calc_cost import calcCost
from src.data.params.full_params import getFullTechData
from src.load.load_default_data import process_routes


# obtain all required data for a scenario
def getFullData(prices: pd.DataFrame, options: dict):
    process_group = options['process_group']


    # convert basic inputs to complete dataframes
    techDataFull = getFullTechData(options['times'], process_group)


    # determine routes based on options
    routes = ['EL_H2DR_EAF', 'NGDR_EAF'] if options['include_electrolysis'] else ['H2DR_EAF', 'NGDR_EAF']
    routes_details = {r: process_routes[process_group][r] for r in routes}


    # calculate cost from tech data
    costData = calcCost(techDataFull, prices, routes_details)


    return {
        'techDataFull': techDataFull,
        'costData': costData,
    }
