from pathlib import Path

import pandas as pd
from posted.ted.TEDataSet import TEDataSet
from posted.ted.TEProcessTreeDataTable import TEProcessTreeDataTable
from posted.ted.Mask import Mask

from src.utils import load_yaml_data_file, load_csv_data_file


def load_data(inputs: dict):
    # load data for electricity-price cases
    inputs['epdcases'] = load_csv_data_file('epd_cases') \
        .astype({c: 'pint[EUR/MWh]' for c in ('RE-scarce', 'RE-rich')}, errors='ignore')

    # load data for other prices
    inputs['other_prices'] = load_csv_data_file('other_prices') \
        .astype({'assump': 'float32'}, errors='ignore') \
        .set_index(['type', 'unit']) \
        .transpose() \
        .pint.quantify() \
        .reset_index(drop=True)

    # load data for specific transport cost
    inputs['transp_cost'] = load_csv_data_file('transp_cost') \
        .astype({'assump': 'float32'}, errors='ignore')

    # load other assumptions
    inputs['other_assump'] = load_yaml_data_file('other_assump')

    # load scenarios and volumes
    inputs['scenarios'] = load_csv_data_file('scenarios').set_index(['scenario', 'commodity'])
    inputs['volumes'] = load_csv_data_file('volumes').astype({'volume': 'float32'}).set_index(['commodity'])['volume']

    # load value chain definitions
    inputs['value_chains'] = load_yaml_data_file('value_chains')


def load_posted(inputs: dict):
    # create list of technologies to load
    vcs = inputs['value_chains']
    techs = {k: {} for comm in vcs for k in vcs[comm]['graph'].keys()}

    # add settings for loading the data
    techs['ELH2'] |= {
        'subtech': 'Alkaline',
        'masks': [
            Mask(
                when="type.str.startswith('capex')",
                use=f"src_ref.isin({'Vartiainen et al. (2022)', 'IRENA Global Hydrogen trade costs (2022)'})",
            ),
            Mask(
                when="type.str.startswith('demand:elec')",
                use=f"src_ref.isin({'Vartiainen et al. (2022)', 'IRENA Global Hydrogen trade costs (2022)'})",
            ),
        ],
    }
    techs['DAC'] |= {
        'subtech': 'LT-DAC',
        'masks': [
            Mask(
                when="type.str.startswith('capex')",
                use="src_ref=='custom'",
            )
        ]
    }
    techs['IDR'] |= {'mode': 'h2'}
    techs['EAF'] |= {'mode': 'primary'}

    # load datatables from POSTED
    inputs['proc_tables'] = {}
    for tid, kwargs in techs.items():
        dac = {'load_other': [Path(__file__).parent.parent / 'data' / 'DAC-capex-custom.csv'], 'load_database': True} \
              if tid == 'DAC' else {}
        t = TEDataSet(tid, **dac).generateTable(
            period=inputs['other_assump']['period'],
            agg=['src_ref'],
            **kwargs,
        )
        inputs['proc_tables'][tid] = t

    # generate process graph datatables
    inputs['vc_tables'] = {}
    for comm, details in vcs.items():
        graph = vcs[comm]['graph']
        t = TEProcessTreeDataTable(*(inputs['proc_tables'][tid] for tid in graph), processGraph=graph)

        # map heat to electricity
        all_cols = []
        for idx, cols in t.data.groupby(by=[c for c in t.data.columns.names if c != 'type'], axis=1):
            cols = cols.copy()
            if 'demand:heat' in cols.columns.get_level_values(level='type'):
                cols[(*idx, 'demand:elec')] += cols[(*idx, 'demand:heat')].fillna(0)
                cols = cols.drop(columns=[(*idx, 'demand:heat')])
            all_cols.append(cols)
        t.data = pd.concat(all_cols, axis=1)

        inputs['vc_tables'][comm] = t


def load_other(inputs: dict):
    # add OCF and other prices (all except electricity) to tables
    for comm, table in inputs['vc_tables'].items():
        # other prices
        assump_other = inputs['other_prices']

        # ocf assumptions
        assump_ocf = pd.DataFrame(
            columns=pd.MultiIndex.from_product(
                [table.data.columns.unique('process'), ['ocf']],
                names=['process', 'type']
            ),
            index=[0],
            data=inputs['other_assump']['ocf']['default'],
        )
        assump_ocf['ELH2', 'ocf'] = inputs['other_assump']['ocf']['ELH2']

        # add assumptions to tables
        inputs['vc_tables'][comm] = table \
            .assume(assump_ocf) \
            .assume(assump_other)
