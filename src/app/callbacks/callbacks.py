import copy

import dash
from dash.dependencies import Input, Output, State
from flask import send_file

from src.app.app import dash_app
from src.app.callbacks.update import updateScenarioInputSimple
from src.load.config_load_app import figNames, figs_cfg, allSubFigNames
from src.data.data import getFullData
from src.load.config_load import input_data, plots, default_assumptions
from src.load.filepaths import getFilePathAssets
from src.plotting.styling.webapp import addWebappSpecificStyling
from src.plotting.plot_all import plotAllFigs


# general callback for (re-)generating plots
@dash_app.callback(
    [*(Output(subFigName, 'figure') for subFigName in allSubFigNames),],
    [Input('simple-update', 'n_clicks'),
     State('plots-cfg', 'data'),
     State('simple-gwp', 'value'),
     State('simple-important-params', 'data'),])
def callbackUpdate(n1, plots_cfg: dict, simple_gwp: str, simple_important_params: list):
    ctx = dash.callback_context
    if not ctx.triggered:
        assumpts = copy.deepcopy(default_assumptions)
        fullCostData, costData = getFullData(input_data, assumpts)
    else:
        btnPressed = ctx.triggered[0]['prop_id'].split('.')[0]
        if btnPressed == 'simple-update':
            assumpts = updateScenarioInputSimple(simple_gwp, simple_important_params)
            fullCostData, costData = getFullData(input_data, assumpts)
        else:
            raise Exception('Unknown button pressed!')

    figs = plotAllFigs(fullCostData, costData, plots_cfg, global_cfg='webapp')

    addWebappSpecificStyling(figs)

    return *figs.values(),


# update figure plotting settings
@dash_app.callback(
    [Output('plot-config-modal', 'is_open'),
     Output('plots-cfg', 'data'),
     Output('plot-config-modal-textfield', 'value'),],
    [*(Input(f'{plotName}-settings', 'n_clicks') for plotName in plots),
     Input('plot-config-modal-ok', 'n_clicks'),
     Input('plot-config-modal-cancel', 'n_clicks'),],
    [State('plot-config-modal-textfield', 'value'),
     State('plots-cfg', 'data'),],
)
def callbackSettingsModal(n1: int, n_ok: int, n_cancel: int,
                          settings_modal_textfield: str, plots_cfg: dict):
    ctx = dash.callback_context
    if not ctx.triggered:
        plots_cfg['last_btn_pressed'] = None
        return False, plots_cfg, ''
    else:
        btnPressed = ctx.triggered[0]['prop_id'].split('.')[0]
        if btnPressed in [f"{cfgName}-settings" for cfgName in plots_cfg]:
            fname = btnPressed.split('-')[0]
            plots_cfg['last_btn_pressed'] = fname
            return True, plots_cfg, plots_cfg[fname]
        elif btnPressed == 'plot-config-modal-cancel':
            return False, plots_cfg, ''
        elif btnPressed == 'plot-config-modal-ok':
            fname = plots_cfg['last_btn_pressed']
            plots_cfg[fname] = settings_modal_textfield
            return False, plots_cfg, ''
        else:
            raise Exception('Unknown button pressed!')


# display of simple or advanced controls
@dash_app.callback(
    Output('simple-controls-card', 'style'),
    *(Output(f"card-{figName}", 'style') for figName in figNames),
    *(Output(f"{plotName}-settings-div", 'style') for plotName in plots),
    [Input('url', 'pathname')]
)
def callbackDisplayForRoutes(route):
    r = []

    r.append({'display': 'none'} if route != '/' else {})

    for figName in figNames:
        r.append({'display': 'none'} if route not in figs_cfg[figName]['display'] else {})

    for figName in figNames:
        r.append({'display': 'none'} if route != '/advanced' else {})

    return r


# serving asset files
@dash_app.server.route('/assets/<path>')
def callbackServeAssets(path):
    return send_file(getFilePathAssets(path), as_attachment=True)
