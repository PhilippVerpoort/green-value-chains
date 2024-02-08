#!/usr/bin/env python
from pathlib import Path

import pint
from posted.units.units import ureg
from piw import Webapp
from dash.dependencies import Input, State
from dash import html

from src.ctrls import main_ctrl
from src.plots.LevelisedPlot import LevelisedPlot
from src.plots.ScenarioPlot import ScenarioPlot
from src.plots.SensitivityPlot import SensitivityPlot
from src.plots.TotalCostPlot import TotalCostPlot
from src.update import update_inputs
from src.utils import load_yaml_config_file
from src.load import load_data, load_posted, load_other
from src.proc import process_inputs


# make sure to always use correct units registry
pint.set_application_registry(ureg)


# metadata
metadata = {
    'title': 'Interactive webapp for techno-economic analysis of the renewables pull in future global green value '
             'chains',
    'abstract': 'This interactive webapp can be used to reproduce figures from an accompanying article by the same '
                'authors that studies the renewables pull and its impact on industrial relocation for future global '
                'green value chains of energy-intensive basic materials. The presented figures compare levelised '
                'production cost from techno-economic assessment for different depth of relocation for the green '
                'value chains of steel, urea, and ethylene.',
    'about': html.Div([
        html.P('This interactive webapp can be used to reproduce figures from an accompanying article by the same '
               'authors that studies the renewables pull and its impact on industrial relocation for future global '
               'green value chains of energy-intensive basic materials. Some of the main assumptions, i.e. the '
               'electricity prices and the transport cost can be changed here when generating the figures.'),
        html.P('We employ techno-economic assessments to compute the levelised cost of production for the studied '
               'green (i.e. low-carbon) value chains of steel, urea, and ethylene for cases of varying depth of '
               'relocation.'),
        html.P('The results show that substantial relocation savings for the levelised cost of production can be '
               'anticipated for full relocation of the studied value chains. Moreover, by studying cases of varying '
               'depth of relocation, we can demonstrate that a large share of the energy-cost savings is associated '
               'with relocating electrolysis to more renewable-favourable locations, yet the high transportation '
               'cost of shipping-based hydrogen imports result in only minor overall relocation savings.'),
        html.P('For more advanced changes and detailed information on the input data and methodology, we encourage '
               'users to inspect the article, its supplement, and the source code written in Python.'),
    ]),
    'authors': [
        {
            'first': 'Philipp C.',
            'last': 'Verpoort',
            'orcid': '0000-0003-1319-5006',
            'affiliation': ['Potsdam Institute for Climate Impact Research, Potsdam, Germany'],
        },
        {
            'first': 'Gast',
            'last': 'Lukas',
            'orcid': '0009-0003-1416-5199',
            'affiliation': ['Potsdam Institute for Climate Impact Research, Potsdam, Germany'],
        },
        {
            'first': 'Anke',
            'last': 'Hofmann',
            'orcid': '0009-0001-4837-3530',
            'affiliation': ['Potsdam Institute for Climate Impact Research, Potsdam, Germany'],
        },
        {
            'first': 'Falko',
            'last': 'Ueckerdt',
            'orcid': '0000-0001-5585-030X',
            'affiliation': ['Potsdam Institute for Climate Impact Research, Potsdam, Germany'],
        },
    ],
    'date': '2023-12-12',
    'version': 'v3.1.0',
    'doi': 'TBD',
    'license': {'name': 'CC BY 4.0', 'link': 'https://creativecommons.org/licenses/by/4.0/'},
    'citeas': 'Verpoort, Philipp C.; Gast, Lukas; Hofmann, Anke; Ueckerdt, Falko (2023): Interactive webapp for '
              'techno-economic analysis of the renewables pull in future global green value chains. V. 3.1.0. '
              'https://doi.org/TBD',
}


# define webapp
webapp = Webapp(
    piw_id='green-value-chains',
    metadata=metadata,
    pages={
        '': 'Main',
        'ext-data': 'Ext. Data Figs.',
    },
    load=[load_data, load_posted, load_other],
    ctrls=[main_ctrl],
    generate_args=[
        Input('simple-update', 'n_clicks'),
        State('simple-elec-prices', 'data'),
        State('simple-transp-cost', 'data'),
    ],
    update=[update_inputs],
    proc=[process_inputs],
    plots=[TotalCostPlot, LevelisedPlot, SensitivityPlot, ScenarioPlot],
    glob_cfg=load_yaml_config_file('global'),
    output=Path(__file__).parent / 'print',
    debug=False,
    input_caching=True,
)


# this will allow running the webapp locally
if __name__ == '__main__':
    webapp.start()
    webapp.run()
