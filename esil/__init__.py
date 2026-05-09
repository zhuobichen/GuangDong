"""
Author: Devin
Date: 2024-06-18 21:30:32
LastEditors: Devin
LastEditTime: 2024-11-28 17:22:15
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
"""

# from .date_helper import *
# from .earth_helper import *
# from .file_helper import *
# from .log_helper import *
# from .interpolation_helper import *
# from .map_helper import *
# from .netcdf_helper import *
# from .panelayout_helper import *
# from .projection_helper import *
# from .scatter_plot_helper import *
# from  .sqlite_helper import *

import importlib


def lazy_import(module_name):
    module = None

    def _import():
        nonlocal module
        if module is None:
            module = importlib.import_module(f"esil.{module_name}")
        return module

    return _import


date_helper = lazy_import("date_helper")
earth_helper = lazy_import("earth_helper")
file_helper = lazy_import("file_helper")
log_helper = lazy_import("log_helper")
interpolation_helper = lazy_import("interpolation_helper")
map_helper = lazy_import("map_helper")
netcdf_helper = lazy_import("netcdf_helper")
panelayout_helper = lazy_import("panelayout_helper")
projection_helper = lazy_import("projection_helper")
scatter_plot_helper = lazy_import("scatter_plot_helper")
sqlite_helper = lazy_import("sqlite_helper")
wrf_helper = lazy_import("wrf_helper")
regrid_helper = lazy_import("regrid_helper")
plot_helper = lazy_import("plot_helper")
rsm_helper = lazy_import(".rsm_helper/__init__")  # 待测试20240625
