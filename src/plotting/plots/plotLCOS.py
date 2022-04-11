import pandas as pd
import plotly.graph_objects as go


def plotLCOS(costData: pd.DataFrame, config: dict):
    # produce figure
    fig = __produceFigure(costData, config)

    # styling figure
    __styling(fig)

    return {'fig1': fig}


def __produceFigure(costData: pd.DataFrame, config: dict):
    # create figure
    fig = go.Figure()

    # prepare data
    cond = costData.case.isin([1, 2, 3, 4])
    costData.loc[cond, 'case'] = costData.loc[cond, 'case'].apply(lambda x: f"Case {x:.0f}")
    casesArray = ['BF', 'NG', *(f"Case {i+1}" for i in range(4))]

    # add dummy entries such that the order is correct
    years = costData['year'].unique()
    dummyData = pd.DataFrame.from_records([{'type': 'dummy', 'year': y, 'val': 0.0, 'case': c, 'order': casesArray.index(c)} for c in casesArray for y in years])
    fig.add_trace(go.Bar(
        x=[dummyData.year, dummyData.case],
        y=dummyData.val,
        showlegend=False,
    ))

    # add traces for all cost types
    keys = config['labels'].keys()
    for stack in keys:
        plotData = costData.query(f"type=='{stack}'").groupby(['type', 'year', 'case']).sum().reset_index()
        fig.add_trace(go.Bar(
            x=[plotData.year, plotData.case],
            y=plotData.val,
            marker_color=config['colours'][stack],
            name=config['labels'][stack],
            hovertemplate=f"<b>{config['labels'][stack]} (%{{x}})</b><br>Cost: %{{y}} EUR/t<extra></extra>",
        ))

    # add vertical line
    nYears = costData['year'].nunique()
    nCases = costData['case'].nunique()
    for i in range(nYears-1):
        fig.add_vline(nCases*(i+1)-0.5, line_width=0.5, line_color='black')
        fig.add_vline(nCases*(i+1)-0.5, line_width=0.5, line_color='black')

    # set axes labels
    fig.update_layout(
        barmode='stack',
        xaxis=dict(title=''),
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        legend_title=''
    )

    return fig


def __styling(fig: go.Figure):
    # update legend styling
    fig.update_layout(
        legend=dict(
            bgcolor='rgba(255,255,255,1.0)',
            bordercolor='black',
            borderwidth=2,
        ),
    )


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


    # update figure background colour and font colour and type
    fig.update_layout(
        paper_bgcolor='rgba(255, 255, 255, 1.0)',
        plot_bgcolor='rgba(255, 255, 255, 0.0)',
        font_color='black',
        font_family='Helvetica',
    )
