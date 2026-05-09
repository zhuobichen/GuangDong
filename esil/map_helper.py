import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.io.shapereader import Reader
import cartopy.mpl.geoaxes
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import geopandas as gpd
import numpy as np
from esil.panelayout_helper import get_layout_col_row, PaneLayout
import math

# Custom function to format data with different decimal places based on magnitude
def format_data(x):
    # 处理非常小的值，避免显示0.00e+00
    if abs(x) < 0.01:
        return "0.00"
    elif abs(x) > 1000:
        return "{:.0f}".format(x)  # Data larger than 1000 retains 0 decimal places
    elif abs(x) > 1:
        return "{:.2f}".format(x)  # Data larger than 1 retains 2 decimal places
    elif abs(x) < 0.001:
        return "{:.2e}".format(x)  # Data smaller than 0.001 uses scientific notation with 2 decimal places
    else:
        return "{:.3f}".format(x)  # Data between 0.001 and 1 retains 3 decimal places

# 专门用于统计信息显示的格式化函数，避免显示0.00e+00
def format_stat_data(x, value_format=None, is_mean=False):
    """格式化统计信息中的数值，处理小值显示

    Args:
        x: 要格式化的数值
        value_format: 格式字符串，如'.2f'
        is_mean: 是否为Mean值，如果是则不应用小于0.01的特例限制
    """
    if value_format is not None:
        # 对于Mean值，不应用小于0.01的特例限制
        if is_mean:
            # 只处理实际上为0的情况
            if abs(x) < 1e-6:
                return "0"
            else:
                return f"{x:{value_format}}"
        else:
            # 对于非Mean值，处理非常小的值
            if abs(x) < 0.01:
                # 对于差值图，0显示为"0"而不是"0.00"
                if abs(x) < 1e-6:  # 实际上接近0
                    return "0"
                else:
                    return "0.00"
            else:
                return f"{x:{value_format}}"
    else:
        # 使用默认的format_data函数
        return format_data(x)


def get_multiple_data(
    dict_data,
    dataset_name,
    variable_name,
    grid_x,
    grid_y,
    grid_concentration,
    file_name="",
    is_delta=False,
    points_data=None,   
    **kwargs
):
    """
    description:
    param {dictionary} dict_data, key=dataset_name, value=variable_name, grid_x, grid_y, grid_concentration, file_name, defaults to None (creates new dictionary)
    param {str} dataset_name, dataset name
    param {str} variable_name, variable name
    param {numpy array(2D)} grid_x, longitude coordinates
    param {numpy array(2D)} grid_y, latitude coordinates
    param {numpy array(2D)} grid_concentration, concentration values
    param {str} file_name, file name containing dataset, default=''
    param {bool} is_delta, whether it's difference data, default=False
    param {dictionary} points_data, point data, default=None, example: {'lon':df_monitor['lon'],'lat':df_monitor['lat'],'value':df_monitor['Monitor_Conc']}
    param {bool} use_map_settings, whether to use separate map settings, default=False, Sample:  
    param {dictionary} custom_map_settings, custom map settings, default=None, Sample: {"value_range":(-1,1),"show_domain_mean":True,"unit":"mg/m3"}   
    return {dictionary} dict_data
    """
    if dict_data is None:
        dict_data = {}
    if dataset_name in dict_data:
        print(f"dataset_name {dataset_name} already exists in dict_data")    
    dict_data[dataset_name] = {
        "file_name": file_name,
        "variable_name": variable_name,
        "grid_x": grid_x,
        "grid_y": grid_y,
        "grid_concentration": grid_concentration,
        "is_delta": is_delta,
        "points_data": points_data,
        # "unit": unit,#If unit is specified, it will be displayed separately instead of using the common unit       
        "custom_map_settings":kwargs
    }   
        
    return dict_data


