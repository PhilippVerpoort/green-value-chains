import pandas as pd
import plotly.graph_objects as go

from src.scaffolding.plotting.AbstractPlot import AbstractPlot


class BasePlot(AbstractPlot):
    @staticmethod
    def _groupbySumval(df: pd.DataFrame, groupCols: list, keep: list = []):
        return df.groupby(groupCols) \
            .agg(dict(**{c: 'first' for c in groupCols + keep}, val='sum')) \
            .reset_index(drop=True)

    @staticmethod
    def _addAnnotationComm(fig: go.Figure, i: int, comm: str):
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


    @staticmethod
    def _updateAxisLayout(fig: go.Figure, i: int, xaxis: dict, yaxis: dict):
        fig.update_layout(**{
            f"xaxis{i + 1 if i else ''}": xaxis,
            f"yaxis{i + 1 if i else ''}": yaxis,
        })
