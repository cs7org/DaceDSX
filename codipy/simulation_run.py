from typing import List
import getopt
import os
import sys
import time
import math
import Backend as Backend
import FleetManager as fleetManager
import V2VNetworkingLayer as v2vNetworkingLayer
import ISMNetworkingLayer as ismNetworkingLayer
import csv
import pathlib
import WlanAPManager as wlan_ap_manager
import traceback
import random
import parameter_parser

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")
import traci
import traci.constants as tc


def parse_options(argv: List[str]) -> (str, int, int, float):  # parse multiple logfiles, put plots, calculated
    # values and traces in new directory
    """
    Parse command line options.
    @param argv List of command line arguments
    @return index in parameter variation, iteration
    """
    usage = 'usage: simulation_run.py [-h | --help] [-c | --config<str>] [-p | --parameter_index<number>] [-i | ' \
            '--iteration=<number>] [-s | --seed=<number>]' + '\n' + \
            'Parameter runs'
    parameter_index = None
    iteration_arg = None
    seed_arg = 0
    config_arg = None

    try:
        if len(argv) == 0:
            raise getopt.GetoptError("No input arguments")
        opts, args = getopt.getopt(argv, "hc:p:i:s:", ["help", "config=", "parameter_index=", "iteration=", "seed="])
        if len(opts) == 0:
            raise getopt.GetoptError("No option specified")
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(usage)
                sys.exit()
            elif opt in ("-p", "--parameter_index"):
                parameter_index = arg
            elif opt in ("-i", "--iteration"):
                iteration_arg = arg
            elif opt in ("-s", "--seed"):
                seed_arg = arg
            elif opt in ("-c", "--config"):
                config_arg = arg

    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    if parameter_index is None or iteration_arg is None or config_arg is None:
        print(usage)
        sys.exit(2)
    config_arg = os.path.abspath(config_arg)
    return str(config_arg), int(parameter_index), int(iteration_arg), float(seed_arg)


def get_data_rate(communication_standard: str, mcs: int, dcm: bool = False) -> float:
    """
    returns data rate belonging to communication standard and mcs combination
    @param communication_standard The used standard
    @param mcs The Modulation and Coding Scheme (MCS) index
    @param dcm Dual SubCarrier Modulation
    @return data rate in Byte/s
    """
    if communication_standard == "bd":
        # code rate and number of bits per symbol
        paket_size = 1500
        cr_nbps = {
            0: (0.5, 1),
            1: (0.5, 2),
            2: (0.75, 2),
            3: (0.5, 4),
            4: (0.75, 4),
            5: (2 / 3, 6),
            6: (0.75, 6),
            7: (5 / 6, 6),
            8: (3 / 4, 8),
            9: (5 / 6, 8),
        }
        cr = cr_nbps[mcs][0]
        nbps = cr_nbps[mcs][1]
        if dcm: nbps = nbps / 2
        nsym = math.ceil((paket_size * 8) / (52 * cr * nbps))
        if mcs < 5:
            tma = 8
        else:
            tma = 4
        nma = math.floor((nsym - 1) / tma)
        tx = 80 + 32 + 8 * nsym + 8 * nma
        tx = round(tx * 10 ** -3, 3)
        data_rate = round(((paket_size * 8) / (tx * 10 ** -3)) * 10 ** -6, 2)
    else:
        standards = {  # in Mbps
            "p": {
                0: 2.94,
                1: 4.37,
                2: 5.77,
                3: 8.52,
                4: 11.19,
                5: 16.13,
                6: 20.83,
                7: 23.08
            },
            "bd": {
                0: 3.02,
                1: 5.93,
                2: 8.72,
                3: 11.41,
                4: 16.57,
                5: 20.13,
                6: 22.22,
                7: 24.19,
                8: 28.30,
                9: 30.92
            },
            "lte": {
                0: 1.13,
                6: 4.22,
                7: 4.94,
                10: 7.09,
                13: 9.24,
                17: 12.88,
                21: 17.49,
                27: 25.77
            },
            "nr": {
                0: 1.70,
                6: 6.31,
                7: 7.36,
                10: 9.57,
                13: 13.67,
                17: 19.80,
                21: 27.34,
                27: 38.27
            }
        }
        data_rate = standards[communication_standard][mcs]  # in Mbps
    return (data_rate * 10 ** 6) / 8  # in bit # should be byte


