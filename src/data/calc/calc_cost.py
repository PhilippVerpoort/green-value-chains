import pandas as pd

from src.load.load_default_data import process_data


def calcCost(tech_data_full: pd.DataFrame, assumptions: pd.DataFrame, routes: dict):
    # technology data
    techData = tech_data_full.filter(['process', 'type', 'component', 'subcomponent', 'val', 'val_year', 'mode'])


    # prepare cost data
    costData = __prepareCostData(techData)


    # obtain prices from spreadsheet
    defaultPrices = assumptions.query(f"id.str.startswith('price ')").filter(['id', 'val', 'val_year']).rename(columns={'id': 'component'})
    defaultPrices['component'] = defaultPrices['component'].str.replace('price ', '')


    # list of entries to return
    es_ret = []


    # loop over routes
    for route_id, route_details in routes.items():
        if route_details['import_cases']:
            for case_name, case_imports in route_details['import_cases'].items():
                es_rout = __calcRouteCost(costData, defaultPrices, route_details['processes'], case_imports)
                es_ret.extend([e.assign(route=f"{route_id}_{case_name}") for e in es_rout])
        else:
            es_rout = __calcRouteCost(costData, defaultPrices, route_details['processes'], None)
            es_ret.extend([e.assign(route=route_id) for e in es_rout])


    r = pd.concat(es_ret, ignore_index=True)

    r['component'] = r['component'].str.replace(' exporter', '')

    return r[['route', 'process', 'type', 'component', 'val', 'val_year']]


def __prepareCostData(techData: pd.DataFrame):
    # for calculating annualised capital cost
    i = 0.08
    n = 18
    FCR = i * (1 + i) ** n / ((1 + i) ** n - 1)
    IF = 1.8  # integration factor

    # capital cost
    costCapital = techData.query("type=='capex'").assign(val=lambda x: FCR * IF * x.val, type='capital')
    costCapital.loc[costCapital['process'] == 'ELEC', 'val'] /= 8760.0 # convert MW to MWh_pa

    # fixed cost
    fopexData = techData.query("type=='fixed_opex'")
    fopexDataOnM = fopexData.query("component=='onm'")\
                            .merge(costCapital.filter(['process', 'val', 'val_year']), on=['process', 'val_year'])\
                            .assign(val=lambda x: x.val_x * x.val_y, type='fonmco')\
                            .drop(columns=['val_x', 'val_y'])
    fopexDataLabour = fopexData.query("component=='labour'").assign(val=lambda x: x.val, type='fonmco')
    costFixed = pd.concat([fopexDataOnM, fopexDataLabour])

    # energy and feedstock cost
    energyFeedstockPrices = techData.query("type=='energy_prices' | type=='feedstock_prices'")
    energyFeedstockDemand = techData.query("type=='energy_demand' | type=='feedstock_demand'")
    energyFeedstockDemand.loc[energyFeedstockDemand['type'] == 'feedstock_demand', 'type'] = 'feedstock'
    energyFeedstockDemand.loc[energyFeedstockDemand['type'] == 'energy_demand', 'type'] = 'energy'


    costEnergyFeedstock = energyFeedstockPrices.drop(columns=['type', 'mode'])\
                                               .merge(energyFeedstockDemand.filter(['process', 'type', 'component', 'val', 'val_year', 'mode']), on=['process', 'component', 'val_year'])\
                                               .assign(val=lambda x: x.val_x * x.val_y)\
                                               .drop(columns=['val_x', 'val_y'])

    # transport cost
    costTransport = techData.query("type=='transport'")

    costTransport = costTransport.merge(energyFeedstockDemand.filter(['process', 'component', 'val', 'val_year']), on=['process', 'component', 'val_year'], how='left') \
                                 .fillna({'val_y': 1.0}) \
                                 .assign(val=lambda x: x.val_x * x.val_y) \
                                 .drop(columns=['val_x', 'val_y'])

    # remaining energy and feedstock demand
    mergeDummy = energyFeedstockPrices.filter(['process', 'component', 'val_year']).assign(remove=True)
    energyFeedstockDemand = energyFeedstockDemand.merge(mergeDummy, on=['process', 'component', 'val_year'], how='outer')
    energyFeedstockDemand = energyFeedstockDemand[pd.isnull(energyFeedstockDemand['remove'])].drop(columns=['remove'])

    return {
        'capital': costCapital,
        'fixed': costFixed,
        'energy_feedstock': costEnergyFeedstock,
        'demand': energyFeedstockDemand,
        'transport': costTransport,
    }


