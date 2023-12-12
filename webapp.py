#!/usr/bin/env python
from pathlib import Path

import pint
from posted.units.units import ureg
from piw import Webapp
from dash.dependencies import Input, State

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


# define webapp
webapp = Webapp(
    piw_id='green-value-chains',
    title='Future global green value chains: estimating the renewables pull and understanding its impact on '
          'industrial relocation',
    pages={
        '': 'Simple',
        'advanced': 'Advanced',
    },
    desc='This webapp reproduces results presented in an accompanying manuscript on estimations of the renewables pull '
         'in future global green value chains. It determines energy-cost savings and other relocation penalties for '
         'different import scenarios for the green value chains of steel, urea, and ethylene.',
    authors=['Philipp C. Verpoort', 'Lukas Gast', 'Anke Hofmann', 'Falko Ueckerdt'],
    date='25/03/2023',
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
