import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.load.load_default_data import all_routes
from src.plotting.helperFuncs import groupbySumval


def plotTotalCost(costData: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    costDataAggregated = __adjustData(costData, config)


    # produce new fig3
    ret['fig3'] = __produceFigure(costDataAggregated, config) if 'fig3' in subfigs_needed else None


    return ret


# make adjustments to data (route names, component labels)
def __adjustData(costData: pd.DataFrame, config: dict):
    showRoutes = costData['route'].unique()
    showYears = costData['period'].unique()

    # remove upstream cost entries
    costDataNew = costData.copy().query(f"type!='upstream'")

    # define route names and ordering
    route_names_woimp = {route_id: route_vals['name'] for route_details in all_routes.values() for route_id, route_vals in sorted(route_details.items()) if route_id in costDataNew['route'].unique()}
    route_names_wiimp = {route_id: route_id.split('--')[-1] for route_id in costDataNew['route'].unique() if route_id not in route_names_woimp}
    route_names = {**route_names_woimp, **route_names_wiimp}

    # rename routes into something readable
    costDataNew.replace({'route': route_names}, inplace=True)

    # aggregate
    costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                ['period', 'commodity', 'route'], keep=['case'])

    # sort by commodities
    commodityOrder = costData.commodity.unique().tolist()
    costDataNew.sort_values(by='commodity', key=lambda row: [commodityOrder.index(c) for c in row], inplace=True)

    # add relative data
    costDataNewBase = groupbySumval(costDataNew.query(f"case=='Base Case'"), ['period', 'commodity'])
    costDataNew = costDataNew \
        .merge(costDataNewBase, on=['period', 'commodity']) \
        .assign(val=lambda x: x.val_x, val_rel=lambda x: x.val_x / x.val_y) \
        .drop(columns=['val_x', 'val_y'])


    # replace
    costDataNew = costDataNew \
        .replace({'route': 'Case 1A'}, 'Case 1A/B') \
        .replace({'route': 'Case 1B'}, 'Case 1A/B')


    return costDataNew


def __produceFigure(costData: pd.DataFrame, config: dict):
    q = f"period=={config['show_year']} & case.notnull()"
    costData = costData.query(q)
    subplots = costData.commodity.unique()
    # subplots = sorted(costData.case.unique())


    # create figure
    fig = make_subplots(
        cols=len(subplots),
        rows=2,
        horizontal_spacing=0.05,
    )


    # add scatter
    for i, comm in enumerate(costData.commodity.unique()):
        thisData = costData\
            .query(f"commodity=='{comm}' and case!='Case 1A'") \
            .sort_values(by='route')

        fig.add_trace(
            go.Scatter(
                x=thisData.route,
                y=100.0*thisData.val_rel,
                name=comm,
                marker=dict(
                    color=config['colour'][comm],
                    symbol=config['symbol'],
                    size=config['global']['marker_def'],
                    line_width=config['global']['lw_thin'],
                    line_color=config['colour'][comm],
                ),
                line=dict(
                    shape='spline',
                    #width=0.0 if not i else None,
                    dash='dash' if not i else 'solid',
                ),
                showlegend=True,
            ),
            row=1,
            col=i+1,
        )

        # add annotations
        fig.add_annotation(
            text=f"<b>{comm}</b>",
            x=0.5,
            xref='x domain',
            xanchor='center',
            y=1.0,
            yshift=50.0,
            yref='y domain',
            yanchor='bottom',
            showarrow=False,
            bordercolor='black',
            borderwidth=2,
            borderpad=3,
            bgcolor='white',
            row=1,
            col=i+1,
        )

    fig.update_xaxes(
        categoryorder='category ascending',
        #showticklabels=False,
    )


    # update layout
    fig.update_layout(
        barmode='stack',
        yaxis_title=config['yaxislabel'],
        yaxis_range=[0.0, 140.0],
        legend_title='',
    )


    return fig
