import pandas as pd


def calcCostComponentsNG(fullCostData: pd.DataFrame, share_scrap: float, elec_price: dict, ng_price: dict, years: list):
    entries = []
    fullCostData = fullCostData.query(f"year in @years & techs.str.contains('ng')").drop(columns=['techs'])

    # capital cost
    i = 0.08
    n = 18
    FCR = i*(1+i)**n/((1+i)**n-1)
    IF = 1.8 # integration factor

    capexData = fullCostData.query("type=='capex'")
    e = capexData.query("name=='drshaft' | name=='eaf'").assign(val=lambda x: FCR * x.val * IF, type='capital')
    entries.append(e)
    e = capexData.query("name=='electrolyser'").merge(fullCostData.query("type=='energy_demand' & name=='h2'").filter(['year', 'val']), on='year')
    e = e.assign(val=lambda x: FCR/(8760.0*0.9) * x.val_x * x.val_y * IF, unit='EUR/t', type='capital').drop(columns=['val_x', 'val_y'])
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
    multiply = pd.DataFrame.from_records([
        {'name': 'ng', 'f': (1.0 - share_scrap)},
        {'name': 'elec_dr', 'f': 1.0 - share_scrap},
        {'name': 'elec_eaf_scrap', 'f': share_scrap},
        {'name': 'elec_eaf_cdri', 'f': 1.0 - share_scrap},
        {'name': 'elec_eaf_cdri_heat', 'f': 1.0 - share_scrap},]
    )
    energyDemand = fullCostData.query("type=='energy_demand'")
    energyPrices = []
    for y in years:
        energyPrices.extend([
            {'year': y, 'name': 'ng', 'val': ng_price[y]},
            {'year': y, 'name': 'elec_dr', 'val': elec_price[y]},
            {'year': y, 'name': 'elec_eaf_scrap', 'val': elec_price[y]},
            {'year': y, 'name': 'elec_eaf_cdri', 'val': elec_price[y]},
            {'year': y, 'name': 'elec_eaf_cdri_heat', 'val': elec_price[y]},
        ])
    energyPrices = pd.DataFrame.from_records(energyPrices)
    e = energyDemand.merge(energyPrices, on=['name', 'year']).merge(multiply, on='name')
    e = e.assign(val=lambda x: x.f * x.val_x * x.val_y, unit='EUR/t', type='energy').drop(columns=['val_x', 'val_y', 'f'])
    entries.append(e)


    # transport cost
    transportCost = fullCostData.query("type=='transport'")
    # iron ore imports
    e = transportCost.query("name=='ore'").merge(ironDemand.query("name=='ore'").filter(['name', 'year', 'val']), on=['name', 'year'])
    e = e.assign(val=lambda x: x.val_x * x.val_y).drop(columns=['val_x', 'val_y'])
    entries.append(e)


    # carbon cost
    ngDemand = energyDemand.query("name=='ng'")
    ng_ghgi = 0.25
    e = ngDemand.assign(val=lambda x: ng_ghgi * x.val, type='carbon')
    entries.append(e)


    r = pd.concat(entries, ignore_index=True)
    r['case'] = 'NG'
    return r[['type', 'name', 'year', 'case', 'val']]
