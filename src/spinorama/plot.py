# -*- coding: utf-8 -*-
# A library to display spinorama charts
#
# Copyright (C) 2020-2023 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import bisect
import itertools
import math
from typing import TypeVar
import warnings

import numpy as np
import pandas as pd
from scipy import stats

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

from spinorama import logger
from spinorama.constant_paths import MIDRANGE_MIN_FREQ, MIDRANGE_MAX_FREQ
from spinorama.filter_peq import peq_spl
from spinorama.compute_misc import compute_contour
from spinorama.load_misc import sort_angles


pio.templates.default = "plotly_white"


# ratio is 4x3
plot_params_default: dict[str, int | str] = {
    "xmin": 20,
    "xmax": 20000,
    "ymin": -40,
    "ymax": 10,
    "width": 1200,
    "height": 800,
}

# ratio is 2x1
contour_params_default = {
    "xmin": 100,
    "xmax": 20000,
    "width": 1200,
    "height": 800,
}

# ratio is 4x5
radar_params_default = {
    "xmin": 400,
    "xmax": 20000,
    "width": 1000,
    "height": 1200,
}

colors = [
    "#5c77a5",
    "#dc842a",
    "#c85857",
    "#89b5b1",
    "#71a152",
    "#bab0ac",
    "#e15759",
    "#b07aa1",
    "#76b7b2",
    "#ff9da7",
]

uniform_colors = {
    # regression
    "Linear Regression": colors[0],
    "Band ±1.5dB": colors[1],
    "Band ±3dB": colors[1],
    # PIR
    "Estimated In-Room Response": colors[0],
    # spin
    "On Axis": colors[0],
    "Listening Window": colors[1],
    "Early Reflections": colors[2],
    "Sound Power": colors[3],
    "Early Reflections DI": colors[4],
    "Sound Power DI": colors[5],
    # reflections
    "Ceiling Bounce": colors[1],
    "Floor Bounce": colors[2],
    "Front Wall Bounce": colors[3],
    "Rear Wall Bounce": colors[4],
    "Side Wall Bounce": colors[5],
    #
    "Ceiling Reflection": colors[1],
    "Floor Reflection": colors[2],
    #
    "Front": colors[1],
    "Rear": colors[2],
    "Side": colors[3],
    #
    "Total Early Reflection": colors[7],
    "Total Horizontal Reflection": colors[8],
    "Total Vertical Reflection": colors[9],
    # SPL
    "10°": colors[1],
    "20°": colors[2],
    "30°": colors[3],
    "40°": colors[4],
    "50°": colors[5],
    "60°": colors[6],
    "70°": colors[7],
    #
    "500 Hz": colors[1],
    "1000 Hz": colors[2],
    "2000 Hz": colors[3],
    "10000 Hz": colors[4],
    "15000 Hz": colors[5],
}

label_short = {}

# label_short = {
#     # regression
#     "Linear Regression": "Reg",
#     "Band ±1.5dB": "±1.5dB",
#     "Band ±3dB": "±3dB",
#     # PIR
#     "Estimated In-Room Response": "PIR",
#     # spin
#     "On Axis": "ON",
#     "Listening Window": "LW",
#     "Early Reflections": "ER",
#     "Sound Power": "SP",
#     "Early Reflections DI": "ERDI",
#     "Sound Power DI": "SPDI",
#     # reflections
#     "Ceiling Bounce": "CB",
#     "Floor Bounce": "FB",
#     "Front Wall Bounce": "FWB",
#     "Rear Wall Bounce": "RWB",
#     "Side Wall Bounce": "SWB",
#     #
#     "Ceiling Reflection": "CR",
#     "Floor Reflection": "FR",
#     #
#     "Front": "F",
#     "Rear": "R",
#     "Side": "S",
#     #
#     "Total Early Reflection": "TER",
#     "Total Horizontal Reflection": "THR",
#     "Total Vertical Reflection": "TVR",
# }


legend_rank = {
    "On Axis": 0,
    "10°": 10,
    "20°": 20,
    "30°": 30,
    "40°": 40,
    "50°": 50,
    "60°": 60,
    "70°": 70,
    "80°": 80,
    "90°": 90,
    "-10°": -10,
    "-20°": -20,
    "-30°": -30,
    "-40°": -40,
    "-50°": -50,
    "-60°": -60,
    "-70°": -70,
    "-80°": -80,
    "-90°": -90,
}


