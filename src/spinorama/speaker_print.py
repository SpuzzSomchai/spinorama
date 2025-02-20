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

import os
import pathlib
import copy
import pandas as pd

try:
    import ray
except ModuleNotFoundError:
    import src.miniray as ray

from spinorama import logger, ray_setup_logger
from spinorama.constant_paths import CPATH_DOCS_SPEAKERS
from spinorama.pict import write_multiformat
from spinorama.speaker_display import (
    display_spinorama,
    display_onaxis,
    display_inroom,
    display_reflection_early,
    display_reflection_horizontal,
    display_reflection_vertical,
    display_spl_horizontal,
    display_spl_vertical,
    display_spl_horizontal_normalized,
    display_spl_vertical_normalized,
    display_contour_horizontal,
    display_contour_vertical,
    display_contour_horizontal_normalized,
    display_contour_vertical_normalized,
    display_contour_horizontal_3d,
    display_contour_vertical_3d,
    display_contour_horizontal_normalized_3d,
    display_contour_vertical_normalized_3d,
    display_radar_horizontal,
    display_radar_vertical,
)
from spinorama.plot import plot_params_default, contour_params_default, radar_params_default


def build_filename(speaker, origin, key, title, file_ext) -> str:
    filedir = CPATH_DOCS_SPEAKERS + "/" + speaker + "/" + origin.replace("Vendors-", "") + "/" + key
    pathlib.Path(filedir).mkdir(parents=True, exist_ok=True)
    filename = filedir + "/" + title.replace("_smoothed", "")
    if file_ext == "png":
        filename += "_large"
    filename += "." + file_ext
    return filename


def build_title(origin: str, version: str, speaker: str, title: str) -> str:
    whom = origin
    if origin[0:7] == "Vendors-":
        whom = origin.replace("Vendors-", "")
    elif origin == "Misc":
        if version[-3:] == "-sr":
            whom = "Sound & Recording (data scanned)"
        elif version[-3:] == "-pp":
            whom = "Production Partners (data scanned)"
        elif origin == "ASR":
            whom = "Audio Science Review"
    return "{2} for {0} measured by {1}".format(speaker, whom, title)


def print_graph(filename, chart, title, ext, force) -> int:
    updated = 0

    check = (
        force
        or not os.path.exists(filename)
        or (os.path.exists(filename) and os.path.getsize(filename) == 0)
    )
    if not check:
        return updated

    try:
        if ext == "json":
            content = chart.to_json()
            with open(filename, "w", encoding="utf-8") as f_d:
                f_d.write(content)
        else:
            write_multiformat(chart, filename, force)
        updated += 1
    except Exception:
        logger.exception("Got unkown error for %s", filename)

    return updated


@ray.remote
def print_graphs(
    df: dict[str, pd.DataFrame],
    speaker: str,
    version: str,
    origin: str,
    origins_info: dict,
    key: str,
    width: int,
    height: int,
    force_print: bool,  # noqa: FBT001
    level: int,
):
    ray_setup_logger(level)
    # may happens at development time or for partial measurements
    # or when the cache is confused (typically when you change the metadata)
    if df is None:
        logger.debug("df is None for %s %s %s", speaker, version, origin)
        return 0

    if len(df.keys()) == 0:
        # if print_graph is called before df is ready
        # fix: ray call above
        return 0

    graph_params = copy.deepcopy(plot_params_default)
    if width // height != 4 // 3:
        logger.error("ratio width / height must be 4/3")
        height = int(width * 3 / 4)
    graph_params["width"] = width
    graph_params["height"] = height
    graph_params["layout"] = "compact"
    graph_params["xmin"] = origins_info[origin]["min hz"]
    graph_params["xmax"] = origins_info[origin]["max hz"]
    graph_params["ymin"] = origins_info[origin]["min dB"]
    graph_params["ymax"] = origins_info[origin]["max dB"]

    graphs = {}
    for op_title, op_call in (
        ("CEA2034", display_spinorama),
        ("On Axis", display_onaxis),
        ("Estimated In-Room Response", display_inroom),
        ("Early Reflections", display_reflection_early),
        ("Horizontal Reflections", display_reflection_horizontal),
        ("Vertical Reflections", display_reflection_vertical),
        ("SPL Horizontal", display_spl_horizontal),
        ("SPL Vertical", display_spl_vertical),
        ("SPL Horizontal Normalized", display_spl_horizontal_normalized),
        ("SPL Vertical Normalized", display_spl_vertical_normalized),
    ):
        logger.debug("%s %s %s %s", speaker, version, origin, ",".join(list(df.keys())))
        graph = op_call(df, graph_params)
        if graph is None:
            logger.debug("display %s failed for %s %s %s", op_title, speaker, version, origin)
            if op_title == "CEA2034":
                logger.warning("display %s failed for %s %s %s", op_title, speaker, version, origin)
            continue
        graphs[op_title] = graph

    # change params for contour
    contour_params = copy.deepcopy(contour_params_default)
    contour_params["width"] = width
    contour_params["height"] = height
    contour_params["layout"] = "compact"
    contour_params["xmin"] = origins_info[origin]["min hz"]
    contour_params["xmax"] = origins_info[origin]["max hz"]

    graphs["SPL Horizontal Contour"] = display_contour_horizontal(df, contour_params)
    graphs["SPL Vertical Contour"] = display_contour_vertical(df, contour_params)
    graphs["SPL Horizontal Contour Normalized"] = display_contour_horizontal_normalized(
        df, contour_params
    )
    graphs["SPL Vertical Contour Normalized"] = display_contour_vertical_normalized(
        df, contour_params
    )

    graphs["SPL Horizontal Contour 3D"] = display_contour_horizontal_3d(df, contour_params)
    graphs["SPL Vertical Contour 3D"] = display_contour_vertical_3d(df, contour_params)
    graphs["SPL Horizontal Contour Normalized 3D"] = display_contour_horizontal_normalized_3d(
        df, contour_params
    )
    graphs["SPL Vertical Contour Normalized 3D"] = display_contour_vertical_normalized_3d(
        df, contour_params
    )

    # better square
    radar_params = copy.deepcopy(radar_params_default)
    radar_params["width"] = int(height * 4 / 5)
    radar_params["height"] = height
    radar_params["layout"] = "compact"
    radar_params["xmin"] = origins_info[origin]["min hz"]
    radar_params["xmax"] = origins_info[origin]["max hz"]

    graphs["SPL Horizontal Radar"] = display_radar_horizontal(df, radar_params)
    graphs["SPL Vertical Radar"] = display_radar_vertical(df, radar_params)

    # add a title and setup legend
    for k in graphs:
        title = k.replace("_smoothed", "")
        # optimised for small screens / vertical orientation
        if graphs[k] is not None:
            text = build_title(origin, version, speaker, title)
            graphs[k].update_layout(
                title=dict(
                    text=text,
                    font=dict(
                        size=20,
                    ),
                ),
                font=dict(
                    size=20,
                ),
            )

    updated = 0
    for title, graph in graphs.items():
        if graph is not None:
            # force_update = need_update()
            force_update = False
            for ext in ("png", "json"):
                filename = build_filename(speaker, origin, key, title, ext)
                updated += print_graph(filename, graph, title, ext, force_print or force_update)
    return updated
