import ast
import itertools
import os
import xmltodict as xdict
from shapely.geometry import Polygon


def parse_parameter_xml(config: str, parameter_index: int) -> (str, str, int, int, int, int, float, bool, int, str):
    """
    Parse the config file for all simulation parameters.
    @param config File path to the config file
    @param parameter_index Index of parameter in parameter variation
    @return Parsed parameters from the config file
    """
    config = os.path.abspath(config)
    with open(config, 'rb') as config_file:
        xml_dict = xdict.parse(config_file)
    sumo_cfg = list(xml_dict['configuration']['input']['sumo-config'].values())[0]
    sumo_binary = list(xml_dict['configuration']['input']['sumo-path'].values())[0]
    sumo_route = None
    if 'sumo-route' in xml_dict['configuration']['input']:
        sumo_route = list(xml_dict['configuration']['input']['sumo-route'].values())[0]
    output_path_string = list(xml_dict['configuration']['output']['output-path'].values())[0]
    output_abs_path = os.path.abspath(output_path_string)
    sumo_buildings = list(xml_dict['configuration']['input']['sumo-buildings'].values())[0]
    sumo_polygons = list(xml_dict['configuration']['input']['sumo-polygons'].values())[0]

    with open(sumo_polygons, 'rb') as polygon_file:
        xml_dict_polygon = xdict.parse(polygon_file)
    residential_areas = []
    for polygon in xml_dict_polygon['additional']['poly']:
        if polygon['@type'] == "residential" and polygon['@fill'] != "0":
            shape_list = []
            for coord_string in polygon['@shape'].split(' '):
                coord_1, coord_2 = coord_string.split(',')
                coord_1 = float(coord_1)
                coord_2 = float(coord_2)
                shape_list.append([coord_1, coord_2])
            residential_areas.append(Polygon(shape_list))

    with open(sumo_buildings, 'rb') as building_file:
        xml_dict_building = xdict.parse(building_file)
    area_list = []
    id_list = []
    for building in xml_dict_building['additional']['poly']:
        if building['@type'] == "building" and building['@fill'] != "0":
            shape_list = []
            for coord_string in building['@shape'].split(' '):
                coord_1, coord_2 = coord_string.split(',')
                coord_1 = float(coord_1)
                coord_2 = float(coord_2)
                shape_list.append([coord_1, coord_2])
            p = Polygon(shape_list)
            for res_area in residential_areas:
                if p.intersects(res_area):
                    area_list.append(p.area)
                    id_list.append(building['@id'])
                    break
    ap_coords = None
    if 'ap-coordinates' in xml_dict['configuration']['input']:
        ap_coords = []
        ap_coords_file = list(xml_dict['configuration']['input']['ap-coordinates'].values())[0]
        with open(ap_coords_file, 'r') as coords:
            for line in coords:
                d = ast.literal_eval(line)
                ap_coords.append(d)
    number_vehicles = None
    additional_vehicles = None
    update_size = None
    initial_seeds = None
    v2v_distance = None
    wlan_distance = None
    duration = True
    duration_parameter = None
    ap_placement = None
    v2v_device = None
    wlan_device = None
    wlan_beacon_interval = None
    wlan_ap_count = None
    wlan_heartbeat_strategy = None
    v2v_heartbeat_strategy = None
    v2v_heartbeat_interval = None
    heartbeat_encoding = None
    v2v_data_rate = None
    wlan_data_rate = None
    seeding_strategy = None
    communication_standard = None
    mcs = None
    additional_attenuation = None
    max_number_connections = None
    v2v_equipment_percentage = None
    wlan_equipment_percentage = None
    wlan_ap_percentage = None

    for parameter in xml_dict['configuration']['parameter']:
        if parameter == "number-vehicles":
            number_vehicles = int(list(xml_dict['configuration']['parameter']['number-vehicles'].values())[0])
        if parameter == "additional-vehicles":
            additional_vehicles = int(list(xml_dict['configuration']['parameter']['additional-vehicles'].values())[0])
        if parameter == "update-size":
            update_size = int(list(xml_dict['configuration']['parameter']['update-size'].values())[0])
        if parameter == "initial-seeds":
            initial_seeds = int(list(xml_dict['configuration']['parameter']['initial-seeds'].values())[0])
        if parameter == "v2v-distance":
            v2v_distance = float(list(xml_dict['configuration']['parameter']['v2v-distance'].values())[0])
        if parameter == "wlan-distance":
            wlan_distance = float(list(xml_dict['configuration']['parameter']['wlan-distance'].values())[0])
        if parameter == "ap-placement":
            ap_placement = (list(xml_dict['configuration']['parameter']['ap-placement'].values())[0])
        if parameter == "v2v-device":
            v2v_device = True if (list(xml_dict['configuration']['parameter']['v2v-device'].values())[
                0]) == "on" else False
        if parameter == "wlan-device":
            wlan_device = True if (list(xml_dict['configuration']['parameter']['wlan-device'].values())[
                0]) == "on" else False
        if parameter == "wlan-beacon-interval":
            wlan_beacon_interval = float(
                list(xml_dict['configuration']['parameter']['wlan-beacon-interval'].values())[0])
        if parameter == "wlan-ap-count":
            wlan_ap_count = int(list(xml_dict['configuration']['parameter']['wlan-ap-count'].values())[0])
        if parameter == "wlan-heartbeat-strategy":
            wlan_heartbeat_strategy = (
            list(xml_dict['configuration']['parameter']['wlan-heartbeat-strategy'].values())[0])
        if parameter == "v2v-heartbeat-strategy":
            v2v_heartbeat_strategy = (
            list(xml_dict['configuration']['parameter']['v2v-heartbeat-strategy'].values())[0])
        if parameter == "v2v-heartbeat-interval":
            v2v_heartbeat_interval = float(
                list(xml_dict['configuration']['parameter']['v2v-heartbeat-interval'].values())[0])
        if parameter == "heartbeat-encoding":
            heartbeat_encoding = (list(xml_dict['configuration']['parameter']['heartbeat-encoding'].values())[0])
        if parameter == "v2v-data-rate":
            v2v_data_rate = int(list(xml_dict['configuration']['parameter']['v2v-data-rate'].values())[0])
        if parameter == "wlan-data-rate":
            wlan_data_rate = int(list(xml_dict['configuration']['parameter']['wlan-data-rate'].values())[0])
        if parameter == "seeding-strategy":
            seeding_strategy = (list(xml_dict['configuration']['parameter']['seeding-strategy'].values())[0])
        if parameter == "additional-attenuation":
            additional_attenuation = float(
                list(xml_dict['configuration']['parameter']['additional-attenuation'].values())[0])
        if parameter == "wlan-ap_max_connections":
            max_number_connections = int(
                list(xml_dict['configuration']['parameter']['wlan-ap_max_connections'].values())[0])
        if parameter == "v2v-equipment-percentage":
            v2v_equipment_percentage = float(
                list(xml_dict['configuration']['parameter']['v2v-equipment-percentage'].values())[0])
        if parameter == "wlan-equipment-percentage":
            wlan_equipment_percentage = float(
                list(xml_dict['configuration']['parameter']['wlan-equipment-percentage'].values())[0])
        if parameter == "wlan-ap-percentage":
            wlan_ap_percentage = float(list(xml_dict['configuration']['parameter']['wlan-ap-percentage'].values())[0])

    for parameter in xml_dict['configuration']['communication']:
        if parameter == "standard":
            communication_standard = str(list(xml_dict['configuration']['communication']['standard'].values())[0])
        if parameter == "mcs":
            mcs = int(list(xml_dict['configuration']['communication']['mcs'].values())[0])

    variation_keys = list(xml_dict['configuration']['parameter-variation'].keys())
    values_parameter = []

    for values in variation_keys:
        paras = list(xml_dict['configuration']['parameter-variation'][values].values())[0].split(", ")
        values_parameter.append(paras)

    parameters = list(itertools.product(*values_parameter))[parameter_index]

    for index, variation_key in enumerate(variation_keys):
        print(index, variation_key, parameters[index], parameters)
        if variation_key == "number-vehicles":
            number_vehicles = int(parameters[index])
        elif variation_key == "additional-vehicles":
            additional_vehicles = int(parameters[index])
        elif variation_key == "update-size":
            update_size = int(parameters[index])
        elif variation_key == "initial-seeds":
            initial_seeds = int(parameters[index])
        elif variation_key == "iterations":
            iterations = int(parameters[index])
        elif variation_key == "v2v-distance":
            v2v_distance = float(parameters[index])
        elif variation_key == "wlan-distance":
            wlan_distance = float(parameters[index])
        elif variation_key == "ap-placement":
            ap_placement = parameters[index]
        elif variation_key == "v2v-device":
            v2v_device = True if parameters[index] == "on" else False
        elif variation_key == "wlan-device":
            wlan_device = True if parameters[index] == "on" else False
        elif variation_key == "wlan-beacon-interval":
            wlan_beacon_interval = float(parameters[index])
        elif variation_key == "wlan-ap-count":
            wlan_ap_count = int(parameters[index])
        elif variation_key == "wlan-heartbeat-strategy":
            wlan_heartbeat_strategy = parameters[index]
        elif variation_key == "v2v-heartbeat-strategy":
            v2v_heartbeat_strategy = parameters[index]
        elif variation_key == "v2v-heartbeat-interval":
            v2v_heartbeat_interval = float(parameters[index])
        elif variation_key == "heartbeat-encoding":
            heartbeat_encoding = parameters[index]
        elif variation_key == "v2v-data-rate":
            v2v_data_rate = int(parameters[index])
        elif variation_key == "wlan-data-rate":
            wlan_data_rate = int(parameters[index])
        elif variation_key == "seeding-strategy":
            seeding_strategy = parameters[index]
        elif variation_key == "additional-attenuation":
            additional_attenuation = float(parameters[index])
        elif variation_key == "wlan-ap_max_connections":
            max_number_connections = int(parameters[index])
        elif variation_key == "v2v-equipment-percentage":
            v2v_equipment_percentage = float(parameters[index])
        elif variation_key == "wlan-equipment-percentage":
            wlan_equipment_percentage = float(parameters[index])
        elif variation_key == "wlan-ap-percentage":
            wlan_ap_percentage = float(parameters[index])

    if list(xml_dict['configuration']['time']['simulate-duration'].values())[0] == 'true':
        duration = True
        duration_parameter = int(list(xml_dict['configuration']['time']['duration'].values())[0])
    else:
        duration = False
        duration_parameter = int(list(xml_dict['configuration']['time']['number-of-routes'].values())[0])

    return sumo_cfg, sumo_binary, number_vehicles, additional_vehicles, update_size, initial_seeds, v2v_distance, \
        duration, duration_parameter, output_abs_path, (id_list, area_list), ap_placement, v2v_device, wlan_device, \
        wlan_distance, wlan_beacon_interval, v2v_heartbeat_interval, wlan_ap_count, wlan_heartbeat_strategy, \
        v2v_heartbeat_strategy, heartbeat_encoding, v2v_data_rate, wlan_data_rate, seeding_strategy, parameters, \
        sumo_route, communication_standard, mcs, additional_attenuation, ap_coords, max_number_connections, v2v_equipment_percentage, wlan_equipment_percentage, wlan_ap_percentage