def generate_xaxis(freq_min=20, freq_max=20000):
    return dict(
        title_text="Frequency (Hz)",
        type="log",
        range=[math.log10(freq_min), math.log10(freq_max)],
        showline=True,
        dtick="D1",
    )


def generate_yaxis_spl(range_min=-40, range_max=10, range_step=1):
    return dict(
        title_text="SPL (dB)",
        range=[range_min, range_max],
        dtick=range_step,
        tickvals=list(range(range_min, range_max + range_step, range_step)),
        ticktext=[
            "{}".format(i) if not i % 5 else " "
            for i in range(range_min, range_max + range_step, range_step)
        ],
        showline=True,
    )


def generate_yaxis_di(range_min=-5, range_max=45, range_step=5):
    tickvals = list(range(range_min, range_max, range_step))
    ticktext = [
        f"{di}" if pos < 5 else "" for pos, di in enumerate(range(range_min, range_max, range_step))
    ]
    # print('DEBUG {} {}'.format(tickvals, ticktext))
    return dict(
        title_text="DI (dB)                                                    &nbsp;",
        range=[range_min, range_max],
        dtick=range_step,
        tickvals=tickvals,
        ticktext=ticktext,
        showline=True,
    )


def generate_yaxis_angles(angle_min=-180, angle_max=180, angle_step=30):
    return dict(
        title_text="Angle",
        range=[angle_min, angle_max],
        dtick=angle_step,
        tickvals=list(range(angle_min, angle_max + angle_step, angle_step)),
        ticktext=["{}°".format(v) for v in range(angle_min, angle_max + angle_step, angle_step)],
        showline=True,
    )


def common_layout(params):
    orientation = "v"
    if params.get("layout", "") == "compact":
        orientation = "h"

    return dict(
        width=params["width"],
        height=params["height"],
        title=dict(
            x=0.5,
            y=0.99,
            xanchor="center",
            yanchor="top",
        ),
        legend=dict(
            x=0.5,
            y=1.12,  # TODO understand why it needs to be larger than 1
            xanchor="center",
            yanchor="top",
            orientation=orientation,
        ),
        margin={
            "t": 100,
            "b": 10,
            "l": 10,
            "r": 10,
        },
    )


def contour_layout(params):
    orientation = "v"
    if params.get("layout", "") == "compact":
        orientation = "h"

    return dict(
        width=params["width"],
        height=params["height"],
        legend=dict(x=0.5, y=0.95, xanchor="center", orientation=orientation),
        title=dict(
            x=0.5,
            y=0.99,
            xanchor="center",
            yanchor="top",
        ),
        margin={
            "t": 40,
            "b": 10,
            "l": 10,
            "r": 10,
        },
        font=dict(
            size=9,
        ),
    )


def radar_layout(params):
    orientation = "v"
    if params.get("layout", "") == "compact":
        orientation = "h"

    return dict(
        width=params["width"],
        height=params["height"],
        legend=dict(
            x=0.5,
            y=1.05,
            xanchor="center",
            orientation=orientation,
            title=dict(
                font=dict(
                    size=10,
                ),
            ),
            font=dict(
                size=9,
            ),
        ),
        title=dict(
            x=0.5,
            y=0.98,
            xanchor="center",
            yanchor="top",
        ),
        margin={
            "t": 100,
            "b": 0,
            "l": 50,
            "r": 50,
        },
    )


def plot_spinorama_traces(spin, params):
    layout = params.get("layout", "")
    traces = []
    for measurement in (
        "On Axis",
        "Listening Window",
        "Early Reflections",
        "Sound Power",
    ):
        if measurement not in spin.keys():
            continue
        trace = go.Scatter(
            x=spin.Freq,
            y=spin[measurement],
            marker_color=uniform_colors.get(measurement, "black"),
            name=label_short.get(measurement, measurement),
            hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
        )
        if layout != "compact":
            trace.name = measurement
            trace.legendgroup = "measurements"
            trace.legendgrouptitle = {"text": "Measurements"}
        traces.append(trace)

    traces_di = []
    for measurement in ("Early Reflections DI", "Sound Power DI"):
        if measurement not in spin.keys():
            continue
        trace = go.Scatter(
            x=spin.Freq,
            y=spin[measurement],
            marker_color=uniform_colors.get(measurement, "black"),
            hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
        )
        if layout == "compact":
            trace.name = label_short.get(measurement, measurement)
        else:
            trace.name = measurement
            trace.legendgroup = "directivity"
            trace.legendgrouptitle = {"text": "Directivity"}
        traces_di.append(trace)
    return traces, traces_di


