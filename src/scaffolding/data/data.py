import pandas as pd

from src.custom.data.calc.calc_cost import calcCost
from src.custom.data.params.full_params import getFullTechData
from src.scaffolding.file.load_data import all_routes


# obtain all required data for a scenario
def getFullData(input_data: dict):
    other_prices = input_data['other_prices']
    elec_prices = input_data['elec_prices']
    options = input_data['options']

    # convert basic inputs to complete dataframes
    techDataFull = getFullTechData(options['times'])

    # get reference hydrogen transport cost for data
    techCostH2Transp = techDataFull.query(f"type=='transport' and component=='hydrogen'")

    # calculate dataframe containing price differences
    elecPriceDiff = __getElecPriceDiff(elec_prices)

    # determine routes based on options
    costData, costDataRec = __getCostData(techDataFull, other_prices, options)

    return {
        'techDataFull': techDataFull,
        'techCostH2Transp': techCostH2Transp,
        'elecPriceDiff': elecPriceDiff,
        'costData': costData,
        'costDataRec': costDataRec,
    }


def __getCostData(techDataFull, other_prices, options):
    costDataList = []
    costDataListRec = []
    for commodity in all_routes:
        routes = {
            r: all_routes[commodity][r]
            for r in __selectRoutes(commodity, options['include_electrolysis'])
        }

        recyclingTokens = ['SECONDARY', 'CCU']
        routesWORecycling = {k: v for k, v in routes.items() if not any(t in k for t in recyclingTokens)}
        routesWithRecycling = {k: v for k, v in routes.items() if any(t in k for t in recyclingTokens)}

        # calculate cost from tech data
        costDataList.append(calcCost(techDataFull, other_prices, routesWORecycling, commodity, options))

        # calculate recycling cost for figS4
        costDataListRec.append(calcCost(techDataFull, other_prices, routesWithRecycling, commodity, options))

    return pd.concat(costDataList), pd.concat(costDataListRec)


def __getElecPriceDiff(elec_prices):
    locations = ('importer', 'exporter')
    elecPriceDiff = pd.merge(
            *(
                elec_prices.query(f"location=='{l}'").filter(['epdcase', 'period', 'val'])
                for l in locations
            ),
            on=['epdcase', 'period'],
            suffixes=(f"_{l}" for l in locations),
        ) \
        .assign(priceDiff=lambda x: x.val_importer - x.val_exporter)

    return elecPriceDiff


# define which routes to work with based on options (include electrolysis, DAC vs CCU, etc.)
def __selectRoutes(commodity: dict, include_electrolysis: bool):
    prefix = 'ELEC_'
    ret = [r for r in all_routes[commodity]]
    route_electrolysis = [r.replace(prefix, '') for r in ret if r.startswith(prefix)]
    inc = prefix if include_electrolysis else ''
    ret = [r for r in ret if r.replace(prefix, '') not in route_electrolysis] + [(inc + r) for r in route_electrolysis]

    return ret
