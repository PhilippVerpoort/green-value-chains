import numpy as np
import pandas as pd

from posted.units.units import ureg


# process cases
def process_inputs(inputs: dict, outputs: dict):
    vcs = inputs['value_chains']

    # calculate epd from price cases
    outputs['epd'] = inputs['epdcases'] \
        .assign(epd=lambda row: row['RE-scarce'] - row['RE-rich']) \
        .rename_axis('type', axis=1) \
        .sort_values(by='epd')

    # calculate transport cost outputs from inputs
    outputs['transp_cost'] = inputs['transp_cost'] \
        .set_index(['traded', 'impsubcase', 'unit']) \
        .transpose() \
        .stack('impsubcase') \
        .pint.quantify() \
        .droplevel(0)

    # associate correct RE prices with processes
    outputs['cases'] = {}
    outputs['tables'] = {}
    outputs['procLocs'] = {}
    for comm in vcs:
        locs = vcs[comm]['locations']

        # get dataframe of process locations
        procLocs = pd.DataFrame(data=[
                {
                    'impcase': f"Case {i}" if i else 'Base Case',
                    **{
                        p: loc
                        for loc, pgList in {'RE-rich': locs[:i], 'RE-scarce': locs[i:]}.items()
                        for pg in pgList for p in pg
                    }
                }
                for i in range(4)
            ]) \
            .set_index('impcase') \
            .rename_axis('process', axis=1)
        outputs['procLocs'][comm] = procLocs

        # get dataframe mapping epdcases and associated elec prices to processes
        procLocsStacked = procLocs \
            .stack() \
            .swaplevel(0, 1, 0) \
            .to_frame('location') \
            .reset_index() \
            .set_index(['process', 'location'])

        # electricity-price difference cases by process
        epdcasesByProc = pd.concat(
            [inputs['epdcases'].query("process!='OTHER'")]
          + [inputs['epdcases'].query("process=='OTHER'").assign(process=p)
             for p in procLocs.columns if p != 'ELH2']
        )

        outputs['cases'][comm] = epdcasesByProc \
            .set_index(['process', 'epdcase']) \
            .rename_axis('location', axis=1) \
            .stack() \
            .to_frame('price:elec') \
            .merge(procLocsStacked, left_index=True, right_index=True) \
            .reset_index() \
            .drop(columns='location') \
            .set_index(['impcase', 'epdcase', 'process']) \
            .rename_axis('type', axis=1) \
            .unstack('process')

        # financing assumptions
        assumpWACC = procLocs \
            .replace('RE-scarce', inputs['other_assump']['irate']['RE-scarce']) \
            .replace('RE-rich', inputs['other_assump']['irate']['RE-rich']) \
            .astype(float) \
            .apply(lambda x: x/100.0) \
            .assign(type='wacc') \
            .set_index('type', append=True) \
            .unstack('type')
        table = inputs['vc_tables'][comm] \
            .assume(assumpWACC) \
            .assume({'lifetime': 18.0 * ureg('a')})

        # insert dummy process
        newData = table.data.copy()
        newData['value', f"demand_sc:{table.refFlow}", 'DUMMY'] = 1.0
        table.data = newData

        # find goods in value chain that have transport cost
        traded = [
            t.split(':')[-1] for t in outputs['transp_cost'].columns
            if table.data.columns.unique(level=1).str.match(fr"^demand(_sc)?:{t.split(':')[-1]}$").any()
        ]

        # create dataframe containing transport cost assumptions
        assumpTransp = pd.DataFrame(
            index=[f"Case {i}" if i else 'Base Case' for i in range(4)],
            columns=traded,
            data=np.nan,
        ) \
        .rename_axis('impcase') \
        .rename_axis('traded', axis=1)

        # match traded goods to import cases
        for p1, p1s in vcs[comm]['graph'].items():
            for t, p2 in p1s.items():
                if t in traded:
                    assumpTransp.loc[(procLocs[p1] != procLocs[p2]), t] = 1
        assumpTransp.loc['Case 3', table.refFlow] = 1
        if comm == 'Steel':
            assumpTransp.loc[['Base Case', 'Case 1'], 'ironore'] = 1

        # determine trade cost cases (including impsubcases)
        tradeCostCases = []
        for impcase, row in assumpTransp.iterrows():
            tradeCostCase = pd.DataFrame(columns=['impcase'], data=[impcase])
            for t in row.dropna().index.tolist():
                tmp = outputs['transp_cost'] \
                    .loc[:, t] \
                    .dropna() \
                    .to_frame() \
                    .rename_axis(f"impsubcase_{t}") \
                    .reset_index()
                tradeCostCase = tradeCostCase.merge(tmp, how='cross').dropna(axis=1, how='all')
            tradeCostCases.append(tradeCostCase)
        assumpTransp = pd.concat(tradeCostCases)
        indexCols = [c for c in assumpTransp if c not in traded]
        assumpTransp = assumpTransp \
            .fillna({c: '' for c in indexCols}) \
            .set_index(indexCols) \
            .rename(columns={c: f"transp:{c}" for c in traded}) \
            .rename_axis('type', axis=1)
        assumpTransp.index = assumpTransp.index \
            .map(lambda i: (i[0], f"{i[0]}{i[1]}")) \
            .rename(['impcase', 'impsubcase'])

        # add trade cost assumptions to table
        table = table.assume(assumpTransp)

        # associate reheating cases to impcases
        if comm == 'Steel':
            table.data = table.data \
                .query(f"(reheating=='w/o reheating' & impcase!='Case 2') | "
                       f"(reheating=='w/ reheating') & (impcase=='Case 2')") \
                .droplevel(level='reheating')

        outputs['tables'][comm] = table
