import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plotCostDiffH2Transp(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame,
                         costH2Transp: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    pd_samples, tc_samples, plotData = __adjustData(costData, costDataRef, prices, costH2Transp, config) if subfigs_needed else None


    # produce figure
    ret['fig6'] = __produceFigure(pd_samples, tc_samples, plotData, config) if 'fig6' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, costH2TranspBase: pd.DataFrame, config: dict):
    # transportation cost for hydrogen
    costH2Transp = costData \
        .query("type=='transport' and component=='hydrogen'") \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True) \
        .assign(costH2Transp=lambda x: x.val) \
        .drop(columns=['val'])


    # cost delta of Cases 1-3 in relation to Base Case without H2 transport cost
    cost = costData \
        .query("not (type=='transport' and component=='hydrogen')") \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costDelta = cost.query(r"route.str.endswith('Case 1')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)) \
        .merge(cost.query("route.str.endswith('Base Case')").assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(cost=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # cost delta of Cases 1-3 in relation to Base Case without H2 transport cost for reference with zero elec price difference
    costRef = costDataRef \
        .query("not (type=='transport' and component=='hydrogen')") \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costRefDelta = costRef.query(r"route.str.endswith('Case 1')") \
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


    # base H2 transportation cost
    costH2TranspBase = costH2TranspBase \
        .assign(costH2TranspBase=lambda x: x.val) \
        .filter(['costH2TranspBase', 'val_year'])


    # linear interpolation of cost difference as a function of elec price
    tmp = costRefDelta \
        .merge(costDelta, on=['commodity', 'route', 'val_year']) \
        .merge(costH2Transp, on=['commodity', 'route', 'val_year']) \
        .merge(costH2TranspBase, on=['val_year']) \
        .merge(elecPriceDiff, on=['val_year'])

    pd_samples = np.linspace(config['xrange'][0], config['xrange'][1], config['samples'])
    tc_samples = np.linspace(config['yrange'][0], config['yrange'][1], config['samples'])
    pd, tc = np.meshgrid(pd_samples, tc_samples)

    plotData = {c: 0.0 for c in costData.commodity.unique().tolist()}
    for index, r in tmp.iterrows():
        if r.val_year != config['showYear']: continue
        plotData[r.commodity] = r.costRef + (r.cost-r.costRef)/r.priceDiff * pd - r.costH2Transp/r.costH2TranspBase * tc


    return pd_samples, tc_samples, plotData


def __produceFigure(pd_samples: np.ndarray, tc_samples: np.ndarray, plotData: dict, config: dict):
    # create figure
    fig = make_subplots(
        cols=len(plotData),
        shared_yaxes=True,
        horizontal_spacing=0.025,
    )


    # plot heatmaps and contours
    for i, commodity in enumerate(plotData):
        fig.add_trace(
            go.Heatmap(
                x=pd_samples,
                y=tc_samples,
                z=plotData[commodity],
                zsmooth='best',
                zmin=config['zrange'][0],
                zmax=config['zrange'][1],
                colorscale=[
                    [0.0, config['zcolours'][0]],
                    [1.0, config['zcolours'][1]],
                ],
                colorbar=dict(
                    x=1.02,
                    y=0.5,
                    len=0.8,
                    title=config['zaxislabel'],
                    titleside='right',
                    tickvals=[float(t) for t in config['zticks']],
                    ticktext=config['zticks'],
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
                y=tc_samples,
                z=plotData[commodity],
                contours_coloring='lines',
                colorscale=[
                    [0.0, '#000000'],
                    [1.0, '#000000'],
                ],
                line_width=config['global']['lw_thin'],
                contours=dict(
                    showlabels=True,
                    start=config['zrange2'][0],
                    end=config['zrange2'][1],
                    size=config['zdelta'][i],
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
        yaxis_title=config['yaxislabel'],
        xaxis2_title=f"{config['xaxislabel']}",
        **{
            f"xaxis{i+1 if i else ''}": dict(range=config['xrange'])
            for i, commodity in enumerate(plotData)
        },
        **{
            f"yaxis{i+1 if i else ''}": dict(range=config['yrange'])
            for i, commodity in enumerate(plotData)
        },
    )


    return fig
