import pandas as pd


# which of the process steps is moved to the exporting country in scenarios 1, 2, 3, and 4.
case_processes = {
    1: [],
    2: ['electrolysis'],
    3: ['electrolysis', 'dr'],
    4: ['electrolysis', 'dr', 'eaf'],
}


def calcCostComponentsH2(fullCostData: pd.DataFrame, share_scrap: float, el_p_local: dict, el_p_remote: dict, years: list, cases: list = [1, 2, 3, 4]):
    entries = []
    fullCostData = fullCostData.query(f"year in @years & techs.str.contains('h2')").drop(columns=['techs'])

    # capital cost
    i = 0.08
    n = 18
    FCR = i*(1+i)**n/((1+i)**n-1)
    IF = 1.8 # integration factor

    capexData = fullCostData.query("type=='capex'")
    e = capexData.query("name=='drshaft' | name=='eaf'").assign(val=lambda x: FCR * x.val * IF, type='capital')
    entries.append(e)
    e = capexData.query("name=='electrolyser'").merge(fullCostData.query("type=='energy_demand' & name=='h2'").filter(['year', 'val']), on='year')
    e = e.assign(val=lambda x: FCR/(4000.0*0.9) * x.val_x * x.val_y * IF, unit='EUR/t', type='capital').drop(columns=['val_x', 'val_y'])
    entries.append(e)

    # fixed cost
    fopexData = fullCostData.query("type=='fixed_opex'")
    totalCapcost = pd.concat(entries).sum().val
    e = fopexData.query("name=='fixed_onm'").assign(val=lambda x: totalCapcost * x.val, type='fopex')
    entries.append(e)
    e = fopexData.query("name=='labour'").assign(val=lambda x: x.val, type='fopex')
    entries.append(e)

    # feedstock cost
    feedstockDemand = fullCostData.query("type=='feedstock_demand'")
    feedstockPrices = fullCostData.query("type=='feedstock_prices'")
    e = feedstockDemand.merge(feedstockPrices.filter(['name', 'year', 'val']), on=['name', 'year'])
    e = e.assign(val=lambda x: x.val_x * x.val_y, unit='EUR/t', type='feedstock').drop(columns=['val_x', 'val_y'])
    entries.append(e)

    # ore cost
    multiply = pd.DataFrame.from_records([{'name': 'scrap', 'f': share_scrap}, {'name': 'ore', 'f': 1.0-share_scrap}])
    ironDemand = fullCostData.query("type=='iron_demand'")
    ironPrices = fullCostData.query("type=='iron_prices'")
    e = ironDemand.merge(ironPrices.filter(['name', 'year', 'val']), on=['name', 'year']).merge(multiply, on='name')
    e = e.assign(val=lambda x: x.f * x.val_x * x.val_y, unit='EUR/t', type='iron').drop(columns=['val_x', 'val_y', 'f'])
    entries.append(e)

    # energy cost
    eff = 0.72
    multiply = pd.DataFrame.from_records([
        {'name': 'h2', 'f': (1.0 - share_scrap)/eff},
        {'name': 'elec_dr', 'f': 1.0 - share_scrap},
        {'name': 'elec_eaf_scrap', 'f': share_scrap},
        {'name': 'elec_eaf_cdri', 'f': 1.0 - share_scrap},
        {'name': 'elec_eaf_cdri_heat', 'f': 1.0 - share_scrap},]
    )
    energyDemand = fullCostData.query("type=='energy_demand'")
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
        entries.append(e)

    # transport cost
    transportCost = fullCostData.query("type=='transport'")
    for c in cases:
        # iron ore imports
        if 'dr' not in case_processes[c]:
            e = transportCost.query("name=='ore'").merge(ironDemand.query("name=='ore'").filter(['name', 'year', 'val']), on=['name', 'year'])
            e = e.assign(val=lambda x: x.val_x * x.val_y).drop(columns=['val_x', 'val_y'])
            e['case'] = c
            entries.append(e)
        # hydrogen imports
        if 'electrolysis' in case_processes[c] and 'dr' not in case_processes[c]:
            e = transportCost.query("name=='h2'").merge(energyDemand.query("name=='h2'").filter(['name', 'year', 'val']), on=['name', 'year'])
            e = e.assign(val=lambda x: x.val_x * x.val_y).drop(columns=['val_x', 'val_y'])
            e['case'] = c
            entries.append(e)
        # dri imports
        if 'dr' in case_processes[c] and not 'eaf' in case_processes[c]:
            e = transportCost.query("name=='hbi'").assign(val=lambda x: (1.0 - share_scrap) * x.val)
            e['case'] = c
            entries.append(e)
        # steel imports
        if 'eaf' in case_processes[c]:
            e = transportCost.query("name=='steel'").assign(val=lambda x: (1.0 - share_scrap) * x.val)
            e['case'] = c
            entries.append(e)


    r = pd.concat(entries, ignore_index=True)
    #print(r.query(f"year==2025 & not case.isin([2,3,4])").drop(columns=['uncertainty', 'uncertainty_lower', 'case', 'year']))

    r = __completeData(r)
    return r[['type', 'name', 'year', 'case', 'val']]


def __completeData(costData: pd.DataFrame):
    naData = costData.query(f"case.isna()").reset_index(drop=True).assign(dummy='dummy')
    cases = pd.DataFrame.from_dict({'case': [1, 2, 3, 4], 'dummy': ['dummy']*4})
    addCases = naData.merge(cases, on='dummy', suffixes=('_nan', '')).drop(columns=['case_nan', 'dummy'])

    combined = pd.concat([addCases, costData.dropna(subset=['case'])])
    return combined[costData.keys()]
