import pandas as pd

from src.data.calc.calc_cost import calcCost
from src.data.params.full_params import getFullTechData
from src.load.load_default_data import all_routes


# obtain all required data for a scenario
def getFullData(prices: pd.DataFrame, options: dict):
    # convert basic inputs to complete dataframes
    techDataFull = getFullTechData(options['times'])


    # determine routes based on options
    costDataList = []
    for commodity in all_routes:
        selectedRoutes = {
            r: all_routes[commodity][r]
            for r in __selectRoutes(commodity, options['include_electrolysis'], options['dac_or_ccu'])
        }

        # calculate cost from tech data
        costDataList.append(calcCost(techDataFull, prices, selectedRoutes, commodity))


    return {
        'techDataFull': techDataFull,
        'costData': pd.concat(costDataList),
    }


# define which routes to work with based on options (include electrolysis, DAC vs CCU, etc.)
def __selectRoutes(commodity: dict, include_electrolysis: bool, dac_or_ccu: str):
    prefix = 'ELEC_'
    ret = [r for r in all_routes[commodity]]
    route_electrolysis = [r.lstrip(prefix) for r in ret if r.startswith(prefix)]
    inc = prefix if include_electrolysis else ''
    ret = [r for r in ret if r.lstrip(prefix) not in route_electrolysis] + [(inc + r) for r in route_electrolysis]

    filter = 'DAC' if dac_or_ccu=='CCU' else 'CCU'
    ret = [r for r in ret if filter not in r]

    return ret
