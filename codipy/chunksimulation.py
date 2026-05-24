import getopt
import sys
from subprocess import Popen
import time
from typing import List
import os
import xmltodict as xdict
from shutil import copy2
import itertools
import random


def parse_options(argv: List[str]) -> str:  # parse multiple logfiles, put plots, calculated values and traces in new directory
    """
    Parse command line options.
    @param argv: List of command line arguments
    @return: index in parameter variation, iteration
    """
    usage = 'usage: simulation_run.py [-h | --help] [-c | --config=<str>]' + '\n' + \
            'Experiment runs'
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
    number_vehicles = None
    additional_vehicles = None
    update_size = None
    initial_seeds = None
    iterations = None
    distance = None

    with open(configuration, 'rb') as config_file:
        xml_dict = xdict.parse(config_file)  # , process_namespaces=True)

    iterations = None
    randomness_fixed = None
    for parameter in xml_dict['configuration']['parameter']:
        if parameter == "iterations":
            iterations = int(list(xml_dict['configuration']['parameter']['iterations'].values())[0])
        if parameter == "fixed-randomness":
            randomness_fixed = True if list(xml_dict['configuration']['parameter']['fixed-randomness'].values())[0] == "true" else False
    print("rand", randomness_fixed)
    variation_key = list(xml_dict['configuration']['parameter-variation'].keys())[0]
    variation_keys = list(xml_dict['configuration']['parameter-variation'].keys())
    values_parameter = []

    for values in variation_keys:
        paras = list(xml_dict['configuration']['parameter-variation'][values].values())[0].split(", ")
        values_parameter.append(paras)

    number_processes = int(list(xml_dict['configuration']['processing']['processes'].values())[0])
    print(number_processes)
    processes = []
    wait = True
    seed = 0#time.time()

    for iteration in range(iterations):
        for index, variation in enumerate(itertools.product(*values_parameter)):
            print("seed is", seed)
            print("it", iteration, index, variation)
            p = Popen(['python3.11 simulation_run.py -c %s -p %i -i %i -s %f' % (configuration, index, iteration, seed)], shell=True)#,
            #                  stdout=sp.DEVNULL)  # stdout=sp.DEVNULL)
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
        if randomness_fixed:
            time.sleep(2)
            seed += 1#time.time()
    wait = True
    while wait:
        for p in processes:
            if p.poll() is not None:
                processes.remove(p)
        if len(processes) == 0:
            wait = False
        if wait:
            time.sleep(5)
    try:
        copy2(configuration, list(xml_dict['configuration']['output']['output-path'].values())[0] + "/config.xml")
    except:
        pass
    if list(xml_dict['configuration']['output']['result-file-conversion'].values())[0] == 'true':
        p = Popen(['python3.11 result_file_converter.py -c %s' % list(xml_dict['configuration']['output']['output-path'].values())[0] + "/config.xml"], shell=True)#, stdout=sp.DEVNULL)


if __name__ == "__main__":
    config = parse_options(sys.argv[1:])
    run(config)