def __calcRouteCost(costData: dict, defaultPrices: pd.DataFrame, processes: dict, imports: list):
    es_rout = {}

    routePrices = defaultPrices.copy()
    routePricesExportSpec = [c.rstrip(' exporter') for c in routePrices.query("component.str.contains('exporter')").component.unique()]

    processes_abroad = __getProcessesAbroad(costData, processes, imports)
    all_outputs = [process_data[p]['output'] for p in processes]

    for process in processes:
        output = process_data[process]['output']
        mode = processes[process]['mode'] if 'mode' in processes[process] else None

        # list of entries in this process
        es_pro = []

        # query for cost data relevant to this process and the chosen route
        queryStr = f"process=='{process}' & (mode.isnull() | mode.str.contains('{mode}'))" if mode else f"process=='{process}'"
        thisCostData = {key: value.query(queryStr) for key, value in costData.items()}

        # add all data that does not need further treatment (capital & fixed cost + energy & feedstock cost with fixed prices)
        es_pro.append(thisCostData['capital'])
        es_pro.append(thisCostData['fixed'])
        es_pro.append(thisCostData['energy_feedstock'])

        # make processes on the exporter side use exporters prices
        if process in processes_abroad:
            cond = thisCostData['demand']['component'].isin(routePricesExportSpec) & ~thisCostData['demand']['component'].isin(all_outputs) & (thisCostData['demand']['process']==process)
            pd.options.mode.chained_assignment = None
            thisCostData['demand'].loc[cond, 'component'] = thisCostData['demand'].loc[cond, 'component'].replace('$', ' exporter', regex=True)
            pd.options.mode.chained_assignment = 'warn'

        # add data for energy and feedstock cost with prices read from route_prices that are not upstream outputs
        es_pro.append(
            thisCostData['demand'].query('component not in @all_outputs') \
                                  .merge(routePrices, on=['component', 'val_year']) \
                                  .assign(val=lambda x: x.val_x * x.val_y) \
                                  .drop(columns=['val_x', 'val_y'])
        )

        # rescale cost components of upstream processes by demand of output commodity and append
        for output_upstream in es_rout:
            d = thisCostData['demand'].query(f"component=='{output_upstream}'").filter(['val', 'val_year'])
            for e in es_rout[output_upstream]:
                es_pro.append(
                    e.merge(d, on=['val_year']) \
                     .assign(val=lambda x: x.val_x * x.val_y) \
                     .drop(columns=['val_x', 'val_y'])
                )

        # transport cost
        if imports:
            es_pro.append(thisCostData['transport'].query(f"component in @imports"))

        # add entries from this process to all entries in this route and assign output from last process
        es_rout[output] = es_pro

    return es_rout[output]


def __getProcessesAbroad(costData: dict, processes: dict, imports: list):
    processes_abroad_len = 0
    processes_abroad = [p for p in processes if process_data[p]['output'] in imports] if imports else []
    while len(processes_abroad) > processes_abroad_len:
        processes_abroad_len = len(processes_abroad)
        for p in processes:
            if p not in processes_abroad and process_data[p]['output'] in costData['demand'].query(f"process in @processes_abroad")['component'].unique():
                processes_abroad.append(p)

    return processes_abroad