def plot_spinorama(spin, params):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    t_max = 0
    traces, traces_di = plot_spinorama_traces(spin, params)
    for t in traces:
        t_max = max(t_max, np.max(t.y[np.where(t.x < 20000)]))
        fig.add_trace(t, secondary_y=False)

    t_max = 5 + int(t_max / 5) * 5
    t_min = t_max - 50
    # print('T min={} max={}'.format(t_min, t_max))

    di_max = 0
    for t in traces_di:
        di_max = max(di_max, np.max(t.y[np.where(t.x < 20000)]))
        fig.add_trace(t, secondary_y=True)

    di_max = 35 + int(di_max / 5) * 5
    di_min = di_max - 50
    # print('DI min={} max={}'.format(di_min, di_max))

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(t_min, t_max, 5))
    fig.update_yaxes(generate_yaxis_di(di_min, di_max, 5), secondary_y=True)

    fig.update_layout(common_layout(params))
    return fig


def plot_graph(df, params):
    layout = params.get("layout", "")
    fig = go.Figure()
    for measurement in df:
        if measurement != "Freq":
            trace = go.Scatter(
                x=df.Freq,
                y=df[measurement],
                hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
            )
            if layout == "compact":
                trace.name = label_short.get(measurement, measurement)
            else:
                trace.name = measurement
                trace.legendgroup = "measurements"
                trace.legendgrouptitle = {"text": "Measurements"}
            if measurement in uniform_colors:
                trace.marker = {"color": uniform_colors[measurement]}
            if measurement in legend_rank:
                trace.legendrank = legend_rank[measurement]
            fig.add_trace(trace)

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))
    fig.update_layout(common_layout(params))
    return fig


def plot_graph_spl(df, params):
    layout = params.get("layout", "")
    fig = go.Figure()
    for measurement in df:
        if measurement != "Freq":
            visible = None
            if measurement in ("On Axis", "10°", "20°", "30°", "40°", "50°", "60°"):
                visible = True
            elif measurement in ("-10°", "-20°", "-30°", "-40°", "-50°", "-60°"):
                visible = "legendonly"
            else:
                continue
            trace = go.Scatter(
                x=df.Freq,
                y=df[measurement],
                hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
                visible=visible,
                showlegend=True,
                legendrank=legend_rank[measurement],
            )
            if layout == "compact":
                trace.name = label_short.get(measurement, measurement)
            else:
                trace.name = measurement
                trace.legendgroup = "measurements"
                trace.legendgrouptitle = {"text": "Measurements"}
            if measurement in uniform_colors:
                trace.marker = {"color": uniform_colors[measurement]}
            if measurement in legend_rank:
                trace.legendrank = legend_rank[measurement]
            fig.add_trace(trace)

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))
    fig.update_layout(common_layout(params))
    return fig


