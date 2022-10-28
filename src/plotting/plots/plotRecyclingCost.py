import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plotRecyclingCost(costData: pd.DataFrame, costDataRec: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    plotData = __adjustData(costData, costDataRec, config) if subfigs_needed else None


    # produce figure
    ret['fig5'] = __produceFigure(plotData, config) if 'fig5' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, costDataRec: pd.DataFrame, config: dict):
    # cost delta of scenarios 2-4 in relation to scenario 1
    cost = costData \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costDelta = cost.query(r"(not route.str.endswith('Base Case')) and route.str.match(r'.*--.*$')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)) \
        .merge(cost.query("route.str.endswith('Base Case')").assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(cost=lambda x: x.val_y - x.val_x) \
        .merge(pd.DataFrame.from_records([{'commodity': 'Steel', 'sh': 0.1}, {'commodity': 'Urea', 'sh': 0.0}])) \
        .drop(columns=['val_x', 'val_y', 'baseRoute']) \
        .assign(route=lambda x: x.route.str.get(-1))


    # cost delta of scenarios 2-4 in relation to scenario 1 for reference with zero elec price difference
    costRec = costDataRec \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costRecDelta = costRec.query(r"(not route.str.endswith('Base Case')) and route.str.match(r'.*--.*$')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)) \
        .merge(costRec.query("route.str.endswith('Base Case')").assign(baseRoute=lambda x: x.route.str.replace(r'--.*$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(costRef=lambda x: x.val_y - x.val_x) \
        .merge(pd.DataFrame.from_records([{'commodity': 'Steel', 'shRef': 0.85}, {'commodity': 'Urea', 'shRef': 1.0}])) \
        .drop(columns=['val_x', 'val_y', 'baseRoute']) \
        .assign(route=lambda x: x.route.str.get(-1))



    # linear interpolation of cost difference as a function of elec price
    tmp = costRecDelta \
        .merge(costDelta, on=['commodity', 'route', 'val_year'])

    plotData = pd.concat([
        #tmp.assign(cd=lambda r: r.costRef + ((r.cost-r.costRef)/(r.sh-r.shRef)) * share, share=share)
        tmp.assign(cd=lambda r: r.cost + (r.costRef - r.cost) * (share - r.sh) / (r.shRef - r.sh), share=share)
        for share in np.linspace(config['xrange'][0], config['xrange'][1], config['xsamples'])
    ]).drop(columns=['cost', 'costRef', 'shRef'])


    return plotData


def __produceFigure(plotData: dict, config: dict):
    commodities = plotData.commodity.unique().tolist()+['Ethylene']


    # create figure
    fig = make_subplots(
        cols=len(commodities),
        shared_yaxes=True,
        horizontal_spacing=0.025,
    )


    # plot lines
    for i, commodity in enumerate(commodities):
        commData = plotData.query(f"commodity=='{commodity}'")

        for j, year in enumerate(plotData.val_year.unique()):
            yearData = commData.query(f"val_year=={year}")

            for route in plotData.route.unique():
                routeID = int(route)
                thisData = yearData.query(f"route=='{route}'")

                fig.add_trace(
                    go.Scatter(
                        x=thisData.share*100,
                        y=thisData.cd,
                        mode='lines',
                        name=int(year),
                        legendgroup=routeID,
                        legendgrouptitle=dict(text=f"<b>Case {routeID}</b>"),
                        line=dict(color=config['line_colour'][routeID], width=config['global']['lw_default'], dash='dot' if j else None),
                        showlegend=not i,
                        hovertemplate=f"<b>Case {routeID} in {int(year)}</b><br>Price difference: %{{x:.2f}}<br>Cost difference: %{{y:.2f}}<extra></extra>",
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
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        **{
            f"xaxis{i+1 if i else ''}": dict(title=f"{config['xaxislabel']}", range=config['xrange'])
            for i, commodity in enumerate(commodities)
        }
    )


    return fig
