import pandas as pd
import plotly.graph_objects as go

from src.plotting.styling.styling import defaultStyling


def plotLCOS(costData: pd.DataFrame, config: dict):
    # produce figure
    fig = __produceFigure(costData, config)

    # styling figure
    defaultStyling(fig)
    __styling(fig)

    return {'fig1': fig}


def __produceFigure(costData: pd.DataFrame, config: dict):
    # create figure
    fig = go.Figure()

    # prepare data
    #cond = costData.case.isin([1, 2, 3, 4])
    #costData.loc[cond, 'case'] = costData.loc[cond, 'case'].apply(lambda x: f"Case {x:.0f}")
    #casesArray = ['BF', 'NG', *(f"Case {i+1}" for i in range(4))]
    #casesOrder = ['BF', 'NG', *(f"Case {i + 1}" for i in range(4))]
    costData = costData.copy()
    costData.loc[(costData['type'] == 'feedstock') & costData['component'].isin(['ore', 'dri']), 'type'] = 'iron'

    # add dummy entries such that the order is correct
    routes = costData['route'].unique()
    years = costData['val_year'].unique()
    dummyData = pd.DataFrame.from_records([{'type': 'dummy', 'val_year': y, 'val': 0.0, 'route': r} for r in routes for y in years])
    fig.add_trace(go.Bar(
        x=[dummyData.val_year, dummyData.route],
        y=dummyData.val,
        showlegend=False,
    ))

    # add traces for all cost types
    keys = config['labels'].keys()
    for stack in keys:
        plotData = costData.query(f"type=='{stack}'")

        if not config['full_breakdown']:
            plotData = plotData.groupby(['type', 'val_year', 'route']).sum().reset_index()

        fig.add_trace(go.Bar(
            x=[plotData.val_year, plotData.route],
            y=plotData.val,
            marker_color=config['colours'][stack],
            name=config['labels'][stack],
            hovertemplate=f"<b>{config['labels'][stack]} (%{{x}})</b><br>Cost: %{{y}} EUR/t<extra></extra>",
        ))

    # add vertical line
    nYears = costData['val_year'].nunique()
    nRoutes = costData['route'].nunique()
    for i in range(nYears-1):
        fig.add_vline(nRoutes*(i+1)-0.5, line_width=0.5, line_color='black')
        fig.add_vline(nRoutes*(i+1)-0.5, line_width=0.5, line_color='black')

    # set axes labels
    fig.update_layout(
        barmode='stack',
        xaxis=dict(title=''),
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        legend_title=''
    )

    return fig


def __styling(fig: go.Figure):
    # update axis styling
    for axis in ['xaxis', 'yaxis']:
        update = {axis: dict(
            showline=True,
            linewidth=2,
            linecolor='black',
            showgrid=False,
            zeroline=False,
            mirror=True,
            ticks='outside',
        )}
        fig.update_layout(**update)