def calculate_sinr_min(communication_standard: str, mcs: int, noisepower: int = 0, dcm: bool = False,
                       retr: bool = True) -> float:
    """
    Calculates the minimum Signal-to-Interference-Noise-Ratio
    @param communication_standard The V2V communication standard
    @param mcs The modulation and coding scheme (MCS)
    @param noisepower The power of noise
    @param dcm Dual SubCarrier Modulation
    @param retr Adaptive Retransmission
    @return Minimum SINR value

    """
    if communication_standard == "p" or communication_standard == "bd":
        min_input_sens = {
            0: -85,
            1: -84,
            2: -82,
            3: -80,
            4: -77,
            5: -73,
            6: -69,
            7: -68
        }
        sinr_min = min_input_sens[mcs] - noisepower
        if communication_standard == "bd":
            if mcs == 0:
                sinr_min = min_input_sens[mcs] - noisepower
            else:
                sinr_min = min_input_sens[mcs + 1] - noisepower
            sinr_min -= 3  # error correction, use of ldpc -> 3 db lower sensitivity
            if dcm:
                sinr_min -= 5  # dcm mode -> 5 db gain
            if retr:
                sinr_min -= 7  # adaptive retransmission -> 4-7 db
    else:
        if communication_standard == "lte":
            # data[0] = code_rate, data[1] = number bits per symbol
            data = {
                0: (0.13, 2),
                6: (0.47, 2),
                7: (0.55, 2),
                10: (0.81, 2),
                13: (0.52, 4),
                17: (0.75, 4),
                21: (0.65, 6),
                27: (0.93, 6)
            }
        elif communication_standard == "nr":
            # data[0] = code_rate, data[1] = number bits per symbol
            data = {
                0: (0.12, 2),
                6: (0.44, 2),
                7: (0.51, 2),
                10: (0.33, 4),
                13: (0.48, 4),
                17: (0.45, 6),
                21: (0.65, 6),
                27: (0.92, 6)
            }
        code_rate = data[mcs][0]
        nbps = data[mcs][1]
        bhz = (14 * 12 * nbps * code_rate) / 180
        res = 2 ** (bhz / (1 - 0.6)) - 1
        sinr_min = round(10 * math.log(res, 10), 1)
    return sinr_min


def calc_eta(mcs: int, standard: str) -> float:
    """
    Calculates Eta Bandwidth, the portion of the bandwith used for transmission. As not the whole bandwith is used for
    transmission, only parts of the noise are relevant.
    @param mcs The modulation and coding scheme (MCS)
    @param standard The cellular communication standard
    @return The Eta bandwith
    """
    if standard == "lte":
        nrb = {
            0: 434,
            6: 116,
            7: 99,
            10: 69,
            13: 53,
            17: 38,
            21: 28,
            27: 19
        }
        nrb_mcs = 2 * nrb[mcs]
    elif standard == "nr":
        nrb = {
            0: 337,
            6: 91,
            7: 78,
            10: 60,
            13: 42,
            17: 29,
            21: 21,
            27: 15
        }
        nrb_mcs = nrb[mcs]
    nsfr_message = math.ceil(nrb_mcs / 81)
    eta = (math.ceil(nrb_mcs / nsfr_message)) / 100
    return eta


