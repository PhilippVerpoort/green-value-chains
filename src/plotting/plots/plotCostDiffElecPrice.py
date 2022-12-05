import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plotCostDiffElecPrice(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict,
                          subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    plotData, elecPriceDiff = __adjustData(costData, costDataRef, prices, config) if subfigs_needed else None


    # produce figure
    ret['fig5'] = __produceFigure(plotData, elecPriceDiff, config) if 'fig5' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict):
    # cost delta of scenarios 2-4 in relation to scenario 1
    cost = costData \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costDelta = cost.query(r"(not route.str.endswith('Base Case')) and route.str.match(r'.*--.*$')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)) \
        .merge(cost.query("route.str.endswith('Base Case')").assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(cost=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # cost delta of scenarios 2-4 in relation to scenario 1 for reference with zero elec price difference
    costRef = costDataRef \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costRefDelta = costRef.query(r"(not route.str.endswith('Base Case')) and route.str.match(r'.*--.*$')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)) \
        .merge(costRef.query("route.str.endswith('Base Case')").assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(costRef=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # electricity price difference from prices object
    elecPriceDiff = prices \
        .query("component=='electricity' and location=='importer'").filter(['val_year', 'val']) \
        .merge(prices.query("component=='electricity' and location=='exporter'").filter(['val_year', 'val']), on=['val_year']) \
        .assign(priceDiff=lambda x: x.val_x - x.val_y) \
        .drop(columns=['val_x', 'val_y'])


    # linear interpolation of cost difference as a function of elec price
    tmp = costRefDelta \
        .merge(costDelta, on=['commodity', 'route', 'val_year']) \
        .merge(elecPriceDiff, on=['val_year'])

    plotData = pd.concat([
        tmp.assign(pd=pd, cd=lambda r: r.costRef + (r.cost-r.costRef)/r.priceDiff * pd)
        for pd in np.linspace(config['xrange'][0], config['xrange'][1], config['xsamples'])
    ]).drop(columns=['cost', 'costRef', 'priceDiff'])


    # sort by commodities
    commodityOrder = costData.commodity.unique().tolist()
    plotData.sort_values(by='commodity', key=lambda row: [commodityOrder.index(c) for c in row], inplace=True)


    return plotData, elecPriceDiff


def __produceFigure(plotData: dict, elecPriceDiff: pd.DataFrame, config: dict):
    commodities = plotData.commodity.unique().tolist()


    # create figure
    fig = make_subplots(
        cols=len(commodities),
        shared_yaxes=True,
        horizontal_spacing=0.01,
    )


    # plot lines
    for i, commodity in enumerate(commodities):
        commData = plotData.query(f"commodity=='{commodity}' and val_year=={config['showYear']}")
        defaultPriceDiff = elecPriceDiff.query(f"val_year=={config['showYear']}").iloc[0].priceDiff

        for route in plotData.route.unique():
            routeID = int(route[-1])
            thisData = commData.query(f"route=='{route}'")

            fig.add_trace(
                go.Scatter(
                    x=thisData.pd,
                    y=thisData.cd,
                    mode='lines',
                    name=f"Case {routeID}",
                    line=dict(color=config['line_colour'][routeID], width=config['global']['lw_default']),
                    showlegend=not i,
                    hovertemplate=f"<b>Case {routeID}</b><br>{config['xlabelshort']}: %{{x:.2f}}<br>{config['ylabelshort']}: %{{y:.2f}}<extra></extra>",
                ),
                col=i+1,
                row=1,
            )


        # add vertical line indicating default price assumption
        fig.add_vline(
            defaultPriceDiff,
            col=i+1,
            row=1,
            line_dash='dash',
        )


        # add text annotations explaining figure content
        fig.add_annotation(
            x=0.0,
            xref='x domain',
            xanchor='left',
            y=1.0,
            yref='y domain',
            yanchor='top',
            text=f"<b>{commodity}</b>",
            showarrow=False,
            bordercolor='black',
            borderwidth=2,
            borderpad=3,
            bgcolor='white',
            col=i+1,
            row=1,
        )


    # set axes labels
    fig.update_layout(
        legend_title='',
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        **{
            f"xaxis{i+1 if i else ''}": dict(title=f"{config['xaxislabel']}", range=config['xrange'])
            for i, commodity in enumerate(commodities)
        }
    )


    return fig
