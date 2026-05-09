"""
Author: Devin
Date: 2023-12-23 18:18:13
LastEditors: Devin
LastEditTime: 2024-11-28 16:19:09
FilePath: \PythonDemo\esil\RSM\Model_Property.py
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
"""

import netCDF4 as nc
from pyproj import pyproj, transform
import numpy as np


class model_attribute:

    def __init__(self, nc_file):
        nc_data = nc.Dataset(nc_file)
        center_lon = nc_data.getncattr("XCENT")
        center_lat = nc_data.getncattr("YCENT")
        lat_1 = nc_data.getncattr("P_ALP")
        lat_2 = nc_data.getncattr("P_BET")
        proj4_string = ""
        # Check conditions and set projection string accordingly
        if center_lat == 40 and center_lon == -97:
            proj4_string = f"+proj=lcc +lat_1={lat_1} +lat_2={lat_2} +lat_0={center_lat} +lon_0={center_lon} +a=6370000.0 +b=6370000.0"
        else:
            proj4_string = f"+x_0=0 +y_0=0 +lat_0={center_lat} +lon_0={center_lon} +lat_1={lat_1} +lat_2={lat_2} +proj=lcc +ellps=WGS84 +no_defs"
        self.proj4_string = proj4_string
        projection = pyproj.Proj(proj4_string)
        self.x_orig = nc_data.getncattr("XORIG")
        self.y_orig = nc_data.getncattr("YORIG")
        self.x_resolution = nc_data.getncattr("XCELL")
        self.y_resolution = nc_data.getncattr("YCELL")
        self.cols = nc_data.getncattr("NCOLS")
        self.rows = nc_data.getncattr("NROWS")
        self.min_x = self.x_orig + self.x_resolution / 2
        self.min_y = self.y_orig + self.y_resolution / 2
        self.max_x = self.min_x + self.cols * self.x_resolution
        self.max_y = self.min_y + self.rows * self.y_resolution
        self.lon_start, self.lat_start = projection(
            self.min_x, self.min_y, inverse=True
        )
        self.lon_end, self.lat_end = projection(self.max_x, self.max_y, inverse=True)
        import cartopy.crs as ccrs

        self.projection = ccrs.LambertConformal(
            central_longitude=center_lon,
            central_latitude=center_lat,
            standard_parallels=(lat_1, lat_2),
        )

        self.is_BC = "PERIM" in nc_data.dimensions
        if self.is_BC:
            self.rows = self.rows + 2  # Add top and bottom boundary grids
            self.cols = self.cols + 2  # Add front and rear boundary grids
            self.start_date = nc_data.getncattr("SDATE")
            if self.start_date:
                from esil import date_helper

                self.start_date = date_helper.convert_julian_regular_date(
                    self.start_date
                )
            self.min_x = float(self.x_orig - self.x_resolution / 2.0)  # Expand by one grid
            tmp = (self.cols + 1) * self.x_resolution
            # Get maximum coordinate
            self.max_x = float(tmp + self.min_x)
            # Get minimum y coordinate
            self.min_y = float(self.y_orig + self.y_resolution / 2.0)
            # There are 111 segments between rows 1~112, so total length between 1~112 is: (112-1)*grid height
            tmp = (self.rows + 1) * self.y_resolution
            # Get maximum coordinate
            self.max_y = float(tmp + self.min_y)

            self.x_coords_bc, self.y_coords_bc, self.x_coords, self.y_coords = (
                self.get_xy_coords()
            )

            # self.lons, self.lats = projection(self.x_coords, self.y_coords , inverse=True)
            # Convert x, y in Lambert projection coordinates to x, y in longitude-latitude coordinates
            self.lats, self.lons = transform(
                projection, "EPSG:4326", self.x_coords_bc, self.y_coords_bc
            )  # 'EPSG:4326' represents longitude-latitude coordinate system
            # lon, lat = projection(self.x_coords[0], self.y_coords[0], inverse=True)
            # print( lon, lat )
        else:
            self.x_coords, self.y_coords = self.get_xy_coords()
            grid_x, grid_y = np.meshgrid(self.x_coords, self.y_coords)
            self.lats, self.lons = transform(projection, "EPSG:4326", grid_x, grid_y)
            # self.lons, self.lats = projection(self.x_coords, self.y_coords, inverse=True)

    def get_xy_coords(self):
        try:
            if self.is_BC:
                cols, rows = self.cols, self.rows
                lon_values, lat_values = [], []
                for col in range(cols):
                    lon_values.append(self.min_x + col * self.x_resolution)
                for row in range(rows):
                    lat_values.append(self.min_y + row * self.y_resolution)
                float_x_coords, float_y_coords = [], []
                # Get longitude and latitude of each grid counterclockwise starting from the first grid at the bottom left
                for col in range(cols):
                    float_y_coords.append(lat_values[0])
                    float_x_coords.append(lon_values[col])
                for row in range(1, rows - 1):
                    float_y_coords.append(lat_values[row])
                    float_x_coords.append(lon_values[cols - 1])
                for col in range(cols - 1, -1, -1):
                    float_y_coords.append(lat_values[rows - 1])
                    float_x_coords.append(lon_values[col])
                for row in range(rows - 2, 0, -1):
                    float_y_coords.append(lat_values[row])
                    float_x_coords.append(lon_values[0])
                return float_x_coords, float_y_coords, lon_values, lat_values
            else:
                row_count = self.rows
                col_count = self.cols
                float_x_coords = [0.0] * col_count
                float_y_coords = [0.0] * row_count
                for col in range(col_count):
                    float_x_coords[col] = self.min_x + col * self.x_resolution
                for row in range(row_count):
                    float_y_coords[row] = self.min_y + row * self.y_resolution
        except Exception as ex:
            print(f"Error: {ex}")
        return float_x_coords, float_y_coords

    def get_xy_coordinates(self, show_lonlat=False):
        """
        description: Get x, y coordinates to be displayed
        param {class} model, model attribute object
        param {bool} show_lonlat, default is False, if True, return longitude-latitude coordinates
        return {numpy.ndarray(2D), numpy.ndarray(2D)}
        """
        if show_lonlat:
            x, y = self.lons, self.lats
        else:
            x = np.linspace(1, self.cols, self.cols)
            y = np.linspace(1, self.rows, self.rows)
            x, y = np.meshgrid(x, y)
        return x, y