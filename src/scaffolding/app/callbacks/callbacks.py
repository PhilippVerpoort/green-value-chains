import dash
from dash.dependencies import Input, Output, State
from flask import send_file

from src.scaffolding.app.app import dash_app
from src.scaffolding.app.callbacks.init import figsDefault
from src.scaffolding.app.callbacks.update import updateScenarioInput
from src.scaffolding.file.load_config_app import figNames, figs_cfg, subfigsDisplayed, app_cfg
from src.scaffolding.data.data import getFullData
from src.scaffolding.file.load_config_plot import plots
from src.scaffolding.file.file_path import pathOfAssetsFile
from src.scaffolding.plotting.styling.webapp import addWebappSpecificStyling
from src.scaffolding.plotting.plot_all import plotAllFigs


# general callback for (re-)generating plots
@dash_app.callback(
    [*(Output(subfigName, 'figure') for subfigName in subfigsDisplayed),],
    [Input('simple-update', 'n_clicks'),
     State('url', 'pathname'),
     State('plots-cfg', 'data'),
     State('simple-important-params', 'data'),
     State('simple-electrolysis', 'value'),
     State('simple-gwp', 'value'),])
def callbackUpdate(n1, route: str, plots_cfg: dict, simple_important_params: list, simple_electrolysis: bool, simple_gwp: str):
    ctx = dash.callback_context

    if not ctx.triggered:
        print("Loading figures from default values")
        return *figsDefault.values(),
    else:
        btnPressed = ctx.triggered[0]['prop_id'].split('.')[0]
        if btnPressed == 'simple-update':
            inputDataUpdated =  updateScenarioInput(simple_important_params, simple_electrolysis, simple_gwp)
            outputData = getFullData(inputDataUpdated)
        else:
            raise Exception(f"Unknown button pressed: {btnPressed}")

    figsNeeded = [fig for fig, routes in app_cfg['figures'].items() if route in routes]
    figs = plotAllFigs(outputData, inputDataUpdated, plots_cfg, global_cfg='webapp', figs_needed=figsNeeded)

    addWebappSpecificStyling(figs)

    return *figs.values(),


# update figure plotting settings
settingsButtons = [plotName for plotName, figList in plots.items() if any(f in app_cfg['figures'] and not ('nosettings' in figs_cfg[f] and figs_cfg[f]['nosettings']) for f in figList)]
@dash_app.callback(
    [Output('plot-config-modal', 'is_open'),
     Output('plots-cfg', 'data'),
     Output('plot-config-modal-textfield', 'value'),],
    [*(Input(f'{plotName}-settings', 'n_clicks') for plotName in settingsButtons),
     Input('plot-config-modal-ok', 'n_clicks'),
     Input('plot-config-modal-cancel', 'n_clicks'),],
    [State('plot-config-modal-textfield', 'value'),
     State('plots-cfg', 'data'),],
)
def callbackSettingsModal(*args):
    settings_modal_textfield = args[-2]
    plots_cfg = args[-1]

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
    *(Output(f"card-{f}", 'style') for f in figNames if f in app_cfg['figures']),
    *(Output(f'{plotName}-settings-div', 'style') for plotName, figList in plots.items() if any(f in app_cfg['figures'] and not ('nosettings' in figs_cfg[f] and figs_cfg[f]['nosettings']) for f in figList)),
    [Input('url', 'pathname')]
)
def callbackDisplayForRoutes(route):
    r = []

    # display of figures for different routes
    for figName in figNames:
        if figName not in app_cfg['figures']: continue
        r.append({'display': 'none'} if route not in app_cfg['figures'][figName] else {})

    # display plot config buttons only on advanced
    for figName in figNames:
        if figName not in app_cfg['figures'] or  ('nosettings' in figs_cfg[figName] and figs_cfg[figName]['nosettings']): continue
        r.append({'display': 'none'} if route != '/advanced' else {})

    return r


# serving asset files
@dash_app.server.route('/assets/<path>')
def callbackServeAssets(path):
    return send_file(pathOfAssetsFile(path), as_attachment=True)
