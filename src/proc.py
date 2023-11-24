import numpy as np
import pandas as pd

from posted.units.units import ureg


# process cases
def process_inputs(inputs: dict, outputs: dict):
    vcs = inputs['value_chains']

    # calculate epd from price cases
    outputs['epd'] = inputs['epdcases'] \
        .assign(epd=lambda df: df['RE-scarce'] - df['RE-rich']) \
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
        proc_locs = pd.DataFrame(data=[
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
        outputs['procLocs'][comm] = proc_locs

        # get dataframe mapping epdcases and associated elec prices to processes
        proc_locs_stacked = proc_locs \
            .stack() \
            .swaplevel(0, 1, 0) \
            .to_frame('location') \
            .reset_index() \
            .set_index(['process', 'location'])

        # electricity-price difference cases by process
        epdcases_by_proc = pd.concat(
            [inputs['epdcases'].query("process!='OTHER'")] +
            [inputs['epdcases'].query("process=='OTHER'").assign(process=p) for p in proc_locs.columns if p != 'ELH2']
        )

        outputs['cases'][comm] = epdcases_by_proc \
            .set_index(['process', 'epdcase']) \
            .rename_axis('location', axis=1) \
            .stack() \
            .to_frame('price:elec') \
            .merge(proc_locs_stacked, left_index=True, right_index=True) \
            .reset_index() \
            .drop(columns='location') \
            .set_index(['impcase', 'epdcase', 'process']) \
            .rename_axis('type', axis=1) \
            .unstack('process')

        # financing assumptions
        assump_wacc = proc_locs \
            .replace('RE-scarce', inputs['other_assump']['irate']['RE-scarce']) \
            .replace('RE-rich', inputs['other_assump']['irate']['RE-rich']) \
            .astype(float) \
            .apply(lambda x: x/100.0) \
            .assign(type='wacc') \
            .set_index('type', append=True) \
            .unstack('type')
        table = inputs['vc_tables'][comm] \
            .assume(assump_wacc) \
            .assume({'lifetime': 18.0 * ureg('a')})

        # insert dummy process
        new_data = table.data.copy()
        new_data['value', f"demand_sc:{table.refFlow}", 'DUMMY'] = 1.0
        table.data = new_data

        # find goods in value chain that have transport cost
        traded = [
            t.split(':')[-1] for t in outputs['transp_cost'].columns
            if table.data.columns.unique(level=1).str.match(fr"^demand(_sc)?:{t.split(':')[-1]}$").any()
        ]

        # create dataframe containing transport cost assumptions
        assump_transp = pd.DataFrame(
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
                    assump_transp.loc[(proc_locs[p1] != proc_locs[p2]), t] = 1
        assump_transp.loc['Case 3', table.refFlow] = 1
        if comm == 'Steel':
            assump_transp.loc[['Base Case', 'Case 1'], 'ironore'] = 1

        # determine trade cost cases (including impsubcases)
        trade_cost_cases = []
        for impcase, row in assump_transp.iterrows():
            trade_cost_case = pd.DataFrame(columns=['impcase'], data=[impcase])
            for t in row.dropna().index.tolist():
                tmp = outputs['transp_cost'] \
                    .loc[:, t] \
                    .dropna() \
                    .to_frame() \
                    .rename_axis(f"impsubcase_{t}") \
                    .reset_index()
                trade_cost_case = trade_cost_case.merge(tmp, how='cross').dropna(axis=1, how='all')
            trade_cost_cases.append(trade_cost_case)
        assump_transp = pd.concat(trade_cost_cases)
        index_cols = [c for c in assump_transp if c not in traded]
        assump_transp = assump_transp \
            .fillna({c: '' for c in index_cols}) \
            .set_index(index_cols) \
            .rename(columns={c: f"transp:{c}" for c in traded}) \
            .rename_axis('type', axis=1)
        assump_transp.index = assump_transp.index \
            .map(lambda i: (i[0], f"{i[0]}{i[1]}")) \
            .rename(['impcase', 'impsubcase'])

        # add trade cost assumptions to table
        table = table.assume(assump_transp)

        # associate reheating cases to impcases
        if comm == 'Steel':
            table.data = table.data \
                .query(f"(reheating=='w/o reheating' & impcase!='Case 2') | "
                       f"(reheating=='w/ reheating') & (impcase=='Case 2')") \
                .droplevel(level='reheating')

        outputs['tables'][comm] = table
