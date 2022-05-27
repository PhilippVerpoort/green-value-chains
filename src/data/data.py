import pandas as pd

from src.data.calc.calc_cost import calcCost
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
