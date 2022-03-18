#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2018-present mundialis GmbH & Co. KG

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Add endpoints to flask app with endpoint definitions and routes
"""

__license__ = "GPLv3"
__author__ = "Anika Weinmann"
__copyright__ = "Copyright 2022 mundialis GmbH & Co. KG"
__maintainer__ = "mundialis GmbH % Co. KG"


# from actinia_tiling_plugin.api.tiling_list import TilingList
from actinia_tiling_plugin.api.tiling.tiling_grid import \
    AsyncTilingProcessGridResource


# endpoints loaded if run as actinia-core plugin as well as standalone app
def create_endpoints(flask_api):

    flask_api.add_resource(
        AsyncTilingProcessGridResource,
        "/locations/<string:location_name>/mapsets/"
        "<string:mapset_name>/tiling_processes/grid",
    )
# TODOs
# Endpoint to list all tiling_processes with description
# /locations/{location_name}/mapsets/{mapset_name}/tiling_processes
# response (wie Modulselbstbeschreibung):
# {
#   tiling_processes: [
#     {
#         categories: [
#           "grid"
#         ],
#        description: "Create vector map grid tiles.",
#        id: "grid"
#      },
# ....
# ]}

# Endpoint to generate a grid
# /locations/{location_name}/mapsets/{mapset_name}/tiling_processes/grid

# TODO:
# * Anzahl oder Auflösung mitschicken?

# region ist vorher gesetzt
# POSTBODY
# {
#   width: .., # in map unitx
#   height: ..,
#   output_prefix: ..,
# }
# RESP
# [
#   output_prefix1,
#   output_prefix2,
#   output_prefix3,
#   ...
# ]

# "/locations/{location_name}/mapsets/{mapset_name}/tiling_process/grid"