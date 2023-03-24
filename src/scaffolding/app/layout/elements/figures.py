from dash import html, dcc

from src.scaffolding.file.load_config import plots


def getFigures():
    cards = {}

    for plotName, plot in plots.items():
        for i, figName in enumerate(sorted(plot.getFigs())):
            figCard = __getFigTemplate(figName, plot.getFigSpecs(figName), plotName, not i)
            cards[figName] = figCard

    return list(dict(sorted(cards.items(), key=lambda t: t[0])).values())


def __getFigTemplate(figName: str, figSpecs: dict, plotName: str, hasSettings: bool):
    if 'subfigs' in figSpecs:
        sfs = [
            (subfigName, subfigSpecs['webapp']['height'], subfigSpecs['webapp']['width'])
             for subfigName, subfigSpecs in figSpecs['subfigs'].items()
        ]
    else:
        sfs = [(figName, figSpecs['sizes']['webapp']['height'], figSpecs['sizes']['webapp']['width'])]

    displayDefault = '/' in figSpecs['display']

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
                                'height': subFigHeight,
                                'width': f"{subFigWidth}%",
                                'float': 'left',
                            },
                        ),
                    ],
                    type='circle',
                    style={
                        'height': subFigHeight,
                        'width': f"{subFigWidth}%",
                        'float': 'left',
                    },
                )
                for subFigName, subFigHeight, subFigWidth in sfs
            ),
            html.Hr(),
            html.B(f"{figSpecs['name']} | {figSpecs['title']}"),
            html.P(figSpecs['desc']),
            (html.Div([
                    html.Hr(),
                    html.Button(id=f"{plotName}-settings", children='Config', n_clicks=0,),
                ],
                id=f"{plotName}-settings-div",
                style={'display': 'none'},
            ) if hasSettings else None),
        ],
        style={} if displayDefault else {'display': 'none'},
    )