def plot_graph_traces(df, measurement, params, slope, intercept, line_title):
    layout = params.get("layout", "")
    traces = []
    # some speakers start very high
    restricted_freq = df.loc[(df.Freq >= MIDRANGE_MIN_FREQ) & (df.Freq <= MIDRANGE_MAX_FREQ)]

    restricted_line = [slope * math.log10(f) + intercept for f in restricted_freq.Freq]
    line = [slope * math.log10(f) + intercept for f in df.Freq]

    # 600 px = 50 dB
    height = params["height"]
    one_db = (height - 150) / 50

    # add 3 dBs zone
    traces.append(
        go.Scatter(
            x=df.Freq,
            y=line,
            line=dict(width=6 * one_db, color="#E4FC5B"),
            opacity=0.4,
            name="Band ±3dB",
        )
    )
    # add 1.5 dBs zone
    traces.append(
        go.Scatter(
            x=df.Freq,
            y=line,
            line=dict(width=3 * one_db, color="#E4FC5B"),
            opacity=0.7,
            name="Band ±1.5dB",
        )
    )
    # add line
    showlegend = True
    if line_title is None:
        showlegend = False
    traces.append(
        go.Scatter(
            x=df.Freq,
            y=line,
            line=dict(width=2, color="black", dash="dot"),
            opacity=1,
            showlegend=showlegend,
            name=line_title,
        )
    )

    # add -3/+3 lines
    offset = 3  # math.sqrt(3*3+slope*slope)
    traces.append(
        go.Scatter(
            x=restricted_freq.Freq,
            y=np.array(restricted_line) + offset,
            line=dict(width=2, color="black", dash="dash"),
            opacity=1,
            showlegend=False,
        )
    )
    traces.append(
        go.Scatter(
            x=restricted_freq.Freq,
            y=np.array(restricted_line) - offset,
            line=dict(width=2, color="black", dash="dash"),
            opacity=1,
            showlegend=False,
        )
    )

    trace = go.Scatter(
        x=df.Freq,
        y=df[measurement],
        marker_color=uniform_colors.get(measurement, "black"),
        opacity=1,
        hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
    )
    if layout == "compact":
        trace.name = label_short.get(measurement, measurement)
    else:
        trace.name = measurement
        trace.legendgroup = "measurements"
        trace.legendgrouptitle = {"text": "Measurements"}
    traces.append(trace)

    return traces


def plot_graph_flat_traces(df, measurement, params):
    restricted_freq = df.loc[(df.Freq >= MIDRANGE_MIN_FREQ) & (df.Freq <= MIDRANGE_MAX_FREQ)]
    slope = 0
    intercept = (
        np.mean(restricted_freq[measurement]) if not restricted_freq[measurement].empty else 0.0
    )

    return plot_graph_traces(df, measurement, params, slope, intercept, None)


def plot_graph_regression_traces(df, measurement, params):
    restricted_freq = df.loc[(df.Freq >= MIDRANGE_MIN_FREQ) & (df.Freq <= MIDRANGE_MAX_FREQ)]
    slope, intercept, _, _, _ = stats.linregress(
        x=np.log10(restricted_freq["Freq"]), y=restricted_freq[measurement]
    )

    return plot_graph_traces(
        df, measurement, params, slope, intercept, "Linear Regression (midrange)"
    )


def plot_graph_flat(df, measurement, params):
    params.get("layout", "")
    # print("{} {}".format(measurement, df.keys()))
    fig = go.Figure()
    traces = plot_graph_flat_traces(df, measurement, params)
    for t in traces:
        fig.add_trace(t)

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))

    fig.update_layout(common_layout(params))
    return fig


def plot_graph_regression(df, measurement, params):
    params.get("layout", "")
    # print("{} {}".format(measurement, df.keys()))
    fig = go.Figure()
    traces = plot_graph_regression_traces(df, measurement, params)
    for t in traces:
        fig.add_trace(t)

    fig.update_xaxes(generate_xaxis())
    fig.update_yaxes(generate_yaxis_spl(params["ymin"], params["ymax"]))

    fig.update_layout(common_layout(params))
    return fig


T = TypeVar("T")


def flatten(l: list[list[T | None]]) -> list[T | None]:
    return list(itertools.chain.from_iterable(l))


