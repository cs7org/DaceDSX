import getopt
import itertools
import pathlib
import sys
from shutil import copy2
from subprocess import Popen
import time
from typing import List
import os
import xmltodict as xdict


def parse_options(argv: List[str]) -> str:
    """
    Parse command line options.
    @param argv: List of command line arguments
    @return: index in parameter variation, iteration
    """
    usage = 'usage: experiments_runner.py [-h | --help] [-c | --config_folder=<str>]' + '\n' + \
            'Runs multiple experiments'
    config_folder = None

    try:
        if len(argv) == 0:
            raise getopt.GetoptError("No input arguments")
        opts, args = getopt.getopt(argv, "hc:", ["help", "config_folder="])
        if len(opts) == 0:
            raise getopt.GetoptError("No option specified")
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                print(usage)
                sys.exit()
            elif opt in ("-c", "--config"):
                config_folder = arg

    except getopt.GetoptError:
        print(usage)
        sys.exit(2)
    if config_folder is None:
        print(usage)
        sys.exit(2)
    config_folder = os.path.abspath(config_folder)
    return str(config_folder)


def run(configuration_directory: str) -> None:
    print(configuration_directory)
    _, _, filenames = next(os.walk(configuration_directory))
    processes = []
    number_processes = 16
    number_processes_result_conversion = 4

    process_dict = {}
    run_combinations = []
    result_conversion = []
#    seed_values = [1, 2, 4, 6, 7, 13]
 #   counter = 0
    for config_file_name in filenames:
        if not config_file_name.startswith("config"):
            continue
        seed = 0 #seed_values[counter]  # 421103210#time.time()
  #      counter = 0
        config_file_name = os.path.abspath(configuration_directory + '/' + config_file_name)
        with open(config_file_name, 'rb') as config_file:
            xml_dict = xdict.parse(config_file)  # , process_namespaces=True)
        output_abs_path = None
        if list(xml_dict['configuration']['output']['result-file-conversion'].values())[0] == 'true':
            output_path_string = list(xml_dict['configuration']['output']['output-path'].values())[0]
            result_conversion.append(output_path_string)
            output_abs_path = os.path.abspath(output_path_string)

        iterations = None
        randomness_fixed = None
        for parameter in xml_dict['configuration']['parameter']:
            if parameter == "iterations":
                iterations = int(list(xml_dict['configuration']['parameter']['iterations'].values())[0])
            if parameter == "fixed-randomness":
                randomness_fixed = True if list(xml_dict['configuration']['parameter']['fixed-randomness'].values())[
                                               0] == "true" else False
        print("rand", randomness_fixed)
        variation_key = list(xml_dict['configuration']['parameter-variation'].keys())[0]
        variation_keys = list(xml_dict['configuration']['parameter-variation'].keys())
        values_parameter = []

        for values in variation_keys:
            paras = list(xml_dict['configuration']['parameter-variation'][values].values())[0].split(", ")
            values_parameter.append(paras)
        for iteration in range(iterations):
            for index, variation in enumerate(itertools.product(*values_parameter)):
                run_combinations.append(tuple([config_file_name, index, iteration, seed]))
            seed += 1
        try:
            pathlib.Path(output_abs_path).mkdir(parents=True, exist_ok=True)
            copy2(config_file_name, output_abs_path + "/config.xml")
        except Exception as err:
            #print(Exception, err)
            pass

    for config_file_name, index, iteration, seed in run_combinations:
        p = Popen(['python3.11 simulation_run.py -c %s -p %i -i %i -s %f' % (config_file_name, index, iteration, seed)],
                  shell=True)  # ,stdout=sp.DEVNULL)  # stdout=sp.DEVNULL)
        processes.append(p)
        number_processes -= 1
        print(len(processes), number_processes, index, iteration)
        if number_processes == 0:
            wait = True
            while wait:
                for p in processes:
                    if p.poll() is not None:
                        processes.remove(p)
                        number_processes += 1
                        wait = False
                if wait:
                    time.sleep(10)
    wait = True
    while wait:
        for p in processes:
            if p.poll() is not None:
                processes.remove(p)
        if len(processes) == 0:
            wait = False
        if wait:
            time.sleep(10)
    for result_c in result_conversion:
        p = Popen(['python3.11 result_file_converter.py -c %s' % result_c + "/config.xml"], shell=True)  # , stdout=sp.DEVNULL)
        processes.append(p)
        number_processes_result_conversion -= 1
        if number_processes_result_conversion == 0:
            wait = True
            while wait:
                for p in processes:
                    if p.poll() is not None:
                        processes.remove(p)
                        number_processes_result_conversion += 1
                        wait = False
                if wait:
                    time.sleep(10)
    wait = True
    while wait:
        for p in processes:
            if p.poll() is not None:
                processes.remove(p)
        if len(processes) == 0:
            wait = False
        if wait:
            time.sleep(10)

if __name__ == "__main__":
    configs = parse_options(sys.argv[1:])
    run(configs)
