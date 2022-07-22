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
    for process_group in process_routes:
        routes = __getRoutes(process_group, options['include_electrolysis'], options['dac_or_ccu'])
        routes_details = {r: process_routes[process_group][r] for r in routes}

        # calculate cost from tech data
        techData = techDataFull.query(f"process_group.str.contains('{process_group}')")
        costDataList.append(calcCost(techData, prices, routes_details))


    return {
        'techDataFull': techDataFull,
        'costData': pd.concat(costDataList),
    }


# define which routes to work with based on options (include electrolysis, DAC vs CCU, etc.)
def __getRoutes(process_group: dict, include_electrolysis: bool, dac_or_ccu: str):
    prefix = 'ELEC_'
    routes = [r for r in process_routes[process_group]]
    route_electrolysis = [r.lstrip(prefix) for r in routes if r.startswith(prefix)]
    inc = prefix if include_electrolysis else ''
    routes = [r for r in routes if r.lstrip(prefix) not in route_electrolysis] + [(inc + r) for r in route_electrolysis]

    filter = 'DAC' if dac_or_ccu=='CCU' else 'CCU'
    routes = [r for r in routes if filter not in r]

    return routes