def plot_contour(spl, params):
    df_spl = spl.copy()
    params.get("layout", "")
    min_freq = params.get("contour_min_freq", 100)

    contour_start = -30
    contour_end = 3

    contour_colorscale = [
        [0, "rgb(0,0,168)"],
        [0.1, "rgb(0,0,200)"],
        [0.2, "rgb(0,74,255)"],
        [0.3, "rgb(0,152,255)"],
        [0.4, "rgb(74,255,161)"],
        [0.5, "rgb(161,255,74)"],
        [0.6, "rgb(255,255,0)"],
        [0.7, "rgb(234,159,0)"],
        [0.8, "rgb(255,74,0)"],
        [0.9, "rgb(222,74,0)"],
        [1, "rgb(253,14,13)"],
    ]

    fig = go.Figure()

    af, am, az = compute_contour(df_spl.loc[df_spl.Freq > min_freq])
    az = np.clip(az, contour_start, contour_end)
    fig.add_trace(
        go.Contour(
            x=af[0],
            y=am.T[0],
            z=az,
            zmin=contour_start,
            zmax=contour_end,
            contours=dict(
                coloring="fill",
                start=contour_start + 0,
                end=contour_end - 0,
                size=3,
                showlines=True,
                # showlabels=True,
            ),
            colorbar=dict(
                dtick=3,
                len=1.0,
                lenmode="fraction",
            ),
            autocolorscale=False,
            colorscale=contour_colorscale,
            hovertemplate="Freq: %{x:.0f}Hz<br>Angle: %{y:.0f}<br>SPL: %{z:.1f}dB<br>",
        )
    )

    def add_lines(x, y):
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                opacity=0.5,
                marker_color="white",
                line_width=1,
                showlegend=False,
            )
        )

    def compute_horizontal_lines(
        x_min: float, x_max: float, y_data: range
    ) -> tuple[list[float | None], list[int | None]]:
        x = [x_min, x_max, None] * len(y_data)
        y = flatten([[a, a, None] for a in y_data])
        return x, y

    def compute_vertical_lines(
        y_min: int, y_max: int, x_data: list[int]
    ) -> tuple[list[int | None], list[float | None]]:
        x = flatten([[a, a, None] for a in x_data])
        y = [y_min, y_max, None] * len(x_data)
        return x, y

    hx, hy = compute_horizontal_lines(min_freq, 20000, range(-150, 180, 30))
    vrange = (
        [100 * i for i in range(2, 9)]
        + [1000 * i for i in range(1, 10)]
        + [10000 + 1000 * i for i in range(1, 9)]
    )
    vx, vy = compute_vertical_lines(-180, 180, vrange)

    add_lines(hx, hy)
    add_lines(vx, vy)

    fig.update_xaxes(generate_xaxis(min_freq))
    fig.update_yaxes(generate_yaxis_angles())
    fig.update_yaxes(
        zeroline=True,
        zerolinecolor="#000000",
        zerolinewidth=3,
    )
    fig.update_layout(contour_layout(params))
    return fig


def find_nearest_freq(dfu: pd.DataFrame, hz: float, tolerance: float = 0.05) -> int | None:
    """return the index of the nearest freq in dfu, return None if not found"""
    ihz = None
    for i in dfu.index:
        f = dfu.loc[i]
        if abs(f - hz) < hz * tolerance:
            ihz = i
            break
    if ihz:
        logger.debug("nearest: %.1f hz at loc %d", hz, ihz)
    return ihz


