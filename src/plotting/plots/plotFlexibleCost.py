import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plotFlexibleCost(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict,
                          subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    pd_samples, ocf_samples, plotData = __adjustData(costData, costDataRef, prices, config) if subfigs_needed else None


    # produce figure
    ret['fig4'] = __produceFigure(pd_samples, ocf_samples, plotData, config) if 'fig4' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict):
    # cost delta of scenarios 2-4 in relation to scenario 1
    cost = costData.query("type!='capital'") \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costDelta = cost.query("route.str.endswith('_4')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'_\d+$', '', regex=True)) \
        .merge(cost.query("route.str.endswith('_1')").assign(baseRoute=lambda x: x.route.str.replace(r'_\d+$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(cost=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # cost delta of scenarios 2-4 in relation to scenario 1 for reference with zero elec price difference
    costRef = costDataRef.query("type!='capital'") \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costRefDelta = costRef.query("route.str.endswith('_4')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'_\d+$', '', regex=True)) \
        .merge(costRef.query("route.str.endswith('_1')").assign(baseRoute=lambda x: x.route.str.replace(r'_\d+$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(costRef=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # capital cost data
    costCap = costData.query("type=='capital'") \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True) \
        .query("route.str.endswith('_4')") \
        .rename(columns={'val': 'costCap'})


    # electricity price difference from prices object
    elecPriceDiff = prices \
        .query("id=='price electricity'").filter(['val_year', 'val']) \
        .merge(prices.query("id=='price electricity exporter'").filter(['val_year', 'val']), on=['val_year']) \
        .assign(priceDiff=lambda x: x.val_x - x.val_y) \
        .drop(columns=['val_x', 'val_y'])


    # linear interpolation of cost difference as a function of elec price
    tmp = costRefDelta \
        .merge(costDelta, on=['commodity', 'route', 'val_year']) \
        .merge(costCap, on=['commodity', 'route', 'val_year']) \
        .merge(elecPriceDiff, on=['val_year'])

    pd_samples = np.linspace(config['xrange'][0], config['xrange'][1], config['samples'])
    ocf_samples = np.linspace(config['yrange'][0], config['yrange'][1], config['samples'])
    pd, ocf = np.meshgrid(pd_samples, ocf_samples)

    plotData = {}
    for index, row in tmp.iterrows():
        if row.val_year != config['showYear']: continue
        plotData[row.commodity] = row.costCap * (100.0/ocf - 1.0) + row.costRef + (row.cost - row.costRef) / row.priceDiff * pd


    return pd_samples, ocf_samples, plotData


def __produceFigure(pd_samples: np.ndarray, ocf_samples: np.ndarray, plotData: dict, config: dict):
    # create figure
    fig = make_subplots(
        cols=len(plotData),
        shared_yaxes=True,
        horizontal_spacing=0.025,
    )


    # plot lines
    for i, commodity in enumerate(plotData):
        tickvals = [100 * i for i in range(6)]
        ticktext = [str(v) for v in tickvals]

        fig.add_trace(
            go.Heatmap(
                x=pd_samples,
                y=ocf_samples,
                z=plotData[commodity],
                zsmooth='best',
                zmin=config['zrange'][0],
                zmax=config['zrange'][1],
                colorscale=[
                    [0.0, '#c6dbef'],
                    [1.0, '#f7bba1'],
                ],
                colorbar=dict(
                    x=1.05,
                    y=0.25,
                    len=0.5,
                    title='Cost difference (EUR/t)',
                    titleside='top',
                    tickvals=tickvals,
                    ticktext=ticktext,
                ),
                showscale=True,
                hoverinfo='skip',
            ),
            col=i+1,
            row=1,
        )

        fig.add_trace(
            go.Contour(
                x=pd_samples,
                y=ocf_samples,
                z=plotData[commodity],
                contours_coloring='lines',
                colorscale=[
                    [0.0, '#000000'],
                    [1.0, '#000000'],
                ],
                line_width=config['global']['lw_thin'],
                contours=dict(
                    showlabels=True,
                    start=config['zrange'][0],
                    end=config['zrange'][1],
                    size=config['zdelta'],
                ),
                showscale=False,
                hoverinfo='skip',
            ),
            col=i+1,
            row=1,
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
        yaxis=dict(title=config['yaxislabel'], range=config['yrange']),
        **{
            f"xaxis{i+1 if i else ''}": dict(title=f"{config['xaxislabel']}", range=config['xrange'])
            for i, commodity in enumerate(plotData)
        }
    )


    return fig
