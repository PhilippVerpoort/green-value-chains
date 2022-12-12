import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.plotting.helperFuncs import groupbySumval


def plotRecyclingCost(costData: pd.DataFrame, costDataRec: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    plotData = __adjustData(costData, costDataRec, config) if subfigs_needed else None


    # produce figure
    ret['fig7'] = __produceFigure(plotData, config) if 'fig7' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, costDataRec: pd.DataFrame, config: dict):
    shares = [{'commodity': 'Steel', 'sh': 0.1}, {'commodity': 'Urea', 'sh': 0.0}, {'commodity': 'Ethylene', 'sh': 0.0}]
    sharesRec = [{'commodity': 'Steel', 'shRef': 0.85}, {'commodity': 'Urea', 'shRef': 1.0}, {'commodity': 'Ethylene', 'shRef': 1.0}]

    # cost delta of Cases 1-3 in relation to Base Case
    cost = groupbySumval(costData, ['commodity', 'route', 'val_year'], keep=['baseRoute', 'case'])

    costDelta = cost.query("case.notnull() & case!='Base Case'") \
        .merge(cost.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(cost=lambda x: x.val_y - x.val_x) \
        .merge(pd.DataFrame.from_records(shares)) \
        .drop(columns=['val_x', 'val_y', 'baseRoute', 'route'])


    # cost delta of Cases 1-3 in relation to Base Case for reference with recycling
    costRec = groupbySumval(costDataRec, ['commodity', 'route', 'val_year'], keep=['baseRoute', 'case'])

    costRecDelta = costRec.query("case.notnull() & case!='Base Case'") \
        .merge(costRec.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(costRef=lambda x: x.val_y - x.val_x) \
        .merge(pd.DataFrame.from_records(sharesRec)) \
        .drop(columns=['val_x', 'val_y', 'baseRoute', 'route'])


    # linear interpolation of cost difference as a function of elec price
    tmp = costRecDelta.merge(costDelta, on=['commodity', 'case', 'val_year'])

    plotData = pd.concat([
        #tmp.assign(cd=lambda r: r.costRef + ((r.cost-r.costRef)/(r.sh-r.shRef)) * share, share=share)
        tmp.assign(cd=lambda r: r.cost + (r.costRef - r.cost) * (share - r.sh) / (r.shRef - r.sh), share=share)
        for share in np.linspace(config['xrange'][0], config['xrange'][1], config['xsamples'])
    ]).drop(columns=['cost', 'costRef', 'shRef'])


    # sort by commodities
    commodityOrder = costData.commodity.unique().tolist()
    plotData.sort_values(by='commodity', key=lambda row: [commodityOrder.index(c) for c in row], inplace=True)


    return plotData


def __produceFigure(plotData: dict, config: dict):
    commodities = plotData.commodity.unique().tolist()


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

            for case in plotData.case.unique():
                thisData = yearData.query(f"case=='{case}'")

                if case == 'Case 1A':
                    continue

                fig.add_trace(
                    go.Scatter(
                        x=thisData.share*100,
                        y=thisData.cd,
                        mode='lines',
                        name=int(year),
                        legendgroup=case,
                        legendgrouptitle=dict(text=f"<b>{case}</b>"),
                        line=dict(color=config['line_colour'][case], width=config['global']['lw_default'], dash='dot' if j else None),
                        showlegend=not i,
                        hovertemplate=f"<b>{case} in {int(year)}</b><br>Price difference: %{{x:.2f}}<br>Cost difference: %{{y:.2f}}<extra></extra>",
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
