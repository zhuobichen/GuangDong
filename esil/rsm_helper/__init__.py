'''
Author: Devin
Date: 2024-06-18 23:40:30
LastEditors: Devin
LastEditTime: 2024-06-28 22:38:34
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
'''
# from .factor import *
# from .model_property  import *
# from .rsm_worker import *
# from .ekma_curve import *
# from .get_differentiate import *
# from .grid_file import *

import importlib

def lazy_import(module_name):
    module = None
    def _import():
        nonlocal module
        if module is None:
            module = importlib.import_module(f'esil.rsm_helper.{module_name}')
        return module
    return _import

count_code_lines = lazy_import('count_code_lines')
ekma_curve = lazy_import('ekma_curve')
factor = lazy_import('factor')
get_differentiate = lazy_import('get_differentiate')
grid_file = lazy_import('grid_file')
model_property = lazy_import('model_property')
rsm_worker = lazy_import('rsm_worker')
