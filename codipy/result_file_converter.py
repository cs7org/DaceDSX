import copy
import csv
import getopt
import json
import os
import sys
from itertools import groupby
from typing import List

import xmltodict as xdict


def parse_options(argv: List[str]) -> str:  # parse multiple logfiles, put plots, calculated values and traces in new directory
    """
    Parse command line options.
    @param argv List of command line arguments
    @return index in parameter variation, iteration
    """
    usage = 'usage: result_file_converter.py [-h | --help] [-c | --config=<str>]' + '\n' + \
            'Convert run files into result files'
    config = None

    try:
        if len(argv) == 0:
            raise getopt.GetoptError("No input arguments")
        opts, args = getopt.getopt(argv, "hc:", ["help", "config="])
        if len(opts) == 0:
            raise getopt.GetoptError("No option specified")
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(usage)
                sys.exit()
            elif opt in ("-c", "--config"):
                config = arg

    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    if config is None:
        print(usage)
        sys.exit(2)
    config = os.path.abspath(config)
    return str(config)


def run(configuration: str) -> None:
    """
    Run the result file converter
    @param configuration Configuration to use for conversion of result files
    """
    with open(configuration, 'rb') as config_file:
        xml_dict = xdict.parse(config_file)

    output_path_string = list(xml_dict['configuration']['output']['output-path'].values())[0]
    output_abs_path = os.path.abspath(output_path_string)
    os.chdir(output_abs_path)

    _, _, filenames = next(os.walk(output_abs_path))
    csv_files = []
    for entry in filenames:
        if entry.endswith(".csv") and entry.startswith("results_"):
            csv_files.append(entry)


    csv_files_sorted = sorted(csv_files, key=lambda x: x.split("_")[:-1])
    grouped_files = [list(g) for k, g in groupby(csv_files_sorted, key=lambda x: x.split("_")[:-1]) if k]

    for iterations_list in grouped_files:

        for i in iterations_list:
            file = i
            vehicleFleet_data = {}
            result_dict = {}
            number_vehicles = int(file.split("_")[2])
            for vehicle_counter in range(number_vehicles):
                dataLogging = {}
                dataLogging['heartbeat'] = []
                dataLogging['update_progress'] = {}
                dataLogging['reception'] = {}
                dataLogging['simulation'] = {}
                dataLogging['simulation']['departed'] = []
                dataLogging['simulation']['arrived'] = []
                dataLogging['wlan_reception'] = []
                dataLogging['wlan_ap_association'] = []
                key = ('vehicle' + str(vehicle_counter))
                vehicleFleet_data[key] = copy.copy(dataLogging)
            if not os.path.isfile(file):
                continue
            with open(file, 'r', newline='') as r_file:
                reader = csv.reader(r_file)
                file_names = []
                for row in reader:
                    for e in row:
                        file_names.extend(e.replace('[', '').replace(']', '').replace("'", '').split(', '))

                for entry in file_names:
                    #print(entry)
                    #print(file_names)
                    infile = open(entry, 'r')
                    if "update_data" in entry:
                        #with open(entry, 'r') as infile:
                        reader = csv.reader(infile)
                        line_1 = next(reader)[0]
                        line_2 = list(map(lambda x: float(x), next(reader)[0][1:-1].split(', ')))
                        result_dict['update_info'] = {line_1: line_2}
                    else:
                        for str_part in entry.split('_'):
                            if str_part.startswith("vehicle"):
                                veh = str_part
                                break
                        if 'heartbeat' in entry:
                            #with open(entry, 'r') as infile:
                            reader = csv.reader(infile)
                            for row in reader:
                                vehicleFleet_data[veh]['heartbeat'].append((float(row[0]), float(row[1])))
                        elif 'reception' in entry and not "wlan" in entry:
                            #with open(entry, 'r') as infile:
                            reader = csv.reader(infile)
                            from_vehicle = str(entry.split('_')[-1])
                            if from_vehicle not in vehicleFleet_data[veh]['reception']:
                                vehicleFleet_data[veh]['reception'][from_vehicle] = []
                            for row in reader:
                                vehicleFleet_data[veh]['reception'][from_vehicle].append((float(row[0]), str(row[1])))
                        elif 'reception' in entry and "wlan" in entry:
                            #with open(entry, 'r') as infile:
                            reader = csv.reader(infile)
                            for row in reader:
                                vehicleFleet_data[veh]['wlan_reception'].append((float(row[0]), str(row[1])))
                        elif "association" in entry:
                            #with open(entry, 'r') as infile:
                            reader = csv.reader(infile)
                            for row in reader:
                                vehicleFleet_data[veh]['wlan_ap_association'].append((float(row[0]), str(row[1]), str(row[2])))
                        elif 'update_progress' in entry:
                            #with open(entry, 'r') as infile:
                            reader = csv.reader(infile)
                            update = str('_'.join(entry.split('_')[-4:]))
                            if update not in vehicleFleet_data[veh]['update_progress']:
                                vehicleFleet_data[veh]['update_progress'][update] = []
                            for row in reader:
                                vehicleFleet_data[veh]['update_progress'][update].append((float(row[0]), int(row[1])))
                        elif 'simulation_departed' in entry:
                            #with open(entry, 'r') as infile:
                            reader = csv.reader(infile)
                            for row in reader:
                                vehicleFleet_data[veh]['simulation']['departed'].append(float(row[0]))
                        elif 'simulation_arrived' in entry:
                            #with open(entry, 'r') as infile:
                            reader = csv.reader(infile)
                            for row in reader:
                                vehicleFleet_data[veh]['simulation']['arrived'].append(float(row[0]))
                    infile.close()
                for f in file_names:
                    if os.path.isfile(f):
                        os.remove(f)
                if os.path.isfile(file):
                    os.remove(file)
            result_dict['vehicle_data'] = vehicleFleet_data
            result_file_name = file[:-4] + ".json"
            with open(result_file_name, "w") as outfile:
                json.dump(result_dict, outfile)


if __name__ == "__main__":
    config = parse_options(sys.argv[1:])
    run(config)