from copy import deepcopy

import pandas as pd

from src.load.load_default_data import all_processes


def calcCost(tech_data_full: pd.DataFrame, prices: pd.DataFrame, selectedRoutes: dict, commodity: str, options: dict):
    # technology data
    selectedProcesses = list(set([p for route in selectedRoutes.values() for p in route['processes']]))
    selectedComponents = [all_processes[p]['output'] for p in selectedProcesses] + list(tech_data_full.query(f"process in @selectedProcesses").component.unique())
    techData = tech_data_full.filter(['process', 'type', 'component', 'subcomponent', 'val', 'val_year', 'mode'])\
                             .query(f"process in @selectedProcesses or (type=='transport' and component in @selectedComponents)")


    # prepare cost data
    costData = __prepareCostData(techData)


    # list of entries to return
    es_ret = []


    # loop over routes
    for route_id, route_details in selectedRoutes.items():
        if 'import_cases' in route_details and len(route_details['import_cases']) > 1:
            for case_name, case_imports in route_details['import_cases'].items():
                es_rout = __calcRouteCost(deepcopy(costData), prices, route_details['processes'], case_imports, options)
                es_ret.extend([e.assign(route=f"{route_id}--{case_name}", baseRoute=route_id, case=case_name) for e in es_rout])
        else:
            case_imports = next(c for c in route_details['import_cases'].values()) if route_details['import_cases'] else None
            es_rout = __calcRouteCost(deepcopy(costData), prices, route_details['processes'], case_imports, options)
            es_ret.extend([e.assign(route=route_id, baseRoute=route_id) for e in es_rout])


    r = pd.concat(es_ret, ignore_index=True).assign(commodity=commodity)

    r['component'] = r['component'].str.replace(' exporter', '')

    return r[['commodity', 'route', 'baseRoute', 'case', 'process', 'type', 'component', 'val', 'val_year']]


def __prepareCostData(techData: pd.DataFrame):
    # capital cost
    costCapital = techData.query("type=='capex'").assign(type='capital')
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


    costEnergyFeedstock = energyFeedstockPrices.drop(columns=['process', 'type', 'mode'])\
                                               .merge(energyFeedstockDemand.filter(['process', 'type', 'component', 'val', 'val_year', 'mode']), on=['component', 'val_year'])\
                                               .assign(val=lambda x: x.val_x * x.val_y)\
                                               .drop(columns=['val_x', 'val_y'])

    # transport cost
    costTransport = techData.query("type=='transport'")\
                            .drop(columns=['process', 'subcomponent'])\
                            .merge(pd.DataFrame.from_records([{'process': p, 'component': all_processes[p]['output']}
                                                              for p in techData.process.unique() if pd.notna(p)]), on=['component'], how='left')\
                            .rename(columns={'mode': 'modeTransp'})

    costTransport = pd.concat([
        costTransport.dropna(subset=['process']),
        costTransport.query('process.isnull()', engine='python')
                     .drop(columns=['process'])
                     .merge(energyFeedstockDemand.filter(['process', 'component', 'subcomponent', 'val', 'val_year', 'mode']), on=['component', 'val_year'], how='left')\
                     .assign(val=lambda x: x.val_x * x.val_y)
                     .drop(columns=['val_x', 'val_y'])
    ])


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


def __calcFCR(i: float, n: int):
    return i * (1 + i) ** n / ((1 + i) ** n - 1)


def __calcRouteCost(costData: dict, prices: pd.DataFrame, processes: dict, imports: list, options: dict):
    es_rout = {}


    # all intermediate process outputs
    allOutputs = [all_processes[p]['output'] for p in processes]


    # condition for using import or export prices
    importTokens = [i.split('--') for i in imports]
    importComponents = [t[0] for t in importTokens]
    importModes = {t[0]: t[1] for t in importTokens if len(t)>1}
    modeQuery = ''.join([f" | (component=='{i}' and modeTransp=='{m}')" for i, m in importModes.items()])
    processAbroad = __getProcessesAbroad(costData, processes, importComponents)

    setLocation = costData['demand']['component'].isin(prices.query("location!='either'").component.unique()) & ~costData['demand']['component'].isin(allOutputs)
    isImported = costData['demand']['process'].isin(processAbroad) | costData['demand']['component'].isin(importComponents if importComponents else [])

    costData['demand'].loc[:, 'location'] = 'either'
    costData['demand'].loc[setLocation & ~isImported, 'location'] = 'importer'
    costData['demand'].loc[setLocation & isImported, 'location'] = 'exporter'


    # country-specific fixed-charge rates
    costData['capital'].loc[:, 'location'] = 'importer'
    costData['capital'].loc[costData['capital']['process'].isin(processAbroad), 'location'] = 'exporter'

    fcr = pd.DataFrame.from_records([
        {
            'location': location,
            'fcr': __calcFCR(options['irate'][location]/100.0, options['ltime']),
        }
        for location in ['importer', 'exporter']
    ])

    costData['capital'] = costData['capital'] \
        .merge(fcr, on=['location']) \
        .assign(val=lambda x: x.val * x.fcr) \
        .drop(columns=['fcr'])


    # individual process steps
    for process in processes:
        output = all_processes[process]['output']
        mode = processes[process]['mode'] if 'mode' in processes[process] else None

        # list of entries in this process
        es_pro = []

        # query for cost data relevant to this process and the chosen route
        queryStr = f"process=='{process}' & (mode.isnull() | mode.str.contains('{mode}'))" if mode else f"process=='{process}'"
        thisCostData = {key: value.query(queryStr).copy() for key, value in costData.items()}

        # remove entries if not needed for this import case
        if 'dri' not in importComponents:
            thisCostData['demand'] = thisCostData['demand'].query("subcomponent!='Heating of CDRI'")

        # add all data that does not need further treatment (capital and fixed cost + energy & feedstock cost with fixed prices)
        es_pro.append(thisCostData['capital'])
        es_pro.append(thisCostData['fixed'])
        es_pro.append(thisCostData['energy_feedstock'])
        es_pro.append(thisCostData['transport'].query(f"component in @importComponents & (modeTransp.isnull(){modeQuery})"))

        # add data for energy and feedstock cost with prices read from route_prices that are not upstream outputs
        es_pro.append(
            thisCostData['demand'].query('component not in @allOutputs') \
                                  .merge(prices.filter(['component', 'location', 'val', 'val_year']), on=['component', 'location', 'val_year']) \
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

        # add entries from this process to all entries in this route and assign output from last process
        es_rout[output] = es_pro


    return es_rout[output]


def __getProcessesAbroad(costData: dict, processes: dict, imports: list):
    processes_abroad_len = 0
    processes_abroad = [p for p in processes if all_processes[p]['output'] in imports] if imports else []
    while len(processes_abroad) > processes_abroad_len:
        processes_abroad_len = len(processes_abroad)
        for p in processes:
            if p not in processes_abroad and all_processes[p]['output'] in costData['demand'].query(f"process in @processes_abroad")['component'].unique():
                processes_abroad.append(p)

    return processes_abroad