def show_maps(dict_data, **kwargs):
    """
    description: Plotting function that supports mapping multiple datasets, including WRF output data and various 2D grid data; essentially any 2D grid data can be plotted with this function
    @param {dictionary} Dataset to be plotted, where keys are dataset names and values are parameter dictionaries containing:
        param {str} dataset_name, unique dataset name (cannot be duplicated)
        param {str} variable_name, variable name such as PM2.5
        param {numpy array(2D)} grid_x, longitude coordinates
        param {numpy array(2D)} grid_y, latitude coordinates
        param {numpy array(2D)} grid_concentration, concentration values
        param {str} file_name, file containing dataset (can be empty)
        param {bool} is_delta, whether it's a difference map (e.g., simulated value - observed value) vs original map, default=False

    param {dictionary} kwargs, parameter dictionary including:
        @param {str} unit, unit; example usage: unit='ug/m3'
        @param {str} cmap, color map, default='jet'; example usage: cmap='jet'
        @param {str} projection, map projection, default='' (uses PlateCarree when empty); example usage: projection=ccrs.PlateCarree()
        @param {str} boundary_file, administrative boundary file, default='' (no boundary data loaded when empty); example usage: boundary_file='data/china_shp/china.shp'
        @param {str} x_title, x-axis title, default='Longitude'; example usage: x_title='Longitude'
        @param {str} y_title, y-axis title, default='Latitude'; example usage: y_title='Latitude'
        @param {bool} show_minmax, whether to display min/max values, default=True; example usage: show_minmax=False
        @param {tuple} value_range, default min and max values (default_min_value, default_max_value), default=(None,None); example usage: value_range=(0,100)
        @param {str} or {tuple} panel_layout, subplot layout, default=None (auto-calculated when empty); tuple example: (col,row); string example from esil.panellayout_helper.PaneLayout: PaneLayout.ForceSquare; example usage: panel_layout=(2,2)
        @param {bool} show_original_grid, whether to display original grid, default=False; example usage: show_original_grid=True
        @param {bool} sharex, whether to share x-axis, default=True; example usage: sharex=False
        @param {bool} sharey, whether to share y-axis, default=True; example usage: sharey=False
        @param {bool} show_sup_title, whether to display shared XY axis titles, default=False; example usage: show_sup_title=True
        @param {bool} show_lonlat, whether to display longitude/latitude; default=False; example usage: show_lonlat=True
        @param {bool} show_plot, whether to display the figure, default=True; example usage: show_plot=False
        @param {dict} points_data, if not None, overlays point data on the map, default=None. This dictionary includes:
            {
            'lon': {numpy array(1D)} , longitude coordinates of points
            'lat':{numpy array(1D)} , latitude coordinates of points
            'value':{numpy array(1D)} , values at points (e.g., measured concentrations)
            'cmap':color map, default='jet'
            'edgecolor:point border color, default='black'
            'symbol_size':point size, default=50
            };
            example usage: points_data={'lon':df_monitor['lon'],'lat':df_monitor['lat'],'value':df_monitor['Monitor_Conc'],'cmap':'jet','edgecolor'='black','symbol_size':50}
        @param {bool} is_wrf_out_data, whether it's WRF output data, default=False; example usage: is_wrf_out_data=True
        @param {dict} delta_map_settings, parameters for difference maps, default=None, example:
            {
            'cmap':'coolwarm', colorbar for difference maps, default=coolwarm
            'value_range':(default_min_value,default_max_value),#default min and max values, default=(None,None)
            'colorbar_ticks_num':None, number of colorbar ticks, default=None (auto-calculated)
            'colorbar_ticks_value_format':format for colorbar tick values, default=None, example: '.2f' (2 decimal places); '.2e' (scientific notation with 2 decimals)
            'value_format':value format, default=same as outer value_format, example: '.2f' (2 decimal places); '.2e' (scientific notation with 2 decimals)
            };
            example usage: delta_map_settings={'cmap':'coolwarm','default_min_value':-1,'default_max_value':1}
        @param {bool} show_dependenct_colorbar, whether to show independent colorbars for each subplot, default=False (all subplots share one colorbar); True shows individual colorbars, useful for mixed original and difference maps; example usage: show_dependenct_colorbar=True
        @param {str} font_name, font name, default=None; example usage: font_name='Arial'; requires font to be installed
        @param {bool} show_grid_line, whether to display grid lines, default=True (only effective for WRF data when is_wrf_out_data=True); example usage: show_grid_line=False
        @param {str} value_format, value format, default=None, example: '.2f' (2 decimal places); '.2e' (scientific notation with 2 decimals); example usage: value_format='.2f'
        @param {int} xy_title_fontsize, font size for x,y axis titles, default=10; example usage: xy_title_fontsize=10
        @param {int} super_xy_title_fontsize, font size for shared x,y axis titles, default=15; example usage: super_xy_title_fontsize=15
        @param {int} title_fontsize, title font size, default=14; example usage: title_fontsize=14
        @param {bool} show_domain_mean, whether to display domain mean in x-axis title, default=True; shows grid sum when False (only effective when show_minmax=True); example usage: show_domain_mean=False
        @param {bool} show_lonlat_with_char, whether to display longitude/latitude with degree symbols, default=False; when True, shows degrees in letters; example usage: show_lonlat_with_char=True
        @param {int} colorbar_ticks_num, number of colorbar ticks, default=None (auto-calculated); example usage: colorbar_ticks_num=5
        @param {str} colorbar_ticks_value_format, format for colorbar tick values, default=None, example: '.2f' (2 decimal places); '.2e' (scientific notation with 2 decimals); example usage: colorbar_ticks_value_format='.2f'
        @param {int} xy_ticks_digits, decimal places for x,y axis ticks, default=1; example: xy_ticks_digits=1
        @param {bool} is_tight_layout, whether to automatically adjust subplot layout for proper spacing and fit, default=False. Recommended True when subplots have individual colorbars (show_dependenct_colorbar=True), else False; subplots_hspace and subplots_wspace have no effect when True; example usage: is_tight_layout=False
        @param {float} subplots_hspace, vertical spacing between subplots as proportion of figure height (0-1 range), default=0.3; only effective when is_tight_layout=False; example usage: subplots_hspace=0.3
        @param {float} subplots_wspace, horizontal spacing between subplots as proportion of figure width (0-1 range), default=0.2; only effective when is_tight_layout=False; example usage: subplots_wspace=0.2
        @param {tuple} subplots_fig_size, subplot size, default=None (auto-calculated). Tuple (width, height); example usage: subplots_fig_size=(6,6); auto-calculates width=6, height proportional to data dimensions if not set.
    @return {None or matplotlib.figure} fig
    Example calls:
    1. Without difference maps:
    fig=show_maps(dict_data,unit='ug/m3',cmap='jet', show_lonlat=True,projection=None, boundary_file='',show_original_grid=False)
    2. With difference maps:
    fig=show_maps(dict_data,unit='ug/m3',cmap='jet', show_lonlat=True,projection=None, boundary_file='',show_original_grid=False,
    delta_map_settings={'cmap':'coolwarm','value_range':(-1,1),'value_format':'.2f'})
    3. Showing point data:
    fig=show_maps(dict_data,unit='ug/m3',cmap='jet', show_lonlat=True,projection=None, boundary_file='',show_original_grid=False,
    points_data={'lon':[116.36,115.46,114.56,113.66,112.76],'lat':[39.92,39.02,38.12,37.22,36.32],'value':[35,40,45,50,55],'cmap':'jet','edgecolor'='black','symbol_size':50}    )
    4. Displaying WRF output data:
    fig=show_maps(dict_data,unit='ug/m3',cmap='jet', show_lonlat=True,projection=proj, boundary_file='',show_original_grid=False,
    is_wrf_out_data=True,show_grid_line=True,value_format='.2f'    )
    """

    # Get values for specified keys, return default if key doesn't exist
    unit = kwargs.get("unit", "")
    cmap = kwargs.get("cmap", "jet")
    show_lonlat = kwargs.get("show_lonlat", False)
    projection = kwargs.get("projection", None)
    boundary_file = kwargs.get("boundary_file", "")
    x_title = kwargs.get("x_title", "Longitude")
    y_title = kwargs.get("y_title", "Latitude")
    show_minmax = kwargs.get("show_minmax", True)
    value_range = kwargs.get("value_range", (None, None))
    panel_layout = kwargs.get("panel_layout", None)
    show_original_grid = kwargs.get("show_original_grid", False)
    sharex = kwargs.get("sharex", True)
    sharey = kwargs.get("sharey", True)
    show_sup_title = kwargs.get("show_sup_title", False)
    is_wrf_out_data = kwargs.get("is_wrf_out_data", False)
    points_data = kwargs.get("points_data", None)
    delta_map_settings = kwargs.get("delta_map_settings", None)
    show_dependenct_colorbar = kwargs.get("show_dependenct_colorbar", False)
    show_plot = kwargs.get("show_plot", True)
    font_name = kwargs.get("font_name", None)
    show_grid_line = kwargs.get(
        "show_grid_line", True
    )  # Whether to show grid lines, only effective for WRF data
    value_format_conc = kwargs.get("value_format", None)
    xy_title_fontsize = kwargs.get("xy_title_fontsize", 10)
    super_xy_title_fontsize = kwargs.get("super_xy_title_fontsize", 15)
    title_fontsize = kwargs.get("title_fontsize", 14)
    show_domain_mean = kwargs.get("show_domain_mean", True)
    show_lonlat_with_char = kwargs.get("show_lonlat_with_char", False)
    # keywords_for_delta= kwargs.get('keywords_for_delta', 'delta')
    colorbar_ticks_num = kwargs.get("colorbar_ticks_num", None)
    colorbar_ticks_value_format = kwargs.get("colorbar_ticks_value_format", None)
    xy_ticks_digits = kwargs.get("xy_ticks_digits", 1)
    is_tight_layout = kwargs.get(
        "is_tight_layout", False
    )  # Automatically adjust subplot layout for proper spacing and fit, default=False. subplots_hspace and subplots_wspace have no effect when True
    subplots_hspace = kwargs.get(
        "subplots_hspace", 0.3
    )  # Vertical spacing between subplots as proportion of figure height (0-1 range), default=0.3; only effective when is_tight_layout=False
    subplots_wspace = kwargs.get(
        "subplots_wspace", 0.2
    )  # Horizontal spacing between subplots as proportion of figure width (0-1 range), default=0.2; only effective when is_tight_layout=False
    subplots_fig_size = kwargs.get(
        "subplots_fig_size", None
    )  # Set subplot size as (width, height) tuple, auto-calculated when None
    if font_name != None:
        # Set Chinese font to installed system font such as SimSun (Song), SimHei (Hei)
        plt.rcParams["font.sans-serif"] = [font_name]  # Set Chinese font to Song
        plt.rcParams["axes.unicode_minus"] = False  # Properly display negative signs
    data_types = dict_data.keys()
    case_num = len(data_types)
    plot_columns, plot_rows = get_layout_col_row(case_num, panel_layout=panel_layout)
    if projection == None:
        projection = ccrs.PlateCarree()
    origin_projection = ccrs.PlateCarree() if is_wrf_out_data else projection
    width = 6
    first_key = next(iter(dict_data))
    height = (
        math.ceil(
            width
            * dict_data[first_key]["grid_y"].shape[0]
            / dict_data[first_key]["grid_x"].shape[-1]
        )
        if not isinstance(dict_data[first_key]["grid_y"], list)
        else width
    )
    if subplots_fig_size != None:
        width, height = subplots_fig_size
    fig, axs = plt.subplots(
        plot_rows,
        plot_columns,
        figsize=(width * plot_columns, height * plot_rows),
        subplot_kw={"projection": projection},
        sharex=sharex,
        sharey=sharey,
    )
    # if boundary_file:
    #     reader = Reader(boundary_file)
    if isinstance(axs, cartopy.mpl.geoaxes.GeoAxesSubplot):
        axs = np.array([axs])
    if show_sup_title == False and plot_rows > 1:
        y_titles = [y_title] * plot_rows
        if axs.ndim == 1:
            axs = axs.reshape(-1, 1)
        for ax, row in zip(axs[:, 0], y_titles):
            ax.set_ylabel(row, rotation=90, size=xy_title_fontsize)

    axs = axs.ravel()
    for ax, data_type in zip(axs, data_types):
        dic_sub_data = dict_data[data_type]
        file_name, variable_name, x, y, grid_concentration, is_delta,custom_map_settings = (
            dic_sub_data["file_name"],
            dic_sub_data["variable_name"],
            dic_sub_data["grid_x"],
            dic_sub_data["grid_y"],
            dic_sub_data["grid_concentration"],
            dic_sub_data["is_delta"],
            dic_sub_data["custom_map_settings"]
        )
        min_value, max_value, mean_value, total_value = (
            np.nanmin(grid_concentration),
            np.nanmax(grid_concentration),
            np.nanmean(grid_concentration),
            np.nansum(grid_concentration),
        )

        # 如果最小值是0.00几，直接设为0
        if abs(min_value) < 0.01:
            min_value = 0.0
        ax.text(
            0.5,
            1.07,
            f"{data_type} {variable_name}",
            transform=ax.transAxes,
            fontsize=title_fontsize,
            fontweight="bold",
            ha="center",
        )
        default_min_value, default_max_value = value_range
        vmax_conc = (
            np.nanpercentile(grid_concentration, 99.5)
            if default_max_value == None
            else default_max_value
        )
        vmin_conc = (
            np.nanpercentile(grid_concentration, 0.5)
            if default_min_value == None
            else default_min_value
        )
        if (
            vmax_conc == vmin_conc
        ):  # Avoid equal min and max values, set max to 1.5x grid mean
            vmax_conc = np.mean(grid_concentration) * 1.5
        if is_delta:
            cmap_delta = delta_map_settings.get("cmap", "coolwarm")
            
            default_delta_vmin, default_delta_vmax = delta_map_settings.get(
                "value_range", (None, None)
            )  # ["default_min_value"],delta_map_settings["default_max_value"]
            unit=custom_map_settings.get("unit",unit) 
            default_delta_vmin, default_delta_vmax=custom_map_settings.get("value_range",(default_delta_vmin, default_delta_vmax))
            show_domain_mean_custom=custom_map_settings.get("show_domain_mean",show_domain_mean)
            vmax_delta = (
                np.nanpercentile(grid_concentration, 99.5)
                if default_delta_vmax == None
                else default_delta_vmax
            )
            vmin_delta = (
                np.nanpercentile(grid_concentration, 0.5)
                if default_delta_vmin == None
                else default_delta_vmin
            )
            max_value_delta = np.max([abs(vmax_delta), abs(vmin_delta)])
            if max_value_delta == 0:  # Avoid zero range, set max to 0.1
                max_value_delta = 0.1
            vmin_delta, vmax_delta = -max_value_delta, max_value_delta
            if show_original_grid:
                contour = ax.pcolormesh(
                    x,
                    y,
                    grid_concentration,
                    cmap=cmap_delta,
                    vmin=vmin_delta,
                    vmax=vmax_delta,
                    transform=origin_projection,
                )
            else:
                contour = ax.contourf(
                    x,
                    y,
                    grid_concentration,
                    cmap=cmap_delta,
                    transform=origin_projection,
                    vmin=vmin_delta,
                    vmax=vmax_delta,
                )
            # Add colorbar to current subplot
            cbar = plt.colorbar(contour, ax=ax, shrink=0.6)
            colorbar_ticks_num_delta = delta_map_settings.get(
                "colorbar_ticks_num", None
            )
            if colorbar_ticks_num_delta is not None:
                cbar.set_ticks(
                    np.linspace(vmin_delta, vmax_delta, num=colorbar_ticks_num_delta)
                )  # Set number of colorbar ticks
            colorbar_ticks_value_format_delta = delta_map_settings.get(
                "colorbar_ticks_value_format", None
            )
            if colorbar_ticks_value_format_delta is not None:
                # 智能格式化差值图颜色条标签，避免显示0.00e+00
                def smart_delta_colorbar_formatter(x, p):
                    # 对于极小值，避免科学计数法
                    if abs(x) < 0.01:
                        # 对于差值图，0显示为"0"而不是"0.00"
                        if abs(x) < 1e-6:  # 实际上接近0
                            return "0"
                        else:
                            return "0.00"
                    else:
                        return f"{x:{colorbar_ticks_value_format_delta}}"

                cbar.ax.yaxis.set_major_formatter(
                    plt.FuncFormatter(smart_delta_colorbar_formatter)
                )  # Set colorbar value format
            if unit != "":
                cbar.set_label(f"({unit})", fontweight="bold")  # Set bold label
        else:  # Non-difference map
            if show_original_grid:
                contour = ax.pcolormesh(
                    x,
                    y,
                    grid_concentration,
                    cmap=cmap,
                    vmin=vmin_conc,
                    vmax=vmax_conc,
                    transform=origin_projection,
                )
            else:
                contour = ax.contourf(
                    x,
                    y,
                    grid_concentration,
                    cmap=cmap,
                    transform=origin_projection,
                    vmin=vmin_conc,
                    vmax=vmax_conc,
                )
            if show_dependenct_colorbar:
                cbar = plt.colorbar(contour, ax=ax, shrink=0.6)
                if colorbar_ticks_num is not None:
                    cbar.set_ticks(
                        np.linspace(vmin_conc, vmax_conc, num=colorbar_ticks_num)
                    )  # Set number of colorbar ticks
                if colorbar_ticks_value_format is not None:
                    # 智能格式化独立颜色条标签，避免显示0.00e+00
                    def smart_independent_colorbar_formatter(x, p):
                        # 对于极小值，避免科学计数法
                        if abs(x) < 0.01:
                            # 对于差值图，0显示为"0"而不是"0.00"
                            if abs(x) < 1e-6:  # 实际上接近0
                                return "0"
                            else:
                                return "0.00"
                        else:
                            return f"{x:{colorbar_ticks_value_format}}"

                    cbar.ax.yaxis.set_major_formatter(
                        plt.FuncFormatter(smart_independent_colorbar_formatter)
                    )  # Set colorbar value format
                if unit != "":
                    cbar.set_label(f"({unit})", fontweight="bold")  # Set bold label

        if (points_data is not None or dic_sub_data.get("points_data", None) is not None) and not is_delta:
            points_data = (
                dic_sub_data.get("points_data", None)
                if dic_sub_data.get("points_data", None) is not None
                else points_data
            )
            symbol_size = points_data.get("symbol_size", 50)
            edgecolor = points_data.get("edgecolor", "black")
            points_cmap = points_data.get("cmap", cmap)
            ax.scatter(
                x=points_data["lon"],
                y=points_data["lat"],
                s=symbol_size,
                c=points_data["value"],
                cmap=points_cmap,
                transform=origin_projection,
                vmin=vmin_conc,
                vmax=vmax_conc,
                edgecolor=edgecolor,
            )
        # Load administrative boundary data (example uses shapefile)
        if boundary_file:
            geometries = get_boundary_geometries(boundary_file)
            # geometries = reader.geometries()
            if geometries is not None:
                enshicity = cfeature.ShapelyFeature(
                    geometries, origin_projection, edgecolor="k", facecolor="none"
                )  # facecolor='none' for boundary lines only
                ax.add_feature(enshicity, linewidth=0.3)  # Add city boundary details
        else:  # Add online map features when no boundary_file provided
            # Add map features
            ax.add_feature(
                cfeature.COASTLINE, facecolor="none"
            )  # '-' or 'solid': solid line# '--' or 'dashed': dashed line# ':' or 'dotted': dotted line# '-.' or 'dashdot': dash-dot line
            ax.add_feature(cfeature.BORDERS, linestyle="solid", facecolor="none")
            ax.add_feature(
                cfeature.LAND, edgecolor="black", facecolor="none"
            )  # facecolor='none' for boundary lines only
            ax.add_feature(cfeature.OCEAN, edgecolor="black", facecolor="none")
        min_longitude, max_longitude, min_latitude, max_latitude = (
            round(x.min(), xy_ticks_digits),
            round(x.max(), xy_ticks_digits),
            round(y.min(), xy_ticks_digits),
            round(y.max(), xy_ticks_digits),
        )
        mean_or_total_label = "Total" if not show_domain_mean else "Mean"
        mean_or_total_value = total_value if not show_domain_mean else mean_value
        value_format = (
            delta_map_settings.get("value_format", value_format_conc)
            if is_delta
            else value_format_conc
        )
        if is_wrf_out_data:
            mesh = ax.gridlines(
                draw_labels=True,
                linestyle="--",
                linewidth=0.6,
                alpha=0.5,
                x_inline=False,
                y_inline=False,
                color="k",
                visible=show_grid_line,
            )
            mesh.top_labels = False
            mesh.right_labels = False
            mesh.xformatter = LONGITUDE_FORMATTER
            mesh.yformatter = LATITUDE_FORMATTER
            interval_x = math.ceil((max_longitude - min_longitude) / 10)
            interval_y = math.ceil((max_latitude - min_latitude) / 10)
            mesh.xlocator = mticker.FixedLocator(
                np.arange(min_longitude, max_longitude, interval_x)
            )
            mesh.ylocator = mticker.FixedLocator(
                np.arange(min_latitude, max_latitude, interval_y)
            )
            mesh.xlabel_style = {"size": xy_title_fontsize}
            mesh.ylabel_style = {"size": xy_title_fontsize}
            if show_minmax:
                # 对于Mean值，不应用小于0.01的特例限制
                is_mean_value = show_domain_mean
                min_max_info = f"Min= {format_stat_data(min_value, value_format)}, Max= {format_stat_data(max_value, value_format)}, {mean_or_total_label}={format_stat_data(mean_or_total_value, value_format, is_mean=is_mean_value)}"
                ax.text(
                    0.5,
                    1.02,
                    min_max_info,
                    transform=ax.transAxes,
                    fontsize=xy_title_fontsize,
                    ha="center",
                )  # , fontweight='bold'
        else:  # Non-WRF data
            if show_grid_line:
                mesh = ax.gridlines(
                    draw_labels=True,
                    linestyle="--",
                    linewidth=0.6,
                    alpha=0.5,
                    x_inline=False,
                    y_inline=False,
                    color="k",
                    visible=show_grid_line,
                )
                mesh.top_labels = False
                mesh.right_labels = False
                mesh.xformatter = LONGITUDE_FORMATTER
                mesh.yformatter = LATITUDE_FORMATTER
                interval_x = math.ceil((max_longitude - min_longitude) / 10)
                interval_y = math.ceil((max_latitude - min_latitude) / 10)
                mesh.xlocator = mticker.FixedLocator(
                    np.arange(min_longitude, max_longitude, interval_x)
                )
                mesh.ylocator = mticker.FixedLocator(
                    np.arange(min_latitude, max_latitude, interval_y)
                )
                mesh.xlabel_style = {"size": xy_title_fontsize}
                mesh.ylabel_style = {"size": xy_title_fontsize}
                if show_minmax:
                    # 对于Mean值，不应用小于0.01的特例限制
                    is_mean_value = show_domain_mean
                    min_max_info = f"Min= {format_stat_data(min_value, value_format)}, Max= {format_stat_data(max_value, value_format)}, {mean_or_total_label}={format_stat_data(mean_or_total_value, value_format, is_mean=is_mean_value)}"
                    ax.text(
                        0.5,
                        1.02,
                        min_max_info,
                        transform=ax.transAxes,
                        fontsize=xy_title_fontsize,
                        ha="center",
                    )  # , fontweight='bold'
            else:
                # Set y-axis range
                ax.set_ylim(min_latitude, max_latitude)
                # print(min(y), max(y))
                # Set x and y axis ticks range
                x_ticks, y_ticks = [], []
                interval_digit = 2 if xy_ticks_digits < 1 else xy_ticks_digits + 1
                if max_longitude > 180 and show_lonlat:
                    x_ticks = [-180, -120, -60, 0, 60, 120, 180]
                else:
                    interval_x = round(
                        float((max_longitude - min_longitude) / 7), interval_digit
                    )
                    x_ticks = np.round(
                        np.arange(min_longitude, max_longitude + 0.1, interval_x),
                        xy_ticks_digits,
                    )

                interval_y = round(
                    float((max_latitude - min_latitude) / 7), interval_digit
                )
                y_ticks = np.round(
                    np.arange(min_latitude, max_latitude + 0.1, interval_y),
                    xy_ticks_digits,
                )
                # x_ticks[0],x_ticks[-1]=min_longitude,max_longitude
                # y_ticks[0],y_ticks[-1]=min_latitude,max_latitude
                if show_lonlat_with_char:
                    mesh = ax.gridlines(
                        draw_labels=True,
                        linestyle="--",
                        linewidth=0.6,
                        alpha=0.5,
                        x_inline=False,
                        y_inline=False,
                        color="k",
                        visible=show_grid_line,
                    )
                    mesh.top_labels = False
                    mesh.right_labels = False
                    mesh.xformatter = LONGITUDE_FORMATTER
                    mesh.yformatter = LATITUDE_FORMATTER
                else:
                    ax.set_xticks(x_ticks)  # Set x-axis ticks range
                    ax.set_yticks(y_ticks)  # Set y-axis ticks range
                # min_value, max_value, mean_value, total_value = np.nanmin(grid_concentration), np.nanmax(grid_concentration), np.nanmean(grid_concentration), np.nansum(grid_concentration)
                if show_minmax:
                    # 对于Mean值，不应用小于0.01的特例限制
                    is_mean_value = show_domain_mean
                    min_max_info = f"Min= {format_stat_data(min_value, value_format)}, Max= {format_stat_data(max_value, value_format)}, {mean_or_total_label}={format_stat_data(mean_or_total_value, value_format, is_mean=is_mean_value)}"
                    ax.set_xlabel(
                        f"{ '' if show_sup_title else  x_title}\n{min_max_info}"
                    )
                else:
                    plt.xlabel(x_title)

    if show_sup_title:
        fig.supxlabel(
            f"{x_title}", y=0.08, fontsize=super_xy_title_fontsize, fontweight="normal"
        )  # Label x position relative to figure (0-1 range), default 0.01 from bottom
        fig.supylabel(
            f"{y_title}", x=0.08, fontsize=super_xy_title_fontsize, fontweight="normal"
        )

    if is_tight_layout:
        plt.tight_layout()
    else:  # Spacing adjustments may have no effect if subplot dimensions are poorly proportioned
        plt.subplots_adjust(
            hspace=subplots_hspace, wspace=subplots_wspace
        )  # Adjust vertical and horizontal spacing between subplots

    if not show_dependenct_colorbar and not is_delta:
        # Add colorbar
        cbar = plt.colorbar(
            contour,
            fraction=0.02,
            pad=0.04,
            label=f"{unit}",
            ax=axs,
            orientation="vertical",
            shrink=0.7,
        )  # Set colorbar height proportional to plot height

        if colorbar_ticks_num is not None:
            cbar.set_ticks(
                np.linspace(vmin_conc, vmax_conc, num=colorbar_ticks_num)
            )  # Set number of colorbar ticks
        if colorbar_ticks_value_format is not None:
            # 智能格式化颜色条标签，避免显示0.00e+00
            def smart_colorbar_formatter(x, p):
                # 对于极小值，避免科学计数法
                if abs(x) < 0.01:
                    # 对于差值图，0显示为"0"而不是"0.00"
                    if abs(x) < 1e-6:  # 实际上接近0
                        return "0"
                    else:
                        return "0.00"
                else:
                    return f"{x:{colorbar_ticks_value_format}}"

            cbar.ax.yaxis.set_major_formatter(
                plt.FuncFormatter(smart_colorbar_formatter)
            )  # Set colorbar value format
        # cbar.ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.2f'))
        if unit != "":
            cbar.set_label(f"({unit})", fontweight="bold")  # Set bold label

    if show_plot:  # Display the figure
        plt.show()
    return fig


def get_boundary_geometries(boundary_file):
    if boundary_file.endswith(".json"):
        import json
        from shapely.geometry import shape

        # Read JSON file
        with open(boundary_file, "r") as f:
            gdf = json.load(f)
            # Extract geometry objects
            geometries = [shape(feature["geometry"]) for feature in gdf["features"]]
    else:
        try:
            # Read shapefile or geojson file
            gdf = gpd.read_file(boundary_file)
            geometries = gdf["geometry"]
        except Exception as e:
            print(f"gpd failed to read administrative boundary data: {e}")
            try:
                from cartopy.io.shapereader import Reader

                reader = Reader(boundary_file)
                geometries = reader.geometries()
            except Exception as e:
                print(f"cartopy.io.shapereader failed to read administrative boundary data: {e}")
                geometries = None
    return geometries