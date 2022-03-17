#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2022 mundialis GmbH & Co. KG

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

Grid Tiling Class
"""

__license__ = "GPLv3"
__author__ = "Anika Weinmann"
__copyright__ = "Copyright 2022 mundialis GmbH & Co. KG"
__maintainer__ = "mundialis GmbH % Co. KG"

from copy import deepcopy
from jinja2 import Template
import json
from flask import make_response, jsonify
from flask_restful_swagger_2 import Resource
from flask_restful_swagger_2 import swagger
import pickle
from uuid import uuid4

from actinia_core.core.common.app import auth
from actinia_core.core.common.api_logger import log_api_call
from actinia_core.rest.persistent_processing import PersistentProcessing
from actinia_core.rest.resource_base import ResourceBase
from actinia_core.core.common.redis_interface import enqueue_job
from actinia_core.core.common.app import URL_PREFIX

from actinia_core.rest.vector_layer import VectorLayerResource
from actinia_core.core.common.process_chain import ProcessChainConverter


from actinia_tiling_plugin.apidocs import helloworld
from actinia_tiling_plugin.resources.templating import tplEnv


class AsyncTilingProcessGridResource(ResourceBase):
    """Sample a STRDS at vector point locations, asynchronous call
    """

    def _execute(self, location_name, mapset_name):

        rdc = self.preprocess(
            has_json=True,
            has_xml=False,
            location_name=location_name,
            mapset_name=mapset_name,
        )
        if rdc:
            # for debugging use the following to lines instead of enqueue_job
            processing = AsyncTilingProcessGrid(rdc)
            processing.run()
            # enqueue_job(self.job_timeout, start_job, rdc)

        return rdc

    @swagger.doc(helloworld.describeHelloWorld_post_docs)
    def post(self, location_name, mapset_name):
        """Sample a strds by point coordinates, asynchronous call
        """
        self._execute(location_name, mapset_name)
        html_code, response_model = pickle.loads(self.response_data)
        return make_response(jsonify(response_model), html_code)

    # def get(self):
    # TODO


def start_job(*args):
    processing = AsyncTilingProcessGrid(*args)
    processing.run()


class AsyncTilingProcessGrid(PersistentProcessing):
    """Create a grid.
    """

    def __init__(self, *args):
        PersistentProcessing.__init__(self, *args)
        # TODO RESPONSEMODEL
        # self.response_model_class = STRDSSampleGeoJSONResponseModel

    def _execute_preparation(self):

        self._setup()

        # Check and lock the target and temp mapsets
        self._check_lock_target_mapset()

        if self.target_mapset_exists is False:
            # Create the temp database and link the
            # required mapsets into it
            self._create_temp_database(self.required_mapsets)

            # Initialize the GRASS environment and switch into PERMANENT
            # mapset, which is always linked
            self._create_grass_environment(
                grass_data_base=self.temp_grass_data_base,
                mapset_name="PERMANENT"
            )

            # Create the temporary mapset with the same name as the target
            # mapset and switch into it
            self._create_temporary_mapset(
                temp_mapset_name=self.target_mapset_name,
                interim_result_mapset=None,
                interim_result_file_path=None)
            self.temp_mapset_name = self.target_mapset_name
        else:
            # Init GRASS environment and create the temporary mapset
            self._create_temporary_grass_environment(
                source_mapset_name=self.target_mapset_name)
            self._lock_temp_mapset()

    def _execute(self):

        self._execute_preparation()
        pconv = ProcessChainConverter()
        # mapset_mr = MapsetManagementResourceUser()
        # mapset_resp = mapset_mr.get(self.location_name, self.mapset_name)
        # mapset_info = json.loads(mapset_resp.data)["process_results"]

        # v.mkgrid with output map and box
        req_data_orig = self.request_data
        grid_prefix = req_data_orig["grid_prefix"]
        grid_name = f"grid_{uuid4().hex}"
        box = f"{req_data_orig['width']},{req_data_orig['height']}"
        tpl1 = tplEnv.get_template("pc_create_grid.json")
        pc1 = json.loads(tpl1.render(
            box=box,
            grid_name=grid_name
        ).replace('\n', '').replace(" ", ""))
        pl1 = pconv.process_chain_to_process_list(pc1)
        self.output_parser_list = pconv.output_parser_list
        self._execute_process_list(pl1)
        self._parse_module_outputs()
        grid_info = self.module_results["grid_info"]
        num_grid_cells = int([
            info.split("=")[1] for info in grid_info
            if info.split("=")[0] == "centroids"
        ][0])

        # extract grid cells
        tpl2 = tplEnv.get_template("pc_extract_grid.json")
        pc2 = json.loads(tpl2.render(
            grid_name=grid_name,
            grid_prefix=grid_prefix,
            n=num_grid_cells
        ).replace('\n', '').replace(" ", ""))
        pl2 = pconv.process_chain_to_process_list(pc2)
        self._execute_process_list(pl2)

        # delete grid
        vect_mng = VectorLayerResource()
        vect_mng.delete(self.location_name, self.mapset_name, grid_name)
        tpl3 = tplEnv.get_template("pc_delete_vector.json")
        pc3 = json.loads(tpl3.render(
            vector_name=grid_name
        ).replace('\n', '').replace(" ", ""))
        pl3 = pconv.process_chain_to_process_list(pc3)
        self._execute_process_list(pl3)

        # make response pretty
        import pdb; pdb.set_trace()

        # point_file = tempfile.NamedTemporaryFile(dir=self.temp_file_path, delete=True)
        # result_file = tempfile.NamedTemporaryFile(dir=self.temp_file_path, delete=True)
        #
        # point_file.write(json_dumps(geojson).encode())
        # point_file.flush()
        #
        # pc = dict()
        # pc["1"] = {"module": "v.import",
        #            "inputs": {"input": point_file.name},
        #            "outputs": {"output": {"name": "input_points"}}}
        #
        # pc["2"] = {"module": "t.rast.sample",
        #            "inputs": {"strds": "%s@%s" % (strds_name, self.mapset_name),
        #                       "points": "input_points"},
        #            "outputs": {"output": {"name": result_file.name}},
        #            "flags": "rn",
        #            "overwrite": True,
        #            "verbose": True}
        #
        # self.request_data = pc
        #
        # # Run the process chain
        # PersistentProcessing._execute(self, skip_permission_check=True)
        #
        # result = open(result_file.name, "r").readlines()
        #
        # output_list = []
        # for line in result:
        #     output_list.append(line.strip().split("|"))
        #
        # self.module_results = output_list
        #
        # point_file.close()
        # result_file.close()

# class TilingProcessGridResource(PersistentProcessing):
#
#     def __init__(self, *args):
#         PersistentProcessing.__init__(self, *args)
#         self.response_model_class = STRDSSampleGeoJSONResponseModel
#
#     def post(self, location_name, mapset_name):
#         """Create a grid.
#         """
#
#
#     decorators = [log_api_call, auth.login_required]


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