def plot_radar(spl, params):
    layout = params.get("layout", "")

    anglelist = list(range(-180, 180, 10))

    def projection(anglelist, grid_z, hz):
        dbs_r = [db for a, db in zip(anglelist, grid_z, strict=False)]
        dbs_theta = [a for a, db in zip(anglelist, grid_z, strict=False)]
        dbs_r.append(dbs_r[0])
        dbs_theta.append(dbs_theta[0])
        return dbs_r, dbs_theta, [hz for i in range(0, len(dbs_r))]

    def label(i):
        return "{:d} Hz".format(i)

    def plot_radar_freq(anglelist, freqlist, df):
        dfu = sort_angles(df)
        db_mean = dfu.loc[(dfu.Freq > 900) & (dfu.Freq < 1100)]["On Axis"].mean()
        freq = dfu.Freq
        dfu = dfu.drop("Freq", axis=1)
        db_min = np.min(dfu.min(axis=0).values)
        db_max = np.max(dfu.max(axis=0).values)
        max(abs(db_max), abs(db_min))
        # if df is normalized then 0 will be at the center of the radar which is not what
        # we want. Let's shift the whole graph up.
        # if db_mean < 45:
        #    dfu += db_scale
        # print(db_min, db_max, db_mean, db_scale)
        # build 3 plots
        db_x = []
        db_y = []
        hz_z = []
        for hz in freqlist:
            ihz = find_nearest_freq(freq, hz)
            if ihz is None:
                continue
            p_x, p_y, p_z = projection(anglelist, dfu.loc[ihz][dfu.columns != "Freq"], hz)
            # add to global variable
            db_x.append(p_x)
            db_y.append(p_y)
            hz_z.append(p_z)

        # normalise
        db_x = [v2 for v1 in db_x for v2 in v1]
        db_y = [v2 for v1 in db_y for v2 in v1]
        # print("db_x min={} max={}".format(np.array(db_x).min(), np.array(db_x).max()))
        # print("db_y min={} max={}".format(np.array(db_y).min(), np.array(db_y).max()))

        hz_z = [label(i2) for i1 in hz_z for i2 in i1]

        return db_mean, pd.DataFrame({"R": db_x, "Theta": db_y, "Freq": hz_z})

    fig = make_subplots(
        rows=2,
        cols=2,
        specs=[
            [{"type": "polar"}, {"type": "polar"}],
            [{"type": "polar"}, {"type": "polar"}],
        ],
        horizontal_spacing=0.15,
        vertical_spacing=0.05,
    )

    radialaxis = dict(
        range=[-45, 5],
        dtick=5,
        tickfont=dict(
            size=10,
        ),
    )
    angularaxis = dict(
        dtick=10,
        tickvals=list(range(0, 360, 10)),
        ticktext=[
            f"{x}°" if abs(x) < 60 or not x % 30 else " "
            for x in (list(range(0, 190, 10)) + list(range(-170, 0, 10)))
        ],
        tickfont=dict(
            size=10,
        ),
    )

    radar_colors = {
        "100 Hz": colors[0],
        "125 Hz": colors[1],
        "160 Hz": colors[2],
        "200 Hz": colors[3],
        "250 Hz": colors[4],
        "315 Hz": colors[5],
        "400 Hz": colors[6],
        "500 Hz": colors[7],
        "1600 Hz": colors[8],
        "2000 Hz": colors[9],
        "2500 Hz": colors[0],
        "3150 Hz": colors[1],
        "4000 Hz": colors[2],
        "5000 Hz": colors[3],
        "6000 Hz": colors[4],
        "8000 Hz": colors[5],
    }

    def update_pict(anglelist, freqlist, row, col, spl):
        _, dbs_df = plot_radar_freq(anglelist, freqlist, spl)

        for freq in np.unique(dbs_df["Freq"].values):
            mslice = dbs_df.loc[dbs_df.Freq == freq]
            trace = go.Scatterpolar(
                r=mslice.R,
                theta=mslice.Theta,
                dtheta=30,
                name=freq,
                marker_color=radar_colors.get(freq, "black"),
                legendrank=int(freq[:-3]),
            )
            if layout != "compact":
                trace.legendgroup = ("measurements",)
                trace.legendgrouptitle_text = ("Frequencies",)
            fig.add_trace(trace, row=row, col=col)
            fig.update_polars(radialaxis=radialaxis, angularaxis=angularaxis, row=row, col=col)

    update_pict(anglelist, [100, 125, 160, 200], 1, 1, spl)
    update_pict(anglelist, [1600, 2000, 2500, 3150], 1, 2, spl)
    update_pict(anglelist, [250, 315, 400, 500], 2, 1, spl)
    update_pict(anglelist, [4000, 5000, 6300, 8000], 2, 2, spl)

    fig.update_layout(radar_layout(params))
    # fig.update_layout(polar=dict(radialaxis=radialaxis, angularaxis=angularaxis)), row=row, col=col)

    return fig


def plot_image(df, params):
    return None


def plot_summary(df, summary, params):
    return None


def plot_eqs(freq, peqs, names):
    peqs_spl = [peq_spl(freq, peq) for peq in peqs]
    if len(peqs) > 1:
        freq_min = bisect.bisect_right(freq, 80)
        freq_max = bisect.bisect_left(freq, 3000)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            if freq_min < freq_max:
                peqs_restriced = [np.array(spl)[freq_min:freq_max] for spl in peqs_spl]
                peqs_avg = [np.mean(v) if len(v) > 0 else 0.0 for v in peqs_restriced]
                peqs_spl = [
                    np.array(spl) - (peqs_avg[i] - peqs_avg[0]) for i, spl in enumerate(peqs_spl)
                ]
    traces = None
    if names is None:
        traces = [go.Scatter(x=freq, y=spl) for spl in peqs_spl]
    else:
        traces = [
            go.Scatter(
                x=freq,
                y=spl,
                name=name,
                hovertemplate="Freq: %{x:.0f}Hz<br>SPL: %{y:.1f}dB<br>",
            )
            for spl, name in zip(peqs_spl, names, strict=False)
        ]
    fig = go.Figure(data=traces)
    fig.update_xaxes(
        dict(
            title_text="Frequency (Hz)",
            type="log",
            range=[math.log10(20), math.log10(20000)],
            showline=True,
            dtick="D1",
        ),
    )
    fig.update_yaxes(
        dict(
            title_text="SPL (dB)",
            range=[-5, 5],
            showline=True,
            dtick="D1",
        ),
    )
    fig.update_layout(
        title="EQs",
        width=600,
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            xanchor="center",
            y=1.1,
            x=0.5,
            title=None,
            font=dict(size=12),
        ),
    )
    return fig


