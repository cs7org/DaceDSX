import math
import os
import time
from typing import List, Dict
import xml.etree.cElementTree as ET

import numpy as np

import ISMNetworkingLayer
from V2VNetworkingLayer import V2VNetworkingLayer
import ISMNetworkingLayer as ismNetworkingLayer
import random
import string
import sys
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from Vehicle import Vehicle


class FleetManager:
    """
    @brief Fleet Manager
    @author Michael Niebisch
    @bug No known bugs

    Class defining the fleet manager in charge of managing all vehicles, communicating and others.

    """

    def create_routes(self, number_of_routes: int, veh_id: str) -> list:
        """
        Creates a defined number of routes in TraCI
        @param number_of_routes Number of routes to be created
        @param veh_id ID of the Vehicle object
        @return: list of routes
        """
        result_list = []
        if False:  # Quick hack, use if a route file should be created (Simulation can not keep running after this)
            self.create_continuous_routes(veh_id)
            sys.exit()
        for i in range(0, number_of_routes):
            while True:
                edge_from = self.__rng.choice(self.__edge_ids)
                edge_to = self.__rng.choice(self.__edge_ids)
                try:
                    route = self.__traci.simulation.findRoute(edge_from, edge_to, "DEFAULT_VEHTYPE")
                except:  # TraCI will throw an error if there is no route between the edges.
                    continue
                if len(list(route.edges)) > 0:
                    # use random chars as strings, as route name has to be unique
                    route_name = ''.join(self.__rng.choices(string.ascii_uppercase + string.digits, k=20))
                    self.__traci.route.add(route_name, list(route.edges))
                    result_list.append(route_name)
                    break
        return result_list

    def create_route_file(self, veh_id: str, calculated_routes: List):
        """
        Creates a route file for a given vehicle and routes
        USE AT OWN RISK
        @param veh_id Vehicle ID
        @param calculated_routes List of routes
        """
        filename_routes = "filename9.xml"
        if not self.__route_file_created:
            routes = ET.Element("routes")
            ET.SubElement(routes, "vType",
                          attrib={"id": "vtype0", "accel": "2.6", "decel": "4.5", "sigma": "0.5", "length": "2.5",
                                  "minGap": "2.5", "maxSpeed": "14", "color": "1,1,0"})
            tree = ET.ElementTree(routes)
            tree.write(filename_routes)
            self.__route_file_created = True
        tree = ET.parse(filename_routes)
        print(tree)
        routes = tree.getroot()

        vehicle = ET.SubElement(routes, "vehicle",
                                attrib={"id": veh_id, "type": "vtype0", "depart": "0.0", "departPos": "random_free"})
        route_name = ''.join(self.__rng.choices(string.ascii_uppercase + string.digits, k=20))
        ET.SubElement(vehicle, "route", attrib={"id": route_name, "edges": ' '.join(
            calculated_routes)})  # "departPos": "free", "departSpeed" : "random",

        tree = ET.ElementTree(routes)
        tree.write(filename_routes)

    def create_continuous_routes(self, veh_id: str) -> List:
        """
        Create continuous routes for a vehicle
        USE AT OWN RISK
        @param veh_id Vehicle ID
        @return List of edges in route
        """
        result_list = []
        added_travel_time = 0.0
        min_travel_time = 3600.0
        last_end_edge = None
        cwd = os.getcwd()
        path_routes = "{}/../../routes".format(cwd)
        path_routes = "/home/niebisch/Documents/chunksimulation/validation_tests"
        filename = "{}/routes_iteration.json".format(path_routes)
        root = ET.Element("root")
        doc = ET.SubElement(root, "doc")
        edges = []
        while added_travel_time < min_travel_time * 1.25:
            if last_end_edge is None:
                edge_from = self.__rng.choice(self.__edge_ids)
            else:
                edge_from = last_end_edge
            edge_to = self.__rng.choice(self.__edge_ids)
            if ":" in edge_to or ":" in edge_from:
                continue
            try:
                route = self.__traci.simulation.findRoute(edge_from, edge_to, "DEFAULT_VEHTYPE")
            except:  # TraCI will throw an error if there is no route between the edges.
                continue
            if len(list(route.edges)) > 0:
                # use random chars as strings, as route name has to be unique
                route_name = ''.join(self.__rng.choices(string.ascii_uppercase + string.digits, k=20))
                if len(edges) == 0:
                    edges.extend(route.edges)
                else:
                    edges.extend(route.edges[1:])
                self.__traci.route.add(route_name, list(route.edges))
                result_list.append(route_name)
                added_travel_time += route.travelTime
                last_end_edge = edge_to

        print(added_travel_time)
        if not self.__route_file_created:
            tree = ET.ElementTree(root)
            tree.write("filename9.xml")
        self.create_route_file(veh_id, edges)
        return result_list

    def add_additional_vehicle(self) -> None:
        """
        Add an additional vehicle to the simulation.
        """
        self.__traci.vehicle.add("randomVehicle%i" % self.__currentNumberOfAdditionalVehicles_index,
                                 self.create_routes(1)[0])
        self.__currentNumberOfAdditionalVehicles += 1
        self.__currentNumberOfAdditionalVehicles_index += 1

    def add_vehicle(self) -> None:
        """
        Add a communicating vehicle to the simulation.
        """
        veh = Vehicle("vehicle%i" % self.__currentNumberOfVehicles, self, self.__file_name)
        veh.set_backend_server(self.__backendServer)
        self.__allVehicles.append(veh)

        if self.__sumo_route is None:
            veh.set_routes(self.create_routes(self.__maximumNumberOfRoutes, veh.get_veh_id()))
            veh.set_scheduled()
            self.__traci.vehicle.add("vehicle%i" % self.__currentNumberOfVehicles, veh.get_current_route())
        self.__currentNumberOfVehicles = self.__currentNumberOfVehicles + 1

    def get_backend_server(self):
        """
        Get the used Backend
        @return The Backend
        """
        return self.__backendServer

    def update(self, current_time: float) -> bool:
        """
        Update all vehicles in every time step
        @param current_time: current simulation time
        @return: True if all communicating vehicles have left the simulation, False otherwise
        """
        self.__current_time = current_time
        # Add vehicles until the required number is added.
        while self.__currentNumberOfVehicles != self.__numberOfVehicles:
            self.add_vehicle()
            print("Added Vehicle")
        while self.__currentNumberOfAdditionalVehicles != self.__numberOfAdditionalVehicles:
            self.add_additional_vehicle()
        # See if vehicles need to be scheduled to depart
        number_of_unfinished_vehicles = len(self.__allVehicles)
        progress = []
        progress_all_veh = 0
        output = round(current_time, 2) % 100.0 == 0
        for veh in self.__allVehicles:
            if current_time >= veh.get_next_route_start() and not veh.is_scheduled() and not veh.is_on_road() and veh.has_next_route():
                veh.set_scheduled()
                self.__traci.vehicle.add(veh.get_veh_id(), veh.update_route())
            if not veh.has_next_route() and not veh.is_on_road() and not veh.is_scheduled() and self.__duration:
                veh.set_routes(self.create_routes(self.__maximumNumberOfRoutes, veh.get_veh_id()))
                print("Simulation", self.__v2v_heartbeat_strategy, "Vehicle", veh.get_veh_id(), "on route",
                      veh.get_current_route(), "at", self.__current_time)
                veh.set_scheduled()
                self.__traci.vehicle.add(veh.get_veh_id(), veh.get_current_route())
            if not veh.has_next_route() and not veh.is_on_road() and not veh.is_scheduled() and not self.__duration:
                number_of_unfinished_vehicles -= 1
            if veh.is_on_road():
                veh.simulation_step(current_time)
            for update in veh.getUpdate():
                if output:
                    progress.append(
                        round(len(veh.getUpdate()[update].keys()) / veh.getMetaUpdate()[update]['numberOfChunks'] * 100,
                              4))
                progress_all_veh += len(veh.getUpdate()[update].keys())
        if output:
            print("\nStrategy:", self.__v2v_heartbeat_strategy)
            print("Update status at time:", current_time)
            for index, value in enumerate(self.__allVehicles):
                print("\t", value.get_veh_id() + ":\t", progress[index])

        self.update_progress_fleet = int(progress_all_veh / self.__numberOfVehicles)

        self.__plot_times.append(self.__current_time)
        self.__plot_values.append(self.update_progress_fleet)
        self.__plot_real_time.append(time.time())

        return number_of_unfinished_vehicles == 0

    def getUpdateState(self) -> int:
        """
        Returns the update progress of all Vehicle
        @return Number of received chunks across all vehicles
        """
        progress_all_veh = 0
        for veh in self.__allVehicles:
            for update in veh.getUpdate():
                progress_all_veh += len(veh.getUpdate()[update].keys())
        return progress_all_veh

    @staticmethod
    def vehicle_in_list(vehicle_name: str, list_value: List) -> bool:
        """
        Checks if a vehicle ID is in a list of vehicle objects
        @param vehicle_name A Vehicle ID
        @param list_value A list of Vehicle
        @return True if vehicle is in the list, False otherwise
        """
        for entry in list_value:
            if entry.get_veh_id() == vehicle_name:
                return True
        return False

    def departed(self, departed_list: List[str]) -> None:
        """
        Call this method with a list of the IDs of the departed vehicles in the last time step. 
        @param departed_list list of Vehicle IDs
        """
        for entry in list(departed_list):
            if len(self.__allVehicles) > 0 and self.vehicle_in_list(entry, self.__allVehicles):
                veh = self.__allVehicles[self.__allVehicles.index(entry)]
                # Add the departed vehicle to the communication layer
                if self.__ismNetworkingLayer is not None and self.get_wlan_device(veh.get_veh_id()):
                    self.__ismNetworkingLayer.add_vehicle(veh)
                if self.__v2v_layer is not None and self.get_v2v_device(veh.get_veh_id()):
                    self.__v2v_layer.add_vehicle(veh)
                #
                veh.set_departed(self.__current_time)
                # Add a TraCI subscription for the vehicle
                self.__traci.vehicle.subscribeContext(veh.get_veh_id(), self.__traci.constants.CMD_GET_VEHICLE_VARIABLE,
                                                      self.__v2v_communicationDistance,
                                                      [self.__traci.constants.VAR_SPEED,
                                                       self.__traci.constants.VAR_POSITION])

                print(veh.get_veh_id(), "departed")

    def get_current_time(self) -> float:
        """
        Get the current simulation time
        @return current simulation time
        """
        return self.__current_time

    def arrived(self, arrived_list: List[str]) -> None:
        """
        Call this method with a list of the IDs of the arrived vehicles in the last time step.
        @param arrived_list list of Vehicle IDs
        """
        for entry in list(arrived_list):
            if entry.startswith("randomVehicle"):
                self.__currentNumberOfAdditionalVehicles -= 1
            if len(self.__allVehicles) > 0 and self.vehicle_in_list(entry, self.__allVehicles):
                veh = self.__allVehicles[self.__allVehicles.index(entry)]
                # Remove arrived vehicles from the communication layer.
                if self.__v2v_layer is not None and self.get_v2v_device(veh.get_veh_id()):
                    self.__v2v_layer.remove_vehicle(veh)
                if self.__ismNetworkingLayer is not None and self.get_wlan_device(veh.get_veh_id()):
                    self.__ismNetworkingLayer.remove_vehicle(veh)
                if self.__current_time is None:
                    self.__current_time = self.__traci.simulation.getTime()
                    veh.set_arrived(self.__current_time)
                else:
                    veh.set_arrived(self.__current_time)
                print(veh.get_veh_id(), "arrived")

    def get_used_file_names(self) -> Dict[str, str]:
        """
        Get the used file names of all the vehicles.
        @return A dict of IDs and file names
        """
        result = {}
        for veh in self.__allVehicles:
            result[veh.get_veh_id()] = list(veh.get_used_file_names())
        return result

    def get_traci(self):
        """
        Get the TraCI interface
        @return TraCI object
        """
        return self.__traci

    def get_v2v_device(self, veh_id: str) -> bool:
        """
        Check if the Vehicle has a V2V Communication Module
        @return True if the Vehicle is equipped with a V2VModuleVehicle, False otherwise
        """
        id_of_vehicle = int(veh_id.strip("vehicle"))
        return self.__v2v_modules_list[id_of_vehicle]

    def get_wlan_device(self, veh_id):
        """
        Check if the Vehicle has a WLAN Communication Module
        @return True if the Vehicle is equipped with a WLANModuleVehicle, False otherwise
        """
        id_of_vehicle = int(veh_id.strip("vehicle"))
        return self.__wlan_modules_list[id_of_vehicle]

    def get_wlan_heartbeat_strategy(self) -> int:
        """
        Get the current WLAN Heartbeat Strategy
        @return Integer encoded strategy
        """
        if self.__wlan_heartbeat_strategy == "random":
            return 0
        elif self.__wlan_heartbeat_strategy == "counter":
            return 1
        elif self.__wlan_heartbeat_strategy == "weighted counter":
            return 2
        elif self.__wlan_heartbeat_strategy == "most recent":
            return 3
        elif self.__wlan_heartbeat_strategy == "most requested":
            return 4

    def get_v2v_heartbeat_strategy(self) -> int:
        """
        Get the current V2V Heartbeat Strategy
        @return Integer encoded strategy
        """
        if self.__v2v_heartbeat_strategy == "earliest":
            return 0
        elif self.__v2v_heartbeat_strategy == "counter":
            return 1
        elif self.__v2v_heartbeat_strategy == "counter relevance weighted":
            return 2
        elif self.__v2v_heartbeat_strategy == "counter time weighted":
            return 3
        elif self.__v2v_heartbeat_strategy == "random":
            return 4
        elif self.__v2v_heartbeat_strategy == "most relevant":
            return 5
        elif self.__v2v_heartbeat_strategy == "most recent":
            return 6

    def get_heartbeat_encoding(self) -> int:
        """
        Get the current Heartbeat Encoding
        @return Integer encoded Encoding Scheme
        """
        if self.__heartbeat_encoding == "rle":
            return 0
        elif self.__heartbeat_encoding == "bitmask":
            return 1
        elif self.__heartbeat_encoding == "hybrid":
            return 2

    def get_ism_networking_layer(self) -> ISMNetworkingLayer:
        """
        Get the ISM / WLAN networking layer
        @return ISM Networking Layer
        """
        return self.__ismNetworkingLayer

    def get_v2v_heartbeat_interval(self) -> float:
        """
        Get the V2V Heartbeat interval
        @return The interval time
        """
        return self.__v2v_heartbeat_interval

    def get_v2v_data_rate(self) -> int:
        """
        Get the V2V data rate
        @return V2V data rate
        """
        return self.__v2v_data_rate

    def get_all_vehicles(self) -> List:
        """
        Get a list of all vehicles
        @return List of all vehicles
        """
        return self.__allVehicles

    def get_update_progress_fleet(self) -> int:
        """
        Helper for RL to get the current update progress across the vehicle fleet
        @return current update status in fleet
        """
        return self.update_progress_fleet

    def update_seeding(self, current_time: float, seeding_number: int) -> (bool, List[int], int):
        """
        Update all vehicles in seeding timestep, used for reinforcement learning @param current_time current
        simulation time @param seeding_number Number of seeds to be seeded @return True if all communicating vehicles
        have left the simulation, False otherwise, downloading progress of each vehicle, and average of downloaded
        chunks in timestep
        """
        self.__current_time = current_time

        # Add vehicles until the required number is added.
        while self.__currentNumberOfVehicles != self.__numberOfVehicles:
            self.add_vehicle()
        while self.__currentNumberOfAdditionalVehicles != self.__numberOfAdditionalVehicles:
            self.add_additional_vehicle()

        progress_all_veh = 0
        progress_veh_list = []
        loaded_chunks = 0
        for veh in self.__allVehicles:
            if current_time >= veh.get_next_route_start() and not veh.is_scheduled() and not veh.is_on_road() and veh.has_next_route():
                veh.set_scheduled()
                self.__traci.vehicle.add(veh.get_veh_id(), veh.update_route())
            if not veh.has_next_route() and not veh.is_on_road() and not veh.is_scheduled() and self.__duration:
                veh.set_routes(self.create_routes(self.__maximumNumberOfRoutes, veh.get_veh_id()))
                print("Simulation", self.__v2v_heartbeat_strategy, "Vehicle", veh.get_veh_id(), "on route",
                      veh.get_current_route(), "at", self.__current_time)
                veh.set_scheduled()
                self.__traci.vehicle.add(veh.get_veh_id(), veh.get_current_route())
            if not veh.has_next_route() and not veh.is_on_road() and not veh.is_scheduled() and not self.__duration or veh.update_done():
                self.__number_of_unfinished_vehicles -= 1
            if veh.is_on_road():
                loaded_chunks += veh.seeding_step(current_time, seeding_number)

            for update in veh.getUpdate():
                progress_veh = len(veh.getUpdate()[update].keys())
                progress_veh_list.append(progress_veh)
                if progress_veh < seeding_number:
                    print("Progress smaller than seeding in veh", veh, progress_veh, seeding_number)
                    print(veh.getUpdate()[update].keys())
                    sys.exit("Error in progress ")
                progress_all_veh += progress_veh

        # mean update status in fleet @ current_time (RL helper)
        fleet_progress = int(progress_all_veh / self.__numberOfVehicles)
        chunks_loaded = int(loaded_chunks / self.__numberOfVehicles)
        self.update_progress_fleet = int(fleet_progress)
        return True if self.__number_of_unfinished_vehicles == 0 else False, progress_veh_list, chunks_loaded

    def get_plot_data(self) -> (List, List, List):
        """
        Get plotting data
        @return Real Time, Plot Time, Plot Values
        """
        return self.__plot_real_time, self.__plot_times, self.__plot_values

    def __init__(self, traci: object, backend_server: object, v2v_layer: V2VNetworkingLayer, additional_vehicle: int,
                 number_vehicle: int, number_routes: int, ismNetworkingLayer_var: ismNetworkingLayer.ISMNetworkingLayer,
                 v2v_device: bool, wlan_device: bool,
                 wlan_heartbeat_strategy: str, v2v_heartbeat_strategy: str, heartbeat_encoding: str,
                 v2v_heartbeat_interval: float, v2v_communication_distance: float, v2v_data_rate: int,
                 file_name: str = "None", duration: bool = False, wlan_communication_distance: float = 400,
                 seed: float = 1.0, sumo_route: str = None, v2v_equipment_percentage: float = 100.0,
                 wlan_equipment_percentage: float = 100.0) -> None:
        """
        Generate a FleetManager object
        @param traci TraCI interface
        @param backend_server A Backend object
        @param v2v_layer The V2V Networking Layer
        @param additional_vehicle Number of additional vehicles
        @param number_vehicle Number of communicating vehicles
        @param number_routes Number of routes per communicating vehicle
        @param ismNetworkingLayer_var The ISM Networking Layer
        @param v2v_device Use of V2V communication
        @param wlan_device Use of WLAN communication
        @param wlan_heartbeat_strategy Strategy for WLAN heartbeat messages
        @param v2v_heartbeat_strategy Strategy for V2V heartbeat messages
        @param heartbeat_encoding Encoding for heartbeat messages
        @param v2v_heartbeat_interval Interval for V2V heartbeat messages
        @param v2v_communication_distance V2V communication distance
        @param v2v_data_rate V2V data rate
        @param file_name File name of simulation
        @param duration True if the vehicles should consistently be in the simulation,
                False if they should leave after number_routes
        @param wlan_communication_distance WLAN communication distance
        @param seed Seed for simulation
        @param sumo_route Sumo routes

        """
        self.__traci = traci
        self.__numberOfAdditionalVehicles = additional_vehicle
        self.__numberOfVehicles = number_vehicle
        self.__v2v_communicationDistance = v2v_communication_distance
        self.__wlan_communication_distance = wlan_communication_distance
        self.__v2v_data_rate = v2v_data_rate
        self.__seed = seed
        self.__rng = random.Random()
        self.__rng.seed(seed)
        self.__route_file_created = False
        print("seed is", seed)
        self.__file_name = file_name
        self.__duration = duration
        self.__maximumNumberOfRoutes = number_routes if not duration else 1
        self.__v2v_device = v2v_device
        self.__wlan_device = wlan_device
        self.__wlan_heartbeat_strategy = wlan_heartbeat_strategy
        self.__v2v_heartbeat_strategy = v2v_heartbeat_strategy
        self.__v2v_heartbeat_interval = v2v_heartbeat_interval
        self.__heartbeat_encoding = heartbeat_encoding
        self.__currentNumberOfVehicles = 0
        self.__currentNumberOfAdditionalVehicles = 0
        self.__currentNumberOfAdditionalVehicles_index = 0
        self.__allVehicles = []
        self.__backendServer = backend_server
        self.__v2v_layer = v2v_layer
        self.__ismNetworkingLayer = ismNetworkingLayer_var
        self.__current_time = self.__traci.simulation.getTime()
        self.__edge_ids = self.__traci.edge.getIDList()
        self.__sumo_route = sumo_route
        self.__v2v_equipment_percentage = v2v_equipment_percentage
        self.__wlan_equipment_percentage = wlan_equipment_percentage
        self.__v2v_modules_list = [False for i in range(self.__numberOfVehicles)]
        self.__wlan_modules_list = [False for i in range(self.__numberOfVehicles)]
        r = random.Random()
        r.seed(seed)
        for i in range(int(math.ceil((self.__v2v_equipment_percentage / 100.0) * self.__numberOfVehicles))):
            pos = r.randint(0, self.__numberOfVehicles - 1)
            while self.__v2v_modules_list[pos] and sum(self.__v2v_modules_list) < self.__numberOfVehicles:
                pos = r.randint(0, self.__numberOfVehicles - 1)
            self.__v2v_modules_list[pos] = True

        for i in range(int(math.ceil((self.__wlan_equipment_percentage / 100.0) * self.__numberOfVehicles))):
            pos = r.randint(0, self.__numberOfVehicles - 1)
            while self.__wlan_modules_list[pos] and sum(self.__wlan_modules_list) < self.__numberOfVehicles:
                pos = r.randint(0, self.__numberOfVehicles - 1)
            self.__wlan_modules_list[pos] = True

        self.__number_of_unfinished_vehicles = self.__numberOfVehicles
        while self.__currentNumberOfVehicles != self.__numberOfVehicles:
            self.add_vehicle()
            print("Added Vehicle")
        self.update_progress_fleet = 0
        self.__plot_times = []
        self.__plot_values = []
        self.__plot_figs = None
        self.__animation = None
        self.__line2 = None
        self.__plot_real_time = []
