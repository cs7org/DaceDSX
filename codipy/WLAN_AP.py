import math
import random
from typing import List
import BeaconMsg
import copy
import BackendConnector


class WlanAP:
    """
    @brief WLAN / WiFi Access Point
    @author Michael Niebisch
    @bug No known bugs

    Class defining a WLAN / WiFi Access Point (AP)
    """

    def get_position(self) -> (float, float):
        """
        Get the position of the WLAN AP
        @return The position
        """
        return self.__position

    def set_position(self, position: float) -> None:
        """
        Sets the position of the WLAN AP
        @param position The (x, y) position
        """
        self.__position = position

    def get_communication_range(self) -> float:
        """
        Get the communication range of the WLAN AP
        @return The maximum communication range
        """
        return self.__communication_range

    def set_communication_range(self, communication_range: float):
        """
        Set the maximum communication range
        @param communication_range The communication range value
        """
        self.__communication_range = communication_range

    def get_max_data_rate(self) -> float:
        """
        Get the maximum data rate
        @return The maximum data rate of the WLAN AP
        """
        return self.__max_data_rate

    def set_max_data_rate(self, max_data_rate: float):
        """
        Set the maximum data rate
        @param max_data_rate The maximum data rate
        """
        self.__max_data_rate = max_data_rate

    def add_to_wlan_incoming_queue(self, element, vehicle_id: str) -> None:
        """
        Adds a message to the incoming queue
        @param element The message
        @param vehicle_id The sender Vehicle ID
        """
        if vehicle_id not in self.__connected_vehicles and not self.is_connectable():
            return
        self.__wlan_incoming_queue.append((vehicle_id, element))
        if vehicle_id not in self.__connected_vehicles:
            self.__connected_vehicles[vehicle_id] = BackendConnector.BackendConnector(self.__backend, vehicle_id,
                                                                                      self.__packet_rate,
                                                                                      self.__step_length)

    def get_wlan_incoming_queue(self) -> List:
        """
        Get the WLAN incoming queue
        @return The message queue
        """
        return self.__wlan_incoming_queue

    def add_to_wlan_outgoing_queue(self, element) -> None:
        """
        Add a message to the WLAN outgoing queue
        @param element The message to be added
        """
        self.__wlan_outgoing_queue.append(element)

    # def get_wlan_outgoing_queue(self):
    #    return self.__wlan_outgoing_queue

    def get_wlan_outgoing_queue(self, current_time: float, time_step: float) -> List:
        """
        Get the current WLAN outgoing queue
        @param current_time Current time in simulation
        @param time_step Time step in simulation
        """
        result_list = []
        counter = 0
        for entry in sorted(self.__wlan_outgoing_queue, key=lambda x: x[0]):
            counter += 1
            if current_time >= entry[0] >= current_time - time_step:
                result_list.append(copy.copy(entry))
                self.__wlan_outgoing_queue.remove(entry)
            elif entry[0] < current_time - time_step:
                self.__wlan_outgoing_queue.remove(entry)
        return result_list

    def add_to_internet_incoming_queue(self, element) -> None:
        """
        Add a message to the incoming queue of the internet
        @param element The message to be added
        """
        self.__internet_incoming_queue.append(element)

    def get_internet_outgoing_queue(self) -> List:
        """
        Get the outgoing queue to the internet
        @return The list of messages
        """
        return self.__internet_outgoing_queue

    def send_beacon(self, send_time: float) -> None:
        """
        Send a beacon message
        @param send_time The send time of the beacon
        """
        self.add_to_wlan_outgoing_queue(
            (send_time, BeaconMsg.generate_message(send_time, self.__beacon_interval, self.__name), '***'))

    def get_number_of_connected_vehicles(self) -> int:
        """
        Get the number of connected vehicles
        @return The number of connected vehicles
        """
        return len(self.__connected_vehicles.keys())

    def send_to_internet(self) -> None:
        """
        Sends data via the BackendConnector of the Vehicles to the internet
        """
        for msg in self.__internet_outgoing_queue:
            try:
                if msg[0] in self.__connected_vehicles:
                    self.__connected_vehicles[msg[0]].incoming_messages(msg[1])
            except Exception as e:
                print(self.__connected_vehicles)
                print(msg[0])
                print(msg[1])
        self.__internet_outgoing_queue = []

    def simulation_step(self, current_time: float) -> None:
        """
        Do one simulation step in the WlanAP
        @param current_time The current time
        """
        if current_time >= self.__last_beacon + self.__beacon_interval:
            self.send_beacon(self.__last_beacon + self.__beacon_interval)
            self.__last_beacon = self.__last_beacon + self.__beacon_interval
        self.__internet_outgoing_queue = self.__wlan_incoming_queue
        self.__wlan_incoming_queue = []
        self.send_to_internet()
        for veh in self.__connected_vehicles:
            self.__connected_vehicles[veh].simulation_step(current_time)
        for connected_vehicle in self.__connected_vehicles:
            messages = self.__connected_vehicles[connected_vehicle].get_send_queue(current_time, self.__step_length)
            for msg in messages:
                self.add_to_wlan_outgoing_queue(msg)

    def remove_backend_connector(self, veh_id: str) -> None:
        """
        Remove the BackendConnector of a Vehicle
        @param veh_id The Vehicle ID
        """
        connector = self.__connected_vehicles.pop(veh_id, None)
        del connector

    def is_connectable(self) -> bool:
        """
        Check if the WlanAP is currently connectable
        @return True if a new connection can be established, False otherwise
        """
        return True if len(self.__connected_vehicles) < self.__max_number_connections else False

    def get_name(self):
        return self.__name

    def __init__(self, name: str, x: float, y: float, communication_range: float, traci: object, beacon_interval: float,
                 backend: object, data_rate: float, max_number_connections: float = math.inf) -> None:
        self.__name = name
        self.__position = (x, y)
        self.__communication_range = communication_range
        self.__backend = backend
        self.__traci = traci
        self.__traci.poi.subscribeContext(name, self.__traci.constants.CMD_GET_VEHICLE_VARIABLE,
                                          self.__communication_range, [self.__traci.constants.VAR_POSITION])
        self.__beacon_interval = beacon_interval
        self.__last_beacon = random.uniform(0.0, beacon_interval)
        self.__max_data_rate = None
        self.__wlan_outgoing_queue = []
        self.__wlan_incoming_queue = []
        self.__internet_outgoing_queue = []
        self.__internet_incoming_queue = []
        self.__step_length = self.__traci.simulation.getDeltaT()
        self.__packet_size = 1500  # byte
        self.__data_rate = data_rate  # Byte/s
        self.__packet_rate = (self.__data_rate * self.__step_length) / self.__packet_size
        self.__connected_vehicles = {}
        self.__backend_connector = BackendConnector.BackendConnector(self.__backend, self, self.__packet_rate,
                                                                     self.__step_length)
        self.__max_number_connections = max_number_connections
