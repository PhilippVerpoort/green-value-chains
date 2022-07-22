from dash import html, dcc

from src.load.load_config_plot import plots
from src.load.load_config_app import figs_cfg


def getFigures():
    figs = []
    for plotName in plots:
        if isinstance(plots[plotName], list):
            figs.extend([__getFigTemplate(fig, [fig], plotName, bool(i)) for i, fig in enumerate(plots[plotName])])
        elif isinstance(plots[plotName], dict):
            figs.extend([__getFigTemplate(fig, plots[plotName][fig], plotName, bool(i)) for i, fig in enumerate(plots[plotName])])
        else:
            raise Exception('Unknown figure type.')

    return figs


def __getFigTemplate(figName: str, subFigNames: list, plotName: str, showConfigButton: bool):
    figCfg = figs_cfg[figName]
    width = figCfg['width'] if 'width' in figCfg else '100%'
    height = figCfg['height'] if 'height' in figCfg else '450px'
    display = '/' in figCfg['display']

    return html.Div(
        id=f"card-{figName}",
        className='fig-card',
        children=[
            *(
                dcc.Loading(
                    children=[
                        dcc.Graph(
                            id=subFigName,
                            style={
                                'height': height,
                                'width': width,
                                'float': 'left',
                            },
                        ),
                    ],
                    type='circle',
                    style={
                        'height': height,
                        'width': width,
                        'float': 'left',
                    },
                )
                for subFigName in subFigNames
            ),
            html.Hr(),
            html.B(f"{figCfg['name']} | {figCfg['title']}"),
            html.P(figCfg['desc']),
            html.Div([
                    html.Hr(),
                    html.Button(id=f"{plotName}-settings", children='Config', n_clicks=0,),
                ],
                id=f"{plotName}-settings-div",
                style={'display': 'none'},
            ) if showConfigButton else None,
        ],
        style={} if display else {'display': 'none'},
    )