def calculate_communication_range(transmission_power: float, gain: int, noisepower: int, pathloss: float,
                                  loss_exponent: float, communication_standard: str, mcs: int) -> int:
    """
        Calculates transmission range with several configuration values
        @param transmission_power transmission_power in dBm
        @param gain The gain in dB
        @param noisepower The noisepower in dBm
        @param pathloss The pathloss in dB
        @param loss_exponent The loss_exponent as float
        @param communication_standard The used standard
        @param mcs modulation and coding scheme (MCS)
        @return achievable transmission range in m
    """
    sinr_min = calculate_sinr_min(communication_standard, mcs, noisepower)
    if communication_standard == "lte" or communication_standard == "nr":
        eta = 10 * math.log(calc_eta(mcs, communication_standard), 10)
        communication_range = 10 ** ((transmission_power + 2 * gain - (sinr_min + pathloss + eta + noisepower)) / 10)
    elif communication_standard == "p" or communication_standard == "bd":
        communication_range = 10 ** ((transmission_power + 2 * gain - (sinr_min + pathloss + noisepower)) / 10)
    communication_range = communication_range ** (1 / loss_exponent)
    return round(communication_range)


def run(config: str, parameter_index: int, iteration_counter: int, seed: float) -> None:
    """
    Run a single simulation run.
    @param config File path to the configuration file
    @param parameter_index Index in the parameter list
    @param iteration_counter Number of iteration
    @param seed The random seed value
    """
    start_time = time.time()
    random.seed(seed)
    sumo_cfg, sumo_binary, number_vehicles, additional_vehicles, update_size, initial_seeds, v2v_distance, duration, \
        duration_parameter, output_abs_path, buildings_tuple, ap_placement, v2v_device, wlan_device, wlan_distance, \
        wlan_beacon_interval, v2v_heartbeat_interval, wlan_ap_count, wlan_heartbeat_strategy, v2v_heartbeat_strategy, \
        heartbeat_encoding, v2v_data_rate, wlan_data_rate, seeding_strategy, parameters, sumo_route, \
        communication_standard, mcs, additional_attenuation, ap_coords, max_number_connections, \
        v2v_equipment_percentage, wlan_equipment_percentage, wlan_ap_percentage \
        = parameter_parser.parse_parameter_xml(config, parameter_index)
    gain, transmission_power, pathloss, noisepower, loss_exponent, antenna_height, two_ray, log_distance, \
        log_shadow, shadow_slope, loss_exponent2, sigma, sigma2 = parameter_parser.parse_constants_xml(config)
    loss_exponent += additional_attenuation
    if communication_standard != "n/a":
        distance = calculate_communication_range(transmission_power, gain, noisepower, pathloss, loss_exponent,
                                                 communication_standard, mcs)
        data_rate = 60000
        v2v_distance = distance
        v2v_data_rate = data_rate
    else:
        distance = None
        data_rate = None
    pathlib.Path(output_abs_path).mkdir(parents=True, exist_ok=True)
    os.chdir(output_abs_path)
    sumo_cmd = [sumo_binary, "-c", sumo_cfg, "--seed", str(int(seed)), "-S"]
    traci.start(sumo_cmd)
    step = 0
    # chunk_size = 1411
    backend_server = Backend.Backend(1411, initial_seeds, number_vehicles, seeding_strategy)
    v2v_layer = None
    ism_layer = None
    if v2v_device and v2v_equipment_percentage > 0.0:
        v2v_layer = v2vNetworkingLayer.V2VNetworkingLayer(traci, distance, data_rate,
                                                          gain, transmission_power,
                                                          pathloss, noisepower, loss_exponent, antenna_height,
                                                          two_ray, log_distance,
                                                          log_shadow, shadow_slope, loss_exponent2, sigma, sigma2
                                                          )

    if wlan_device and wlan_equipment_percentage > 0.0:
        ism_layer = ismNetworkingLayer.ISMNetworkingLayer(traci)
    t = time.time()
    var_dump_file_name = time.strftime("%d%m%Y%H_%M_%S") + "_" + str(
        int(round(t * 1000))) + "_%i_%i_%i" % (
                             additional_vehicles, number_vehicles, duration_parameter)
    for value in parameters:
        if type(value) is float:
            var_dump_file_name += "_%i" % (int(value * 100))
        elif type(value) is str:
            var_dump_file_name += "_" + value.replace(' ', '_')
        else:
            var_dump_file_name += "_%i" % (int(value))
    var_dump_file_name += "_%i" % iteration_counter

    vehicle_fleet = fleetManager.FleetManager(traci, backend_server, v2v_layer, additional_vehicles, number_vehicles,
                                              duration_parameter, ism_layer, v2v_device, wlan_device,
                                              wlan_heartbeat_strategy, v2v_heartbeat_strategy, heartbeat_encoding,
                                              v2v_heartbeat_interval, v2v_distance, v2v_data_rate, var_dump_file_name,
                                              duration, wlan_distance, seed, sumo_route, v2v_equipment_percentage,
                                              wlan_equipment_percentage)

    if wlan_device and wlan_equipment_percentage > 0.0:
        wlan_manager = wlan_ap_manager.WlanAPManager(traci, wlan_ap_count, ism_layer, backend_server, buildings_tuple,
                                                     ap_placement, wlan_distance, wlan_beacon_interval, wlan_data_rate,
                                                     ap_coords, max_number_connections, wlan_ap_percentage, seed)
    generated_update = False
    finished = False
    update_data = {}
    update_names = []
    connected_vehicles = []
    try:
        while (duration and step <= duration_parameter * 10) or (not duration and not finished):

            traci.simulationStep()
            current_time = traci.simulation.getTime()

            if not generated_update:
                # size = 1000 * 1000 * 100  # 100 Megabyte
                filename = backend_server.generate_update(update_size)  # 100 Megabyte
                generated_update = True
                update_names.append(filename)
                update_data[filename] = [current_time, update_size, 1411]

            vehicle_fleet.arrived(traci.simulation.getArrivedIDList())
            vehicle_fleet.departed(traci.simulation.getDepartedIDList())
            if v2v_device and v2v_equipment_percentage > 0.0:
                v2v_layer.simulation_step(current_time)
            if wlan_device and wlan_equipment_percentage > 0.0:
                connected_vehicles.extend(ism_layer.simulation_step(current_time))
            finished = vehicle_fleet.update(current_time)

            step += 1

        with open("plotdata.txt", 'w', newline='') as r_file:
            writer = csv.writer(r_file)
            a, b, c = vehicle_fleet.get_plot_data()
            writer.writerow(a)
            writer.writerow(b)
            writer.writerow(c)


    except Exception as e:
        print("Unexpected error:", sys.exc_info()[0])
        print(e)
        traceback.print_tb(sys.exc_info()[2])
    else:
        with open(var_dump_file_name + '_update_data', 'w', newline='') as r_file:
            writer = csv.writer(r_file)
            writer.writerow(update_data.keys())
            writer.writerow(update_data.values())
        result_data = vehicle_fleet.get_used_file_names()
        result_file_name = 'results_%i_%i_%i' % (
            additional_vehicles, number_vehicles, duration_parameter)
        for value in parameters:
            if type(value) is float:
                result_file_name += "_%i" % (int(value * 100))
            elif type(value) is str:
                result_file_name += "_" + value.replace(' ', '_')
            else:
                result_file_name += "_%i" % (int(value))
        result_file_name += "_%i.csv" % iteration_counter
        with open(result_file_name, 'w', newline='') as r_file:
            writer = csv.writer(r_file)
            for element in result_data.values():
                for string in element:
                    writer.writerow([string])
            writer.writerow([var_dump_file_name + '_update_data'])

        for update_name in update_names:
            if os.path.isfile(update_name + ".dat"):
                os.remove(update_name + ".dat")
            if os.path.isfile(update_name + ".datmeta"):
                os.remove(update_name + ".datmeta")
        traci.close()
        end_time = time.time()
        with open(var_dump_file_name + "execution_time.txt", 'w') as f:
            f.write(str(end_time - start_time))

        with open(var_dump_file_name + "wlan_ap_connections.txt", 'w') as f:
            for element in connected_vehicles:
                f.write(str(element[0]) + " " + str(element[1]) + " " + str(element[2]) + "\n")


if __name__ == "__main__":
    config, par_index, iteration, seed = parse_options(sys.argv[1:])
    run(config, par_index, iteration, seed)
