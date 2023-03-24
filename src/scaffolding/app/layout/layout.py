from dash import dcc, html

from src.scaffolding.app.layout.modals.advanced_modal import getModalUpdateAdvancedTable
from src.scaffolding.app.layout.modals.plot_settings_modal import getModalPlotConfig
from src.scaffolding.app.layout.elements.figures import getFigures
from src.scaffolding.app.layout.elements.simple import getElementSimpleControlsCard
from src.scaffolding.app.layout.elements.summary import getElementSummaryCard
from src.scaffolding.file.load_config import plot_cfgs, app_cfg


def getLayout(logo_url: str):
    return html.Div(
        id='app-container',

        # banner
        children=[
            html.Div(
                id='banner',
                className='banner',
                children=[
                    html.Div(
                        children=[
                            html.A(
                                html.Img(src=logo_url),
                                href='https://www.pik-potsdam.de/',
                            ),
                            html.Div(
                                html.B(app_cfg['title']),
                                className='app-title',
                            ),
                            html.Div(
                                dcc.Link(
                                    'Simple',
                                    href='/',
                                    className='mainlink',
                                ),
                                className='app-modes',
                            ),
                            html.Div(
                                dcc.Link(
                                    'Advanced',
                                    href='/advanced',
                                    className='mainlink',
                                ),
                                className='app-modes',
                            ),
                        ],
                        className='header-left-side',
                    ),
                    html.Div(
                        children=[
                            html.Div(
                                dcc.Link(
                                    'Impressum',
                                    href='https://interactive.pik-potsdam.de/impressum',
                                    className='mainlink',
                                ),
                            ),
                            html.Div(
                                dcc.Link(
                                    'Accessibility',
                                    href='https://interactive.pik-potsdam.de/accessibility',
                                    className='mainlink',
                                ),
                            ),
                            html.Div(
                                dcc.Link(
                                    'Privacy policy',
                                    href='https://interactive.pik-potsdam.de/privacy-policy',
                                    className='mainlink',
                                ),
                            ),
                        ],
                        className='header-right-side',
                    ),
                ],
            ),

            # left column
            html.Div(
                id='left-column',
                className='four columns',
                children=[getElementSummaryCard(), getElementSimpleControlsCard()]
            ),

            # right column
            html.Div(
                id='right-column',
                className='eight columns',
                children=getFigures(),
            ),

            # modals
            getModalPlotConfig(),
            getModalUpdateAdvancedTable(),

            # dcc locations, stores, and downloads
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='plot-cfgs', storage_type='memory', data=plot_cfgs),
            dcc.Download(id='download-config-yaml'),
            dcc.Download(id='download-results-xlsx'),
        ],
    )