def plot_contour_3d(spl, params):
    params.get("layout", "")
    min_freq = max(20, params.get("contour_min_freq", 100))

    contour_start = -30
    contour_end = 3

    contour_colorscale = [
        [0, "rgb(0,0,168)"],
        [0.1, "rgb(0,0,200)"],
        [0.2, "rgb(0,74,255)"],
        [0.3, "rgb(0,152,255)"],
        [0.4, "rgb(74,255,161)"],
        [0.5, "rgb(161,255,74)"],
        [0.6, "rgb(255,255,0)"],
        [0.7, "rgb(234,159,0)"],
        [0.8, "rgb(255,74,0)"],
        [0.9, "rgb(222,74,0)"],
        [1, "rgb(253,14,13)"],
    ]

    colorbar = dict(
        dtick=3,
        len=0.5,
        lenmode="fraction",
        tickfont=dict(size=14),
    )

    angle_list_3d = [-180, -150, -120, -90, -60, -30, 0, 30, 60, 90, 120, 150, 180]
    angle_text_3d = [f"{a}°" for a in angle_list_3d]
    spl_list_3d = [0, -5, -10, -15, -20, -25, -30, -35, -40, -45]
    spl_text_3d = [f"{s}" if s > -45 else "" for s in spl_list_3d]

    def a2v(angle):
        if angle == "Freq":
            return -1000
        elif angle == "On Axis":
            return 0
        iangle = int(angle[:-1])
        return iangle

    def transform(spl, db_max, clip_min, clip_max):
        if "-180°" not in spl and "180°" in spl:
            spl["-180°"] = spl["180°"]
        df_spl = spl.reindex(columns=sorted(spl.columns, key=lambda a: a2v(a))) - db_max
        # x,y,z
        freq = df_spl.Freq
        angle = [a2v(i) for i in df_spl.loc[:, df_spl.columns != "Freq"].columns]
        selector = (df_spl["Freq"] > min_freq) & (df_spl["Freq"] < 20000)
        spl = df_spl.loc[selector, df_spl.columns != "Freq"].T.to_numpy()
        # color
        color = np.clip(np.multiply(np.floor_divide(spl, 3), 3), clip_min, clip_max)
        return freq, angle, spl, color

    db_max = spl["On Axis"].max()

    freqs, angles, spls, colors = transform(spl, db_max, contour_start, contour_end)

    fig = go.Figure()

    trace = go.Surface(
        x=freqs,
        y=angles,
        z=spls,
        showscale=True,
        autocolorscale=False,
        colorscale=contour_colorscale,
        surfacecolor=colors,
        colorbar=colorbar,
        cmin=contour_start,
        cmax=contour_end,
        hovertemplate="Freq: %{x:.0f}Hz<br>Angle:  %{y}°<br> SPL: %{z:.1f}dB<br>",
    )

    fig.add_trace(trace)

    fig.update_layout(
        autosize=False,
        width=600,
        height=700,
        scene=dict(
            xaxis=dict(
                title="Freq. (Hz)",
                tickfont=dict(
                    size=11,
                ),
                titlefont=dict(
                    size=14,
                ),
            ),
            yaxis=dict(
                range=[-180, 180],
                showline=True,
                tickvals=angle_list_3d,
                ticktext=angle_text_3d,
                title="Angle",
                tickfont=dict(
                    size=11,
                ),
                titlefont=dict(
                    size=14,
                ),
            ),
            zaxis=dict(
                range=[-45, 5],
                title="SPL",
                showline=True,
                tickvals=spl_list_3d,
                ticktext=spl_text_3d,
                tickfont=dict(
                    size=11,
                ),
                titlefont=dict(
                    size=14,
                ),
            ),
        ),
    )
    fig.update_traces(contours_z=dict(show=True, project_z=True))

    return fig
