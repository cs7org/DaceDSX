from typing import List, Tuple
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
from TraCInterface import TraCIInterface, register_access_points_from_file
from CodipyWrapper.CodipyWrapper import CodipyWrapper


def parse_options(argv: List[str]) -> Tuple[str, str, str]:
    """
    Parse command line options for passive-mode operation.
    
    Args:
        argv: List of command line arguments
        
    Returns:
        Tuple of (config_file_path, scenario_id, instance_id)
    """
    usage = 'usage: simulation_run.py [-h | --help] [-c | --config=<str>] [-s | --scenario=<str>] [-i | --instance=<str>]\n' \
            'Passive Mode CoDiPy Runtime'
    config_arg = None
    scenario_arg = None
    instance_arg = None

    try:
        if len(argv) == 0:
            raise getopt.GetoptError("No input arguments")
        opts, args = getopt.getopt(argv, "hc:s:i:", ["help", "config=", "scenario=", "instance="])
        if len(opts) == 0:
            raise getopt.GetoptError("No option specified")
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(usage)
                sys.exit()
            elif opt in ("-c", "--config"):
                config_arg = arg
            elif opt in ("-s", "--scenario"):
                scenario_arg = arg
            elif opt in ("-i", "--instance"):
                instance_arg = arg

    except getopt.GetoptError as e:
        print(f"Error: {e}")
        print(usage)
        sys.exit(2)
        
    if config_arg is None or scenario_arg is None or instance_arg is None:
        print("Error: All arguments (--config, --scenario, --instance) are required")
        print(usage)
        sys.exit(2)
        
    config_arg = os.path.abspath(config_arg)
    return str(config_arg), str(scenario_arg), str(instance_arg)


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


