import pandas as pd

from src.load.load_default_data import process_data


def calcCost(tech_data_full: pd.DataFrame, assumptions: pd.DataFrame, routes: dict):
    # technology data
    techData = tech_data_full.filter(['process', 'type', 'component', 'subcomponent', 'val', 'val_year', 'mode'])


    # prepare cost data
    costData = prepareCostData(techData)


    # obtain prices from spreadsheet
    prices = assumptions.query(f"id.str.startswith('price ')").filter(['id', 'val', 'val_year']).rename(columns={'id': 'component'})
    prices['component'] = prices['component'].str.replace('price ', '')


    # list of entries to return
    es_ret = []


    # loop over routes
    for route, processes in routes.items():
        route_prices = prices.copy()
        route_prices['upstream'] = False

        # create list of entries for all processes in this route
        es_rout = []
        for process in processes:
            output = process_data.query(f"id=='{process}'").output.iloc[0]
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

            # add data for energy and feedstock cost with prices read from route_prices
            tmp = thisCostData['demand'].query(queryStr) \
                                        .merge(route_prices, on=['component', 'val_year']) \
                                        .assign(val=lambda x: x.val_x * x.val_y) \
                                        .drop(columns=['val_x', 'val_y'])

            # add type 'upstream' if price comes from cost of an upstream process
            tmp.loc[tmp['upstream'], 'type'] = 'upstream'
            es_pro.append(tmp.drop(columns='upstream'))

            # rescale cost components of upstream processes by demand of output commodity
            feedstocks_upstream = route_prices.query('upstream==True')['component'].unique()
            downstream_demands = thisCostData['demand'].query(f"component in @feedstocks_upstream")

            for process_upstream in processes:
                output_upstream = process_data.query(f"id=='{process_upstream}'").output.iloc[0]
                downstream_demands.loc[downstream_demands['component']==output_upstream, 'process'] = process_upstream
            downstream_demands = downstream_demands.filter(['process', 'val', 'val_year'])

            es_rout = [
                e.merge(downstream_demands, on=['process', 'val_year']) \
                 .assign(val=lambda x: x.val_x * x.val_y) \
                 .drop(columns=['val_x', 'val_y'])
                for e in es_rout
            ]

            # add entries from this process to all entries in this route
            es_rout.extend(es_pro)

            # add total cost of produced commodity to prices for downstream processes
            output_cost = pd.concat(es_pro).filter(['val', 'val_year']).groupby(['val_year']).sum().reset_index()
            route_prices = pd.concat([
                route_prices.query(f"component!='{output}'"),
                output_cost.assign(component=output, upstream=True),
            ])

        # add list of entries from this route to all entries returned
        es_ret.extend([e.assign(route=route) for e in es_rout])


    r = pd.concat(es_ret, ignore_index=True)
    return r[['route', 'process', 'type', 'component', 'val', 'val_year']]


    # ore cost
    multiply = pd.DataFrame.from_records([{'name': 'scrap', 'f': share_scrap}, {'name': 'ore', 'f': 1.0-share_scrap}])
    ironDemand = techData.query("type=='iron_demand'")
    ironPrices = techData.query("type=='iron_prices'")
    e = ironDemand.merge(ironPrices.filter(['name', 'year', 'val']), on=['name', 'year']).merge(multiply, on='name')
    e = e.assign(val=lambda x: x.f * x.val_x * x.val_y, unit='EUR/t', type='iron').drop(columns=['val_x', 'val_y', 'f'])
    es_rout.append(e)

    # energy cost
    eff = 0.72
    multiply = pd.DataFrame.from_records([
        {'name': 'h2', 'f': (1.0 - share_scrap)/eff},
        {'name': 'elec_dr', 'f': 1.0 - share_scrap},
        {'name': 'elec_eaf_scrap', 'f': share_scrap},
        {'name': 'elec_eaf_cdri', 'f': 1.0 - share_scrap},
        {'name': 'elec_eaf_cdri_heat', 'f': 1.0 - share_scrap},]
    )
    energyDemand = techData.query("type=='energy_demand'")
    for c in cases:
        energyPrices = []
        for y in years:
            ep = {
                'remote': el_p_remote[y],
                'local': el_p_local[y],
            }
            energyPrices.extend([
                {'year': y, 'name': 'h2', 'val': ep['remote'] if 'electrolysis' in case_processes[c] else ep['local']},
                {'year': y, 'name': 'elec_dr', 'val': ep['remote'] if 'dr' in case_processes[c] else ep['local']},
                {'year': y, 'name': 'elec_eaf_scrap', 'val': ep['remote'] if 'eaf' in case_processes[c] else ep['local']},
                {'year': y, 'name': 'elec_eaf_cdri', 'val': ep['remote'] if 'eaf' in case_processes[c] else ep['local']},
                {'year': y, 'name': 'elec_eaf_cdri_heat', 'val': ep['remote'] if 'eaf' in case_processes[c] else ep['local']},
            ])
        energyPrices = pd.DataFrame.from_records(energyPrices)

        e = energyDemand.merge(energyPrices, on=['name', 'year']).merge(multiply, on='name')
        e = e.assign(val=lambda x: x.f * x.val_x * x.val_y, unit='EUR/t', type='energy').drop(columns=['val_x', 'val_y', 'f'])
        e['case'] = c
        es_rout.append(e)

    # transport cost
    transportCost = techData.query("type=='transport'")
    for c in cases:
        # iron ore imports
        if 'dr' not in case_processes[c]:
            e = transportCost.query("name=='ore'").merge(ironDemand.query("name=='ore'").filter(['name', 'year', 'val']), on=['name', 'year'])
            e = e.assign(val=lambda x: x.val_x * x.val_y).drop(columns=['val_x', 'val_y'])
            e['case'] = c
            es_rout.append(e)
        # hydrogen imports
        if 'electrolysis' in case_processes[c] and 'dr' not in case_processes[c]:
            e = transportCost.query("name=='h2'").merge(energyDemand.query("name=='h2'").filter(['name', 'year', 'val']), on=['name', 'year'])
            e = e.assign(val=lambda x: x.val_x * x.val_y).drop(columns=['val_x', 'val_y'])
            e['case'] = c
            es_rout.append(e)
        # dri imports
        if 'dr' in case_processes[c] and not 'eaf' in case_processes[c]:
            e = transportCost.query("name=='hbi'").assign(val=lambda x: (1.0 - share_scrap) * x.val)
            e['case'] = c
            es_rout.append(e)
        # steel imports
        if 'eaf' in case_processes[c]:
            e = transportCost.query("name=='steel'").assign(val=lambda x: (1.0 - share_scrap) * x.val)
            e['case'] = c
            es_rout.append(e)


    r = pd.concat(es_rout, ignore_index=True)
    #print(r.query(f"year==2025 & not case.isin([2,3,4])").drop(columns=['uncertainty', 'uncertainty_lower', 'case', 'year']))

    r = __completeData(r)
    return r[['type', 'name', 'year', 'case', 'val']]


def prepareCostData(techData: pd.DataFrame):
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


    costEnergyFeedstock = energyFeedstockPrices.drop(columns='type')\
                                               .merge(energyFeedstockDemand.filter(['process', 'type', 'component', 'val', 'val_year']), on=['process', 'component', 'val_year'])\
                                               .assign(val=lambda x: x.val_x * x.val_y)\
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
    }