def parse_constants_xml(config) -> (int, float, float, int, float, float, bool, bool, bool, bool, float, float, float):
    """
    Parse the config file for all constants.
    @param config File path to the config file
    @return Parsed constants from the config file
    """
    config = os.path.abspath(config)
    with open(config, 'rb') as config_file:
        xml_dict = xdict.parse(config_file)

    gain = None
    transmission_power = None
    pathloss = None
    noisepower = None
    loss_exponent = None
    antenna_height = None
    two_ray = None
    log_distance = None
    log_shadow = None
    shadow_slope = None
    loss_exponent2 = None
    sigma = None
    sigma2 = None

    for parameter in xml_dict['configuration']['constants']:
        if parameter == "gain":
            gain = int(list(xml_dict['configuration']['constants']['gain'].values())[0])
        if parameter == "transmission-power":
            transmission_power = float(list(xml_dict['configuration']['constants']['transmission-power'].values())[0])
        if parameter == "pathloss":
            pathloss = float(list(xml_dict['configuration']['constants']['pathloss'].values())[0])
        if parameter == "noisepower":
            noisepower = int(list(xml_dict['configuration']['constants']['noisepower'].values())[0])
        if parameter == "loss-exponent":
            loss_exponent = float(list(xml_dict['configuration']['constants']['loss-exponent'].values())[0])
        if parameter == "antenna-height":
            antenna_height = float(list(xml_dict['configuration']['constants']['antenna-height'].values())[0])
        if parameter == "two_ray":
            if list(xml_dict['configuration']['constants']['two-ray-ground'].values())[0] == 'true':
                two_ray = True
            else:
                two_ray = False
        if parameter == "log_distance":
            if list(xml_dict['configuration']['constants']['log-distance'].values())[0] == 'true':
                log_distance = True
            else:
                log_distance = False
        if parameter == "log-normal-shadowing":
            if list(xml_dict['configuration']['constants']['log-normal-shadowing'].values())[0] == 'true':
                log_shadow = True
            else:
                log_shadow = False
        if parameter == "log-normal-shadowing-dual-slope":
            if list(xml_dict['configuration']['constants']['log-normal-shadowing-dual-slope'].values())[0] == 'true':
                shadow_slope = True
            else:
                shadow_slope = False
        if parameter == "loss-exponent2":
            loss_exponent2 = float(list(xml_dict['configuration']['constants']['loss-exponent2'].values())[0])
        if parameter == "sigma":
            sigma = float(list(xml_dict['configuration']['constants']['sigma'].values())[0])
        if parameter == "sigma2":
            sigma2 = float(list(xml_dict['configuration']['constants']['sigma2'].values())[0])
        if two_ray:
            loss_exponent = 2
    return gain, transmission_power, pathloss, noisepower, loss_exponent, antenna_height, two_ray, log_distance, \
        log_shadow, shadow_slope, loss_exponent2, sigma, sigma2
