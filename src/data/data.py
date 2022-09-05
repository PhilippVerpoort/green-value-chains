import pandas as pd

from src.data.calc.calc_cost import calcCost
from src.data.params.full_params import getFullTechData
from src.load.load_default_data import all_routes


# obtain all required data for a scenario
def getFullData(input_data: dict):
    prices = input_data['prices']
    options = input_data['options']


    # convert basic inputs to complete dataframes
    techDataFull = getFullTechData(options['times'])


    # set prices for reference calculation
    exporterPrices = [p.rstrip(' exporter') for p in prices.id.unique() if p.endswith(' exporter')]
    pricesRef = pd.concat([
        prices.query("not id.str.endswith(' exporter')"),
        prices.query(f"id in {exporterPrices}").assign(id=lambda x: x.id.astype(str) + ' exporter'),
    ])


    # determine routes based on options
    costDataList = []
    costDataListRef = []
    for commodity in all_routes:
        selectedRoutes = {
            r: all_routes[commodity][r]
            for r in __selectRoutes(commodity, options['include_electrolysis'], options['dac_or_ccu'])
        }

        # calculate cost from tech data
        costDataList.append(calcCost(techDataFull, prices, selectedRoutes, commodity))

        # calculate reference cost without price differences for Fig. 3
        costDataListRef.append(calcCost(techDataFull, pricesRef, selectedRoutes, commodity))


    return {
        'techDataFull': techDataFull,
        'costData': pd.concat(costDataList),
        'costDataRef': pd.concat(costDataListRef),
        'prices': prices,
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
