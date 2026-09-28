from typing import List

from WLAN_AP import WlanAP
import random
import numpy
import time


class ISMNetworkingLayer:
    """
    @brief ISM Networking Layer
    @author Michael Niebisch
    @bug No known bugs

    Class defining the ISM Networking Layer for communication via WLAN
    """

    def get_receive_vehicle_by_id(self, vehicle_id: str):
        """
        Get the Vehicle object by its ID.
        @param vehicle_id The Vehicle ID
        @return The Vehicle object
        """
        for vehicle in self.__allVehicles:
            if vehicle.get_veh_id() == vehicle_id:
                return vehicle

    def get_receive_ap_by_id(self, ap_id: str) -> WlanAP:
        """
        Get the AP object by its ID.
        @param ap_id The AP ID
        @return The AP object
        """
        for ap in self.__allWlanAps:
            if ap.get_name() == ap_id:
                return ap

    def simulation_step(self, current_time: float) -> List:
        """
        @param current_time Current simulation time
        @return List of WlanAPs and their number of connected Vehicles
        """
        number_connected_vehicles = []
        for ap_wlan in self.__allWlanAps:
            ap_wlan.simulation_step(current_time)
            number_connected_vehicles.append(
                (current_time, ap_wlan.get_name(), ap_wlan.get_number_of_connected_vehicles()))
        sent_messages = 0
        for ap in self.__allWlanAps:
            close_vehicles = self.__traci.poi.getContextSubscriptionResults(ap.get_name())
            send = ap.get_wlan_outgoing_queue(current_time, self.__step_length)
            sent_messages += len(send)
            if len(send) == 0:
                continue
            for id_close_vehicle in close_vehicles:
                if id_close_vehicle.startswith('vehicle') and id_close_vehicle in self.__allVehicles:
                    close_vehicle = self.__allVehicles[id_close_vehicle]
                    send_list = []
                    for element in send:
                        # Use a 0 percent packet loss
                        if random.random() >= 0.0 and (element[2] == id_close_vehicle or element[2] == '***'):
                            send_list.append(element)
                    if close_vehicle is not None and len(send_list) > 0:
                        a = numpy.array(
                            (close_vehicles[id_close_vehicle][66][0], close_vehicles[id_close_vehicle][66][1]))
                        b = numpy.array((ap.get_position()[0], ap.get_position()[1]))
                        distance = numpy.linalg.norm(a - b)
                        close_vehicle.get_wlan_module().send_to_layer_2(send_list, ap.get_name(), distance)
        for veh_id in self.__allVehicles:
            veh = self.__allVehicles[veh_id]
            wlan_module = veh.get_wlan_module()
            if wlan_module.is_associated():
                get_msg_to_send = wlan_module.retrieve_send_messages()
                for msg in get_msg_to_send:
                    ap_obj = self.get_receive_ap_by_id(msg[1])
                    ap_obj.add_to_wlan_incoming_queue(msg[0], veh_id)  # add veh name?
        return number_connected_vehicles

    def add_vehicle(self, vehicle: object) -> None:
        """
        Add a vehicle to the ISM Layer
        @param vehicle: A Vehicle
        """
        self.__allVehicles[vehicle.get_veh_id()] = vehicle

    def remove_vehicle(self, vehicle: object) -> None:
        """
        Remove a vehicle from the ISM Layer
        @param vehicle: A Vehicle
        """
        del self.__allVehicles[vehicle.get_veh_id()]

    def add_wlan_ap(self, ap: WlanAP) -> None:
        """
        Add a WlanAP to the ISM Layer
        @param ap: A WlanAP
        """
        self.__allWlanAps.append(ap)

    def remove_wlan_ap(self, ap: WlanAP) -> None:
        """
        Remove a WlanAP from the ISM Layer
        @param ap: A WlanAP
        """
        self.__allWlanAps.remove(ap)

    def get_wlan_ap_by_name(self, name: str) -> WlanAP:
        """
        Get a WlanAP by its name
        @param name The name of the WlanAP
        @return The WlanAP object
        """
        for ap in self.__allWlanAps:
            if ap.get_name() == name:
                return ap

    def __init__(self, traci):
        """
        Initializes the ISMNetworkingLayer
        """
        self.__allVehicles = {}
        self.__allWlanAps = []
        self.__traci = traci
        self.__step_length = self.__traci.simulation.getDeltaT()