def run_passive(config: str, scenario_id: str, instance_id: str) -> None:
    """
    Run CoDiPy in passive mode - consumes vehicle telemetry from Kafka.
    
    Args:
        config: File path to the configuration file
        scenario_id: Scenario identifier (for Kafka topics)
        instance_id: Instance identifier (for Kafka consumer group)
    """
    print(f"Starting CoDiPy in PASSIVE MODE")
    print(f"   Scenario ID: {scenario_id}")
    print(f"   Instance ID: {instance_id}")
    print(f"   Config: {config}")
    print("-" * 60)
    
    start_time = time.time()
    
    # Parse configuration (use parameter_index=0 for default parameters)
    parameter_index = 0
    try:
        _, _, number_vehicles, additional_vehicles, update_size, initial_seeds, v2v_distance, duration, \
            duration_parameter, output_abs_path, buildings_tuple, ap_placement, v2v_device, wlan_device, wlan_distance, \
            wlan_beacon_interval, v2v_heartbeat_interval, wlan_ap_count, wlan_heartbeat_strategy, v2v_heartbeat_strategy, \
            heartbeat_encoding, v2v_data_rate, wlan_data_rate, seeding_strategy, _, _, \
            communication_standard, mcs, additional_attenuation, ap_coords, max_number_connections, \
            v2v_equipment_percentage, wlan_equipment_percentage, wlan_ap_percentage \
            = parameter_parser.parse_parameter_xml(config, parameter_index)
        gain, transmission_power, pathloss, noisepower, loss_exponent, antenna_height, two_ray, log_distance, \
            log_shadow, shadow_slope, loss_exponent2, sigma, sigma2 = parameter_parser.parse_constants_xml(config)
    except Exception as e:
        print(f"Failed to parse configuration: {e}")
        raise
    
    # Calculate communication range if standard is specified
    loss_exponent += additional_attenuation
    if communication_standard != "n/a":
        distance = calculate_communication_range(transmission_power, gain, noisepower, pathloss, loss_exponent,
                                                 communication_standard, mcs)
        data_rate = 60000
        v2v_distance = distance
        v2v_data_rate = data_rate
    else:
        distance = v2v_distance
        data_rate = v2v_data_rate
    
    # Create output directory
    pathlib.Path(output_abs_path).mkdir(parents=True, exist_ok=True)
    os.chdir(output_abs_path)
    
    print(f"Configuration loaded:")
    print(f"   V2V distance: {v2v_distance}m")
    print(f"   WLAN distance: {wlan_distance}m")
    print(f"   Number of vehicles: {number_vehicles}")
    print(f"   WLAN AP count: {wlan_ap_count}")
    print(f"   AP coordinates file: {ap_coords}")
    print("-" * 60)
    
    # Step length from config (default 0.1 seconds)
    step_length = 0.1
    
    # Initialize CodipyWrapper (passive data pipeline)
    print("Initializing CodipyWrapper...")
    try:
        wrapper = CodipyWrapper(
            scenarioID=scenario_id,
            instanceID=instance_id,
            step_length_seconds=step_length
        )
        wrapper.prepare()
        print("CodipyWrapper initialized and connected to Kafka")
    except Exception as e:
        print(f"Failed to initialize CodipyWrapper: {e}")
        raise
    
    # Get TraCIInterface from wrapper
    traci_interface = wrapper.traci_interface
    
    # Register Access Points if configured
    if wlan_device and wlan_equipment_percentage > 0.0 and ap_coords:
        print(f"Registering WLAN Access Points from {ap_coords}...")
        try:
            ap_count = register_access_points_from_file(traci_interface, ap_coords)
            print(f"Registered {ap_count} access points")
        except Exception as e:
            print(f"Failed to register access points: {e}")
            print("   Continuing without access points...")
    
    # Initialize Backend server
    # Estimated vehicle count for seeding (hint only, not enforced)
    estimated_vehicles = number_vehicles if number_vehicles > 0 else 36  # Default estimate
    backend_server = Backend.Backend(1411, initial_seeds, estimated_vehicles, seeding_strategy)
    print(f"Backend server initialized (estimated vehicles for seeding: {estimated_vehicles})")
    
    # Initialize networking layers
    v2v_layer = None
    ism_layer = None
    
    if v2v_device and v2v_equipment_percentage > 0.0:
        print(f"Initializing V2V networking layer (range: {v2v_distance}m)...")
        v2v_layer = v2vNetworkingLayer.V2VNetworkingLayer(
            traci_interface, distance, data_rate,
            gain, transmission_power,
            pathloss, noisepower, loss_exponent, antenna_height,
            two_ray, log_distance,
            log_shadow, shadow_slope, loss_exponent2, sigma, sigma2
        )
        print("V2V layer initialized")
    
    if wlan_device and wlan_equipment_percentage > 0.0:
        print(f"Initializing WLAN/ISM networking layer (range: {wlan_distance}m)...")
        ism_layer = ismNetworkingLayer.ISMNetworkingLayer(traci_interface)
        print("WLAN/ISM layer initialized")
    
    # Generate output filenames
    t = time.time()
    var_dump_file_name = time.strftime("%d%m%Y%H_%M_%S") + "_" + str(int(round(t * 1000)))
    var_dump_file_name += f"_{scenario_id}_{instance_id}"
    
    # Initialize FleetManager
    print("Initializing FleetManager...")
    # Set number_vehicles=0 to signal passive mode (prevents vehicle spawning)
    vehicle_fleet = fleetManager.FleetManager(
        traci_interface, backend_server, v2v_layer, additional_vehicles, 
        0,  # number_vehicle=0 (passive mode)
        0,  # number_routes=0 (passive mode)
        ism_layer, v2v_device, wlan_device,
        wlan_heartbeat_strategy, v2v_heartbeat_strategy, heartbeat_encoding,
        v2v_heartbeat_interval, v2v_distance, v2v_data_rate, var_dump_file_name,
        duration, wlan_distance, 1.0, None, v2v_equipment_percentage,
        wlan_equipment_percentage
    )
    print("FleetManager initialized (passive mode: dynamic vehicle count)")
    
    # Initialize WLAN AP Manager (if enabled)
    wlan_manager = None
    if wlan_device and wlan_equipment_percentage > 0.0:
        print("Initializing WLAN AP Manager...")
        wlan_manager = wlan_ap_manager.WlanAPManager(
            traci_interface, wlan_ap_count, ism_layer, backend_server, buildings_tuple,
            ap_placement, wlan_distance, wlan_beacon_interval, wlan_data_rate,
            ap_coords, max_number_connections, wlan_ap_percentage, 0
        )
        print("WLAN AP Manager initialized")
    
    print("-" * 60)
    print("All components initialized successfully!")
    print("Starting passive monitoring loop...")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    # Start wrapper (non-blocking - starts Kafka consumer in background)
    wrapper.start()
    
    # Passive monitoring loop
    step = 0
    generated_update = False
    update_data = {}
    update_names = []
    connected_vehicles = []
    status_interval = 100  # Print status every N steps
    
    try:
        # Main simulation loop
        while True:
            # Advance wrapper one step (processes Kafka messages)
            should_continue = wrapper.step()
            
            if not should_continue:
                print("\nSimulation time limit reached")
                break
            
            # Get current simulation time from TraCI interface
            current_time = traci_interface.simulation.getTime()
            
            # Generate update file on first step
            if not generated_update:
                filename = backend_server.generate_update(update_size)
                generated_update = True
                update_names.append(filename)
                update_data[filename] = [current_time, update_size, 1411]
            
            # Process arrivals and departures
            vehicle_fleet.arrived(traci_interface.simulation.getArrivedIDList())
            vehicle_fleet.departed(traci_interface.simulation.getDepartedIDList())
            
            # Update networking layers
            if v2v_device and v2v_equipment_percentage > 0.0:
                v2v_layer.simulation_step(current_time)
            if wlan_device and wlan_equipment_percentage > 0.0:
                connected_vehicles.extend(ism_layer.simulation_step(current_time))
            
            # Update vehicle fleet
            finished = vehicle_fleet.update(current_time)
            
            # Print status periodically
            if step % status_interval == 0:
                active_count = len(traci_interface.vehicles)
                print(f"Step {step:5d} | Time: {current_time:7.2f}s | Active vehicles: {active_count:3d}")
            
            step += 1
            
    except KeyboardInterrupt:
        print("\nReceived interrupt signal, shutting down...")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        print("\nCleaning up resources...")
        wrapper.stop()
        time.sleep(0.5)
        print("Resources cleaned up")
        print("\nSaving results...")
        
        # Save plot data
        try:
            with open("plotdata.txt", 'w', newline='') as r_file:
                writer = csv.writer(r_file)
                a, b, c = vehicle_fleet.get_plot_data()
                writer.writerow(a)
                writer.writerow(b)
                writer.writerow(c)
            print("Plot data saved")
        except Exception as e:
            print(f"Failed to save plot data: {e}")
        
        try:
            result_data = vehicle_fleet.get_used_file_names()
            result_file_name = 'results_%i_%i_%i.csv' % (additional_vehicles, number_vehicles, duration_parameter)
            with open(result_file_name, 'w', newline='') as r_file:
                writer = csv.writer(r_file)
                for element in result_data.values():
                    for string in element:
                        writer.writerow([string])
                writer.writerow([var_dump_file_name + '_update_data'])
            print(f"Results CSV saved to {result_file_name}")
        except Exception as e:
            print(f"Failed to save results CSV: {e}")
            traceback.print_exc()
        
        # Save update data
        try:
            with open(var_dump_file_name + '_update_data', 'w', newline='') as r_file:
                writer = csv.writer(r_file)
                writer.writerow(update_data.keys())
                writer.writerow(update_data.values())
            print("Update data saved")
        except Exception as e:
            print(f"Failed to save update data: {e}")
        
        # Cleanup update files
        for update_name in update_names:
            try:
                if os.path.isfile(update_name + ".dat"):
                    os.remove(update_name + ".dat")
                if os.path.isfile(update_name + ".datmeta"):
                    os.remove(update_name + ".datmeta")
            except Exception as e:
                print(f"Failed to cleanup {update_name}: {e}")
        
        end_time = time.time()
        duration_seconds = end_time - start_time
        
        try:
            with open(var_dump_file_name + "execution_time.txt", 'w') as f:
                f.write(str(duration_seconds))
            print(f"Execution time saved: {duration_seconds:.2f} seconds")
        except Exception as e:
            print(f"Failed to save execution time: {e}")
        
        try:
            with open(var_dump_file_name + "wlan_ap_connections.txt", 'w') as f:
                for element in connected_vehicles:
                    f.write(str(element[0]) + " " + str(element[1]) + " " + str(element[2]) + "\n")
            print("WLAN connection data saved")
        except Exception as e:
            print(f"Failed to save WLAN connection data: {e}")
        
        print("-" * 60)
        print(f"CoDiPy passive mode completed")
        print(f"   Total runtime: {duration_seconds:.2f} seconds")
        print(f"   Total steps: {step}")
        print(f"   Output directory: {output_abs_path}")
        print("-" * 60)


if __name__ == "__main__":
    config, scenario_id, instance_id = parse_options(sys.argv[1:])
    run_passive(config, scenario_id, instance_id)
