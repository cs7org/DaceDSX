import csv
import struct
from typing import List

import BeaconMsg
from MessageType import MessageType


class WLANModuleVehicle:
    """
    @brief WLAN / WiFi Module for a Vehicle
    @author Michael Niebisch
    @bug No known bugs

    Class defining a WLAN / WiFi Module for Vehicles
    """

    def is_associated(self) -> bool:
        """
        Check if the WLAN module is associated with a WLAN AP
        @return True if module is associated, False otherwise
        """
        return True if self.__associated_ap is not None else False

    def association_triggered(self) -> bool:
        """
        Check if an association was triggered
        @return True if association was triggered, False otherwise
        """
        if self.__new_association:
            self.__new_association = False
            return True
        else:
            return False

    def log_association(self, current_time: float, association: bool, ap_name: str, last_ap: str = "") -> None:
        """
        Logging of associations
        @param current_time The current time
        @param association bool if this is an association log
        @param ap_name Name of the WlanAP
        @param last_ap Name of the last WlanAP
        """
        if not association:
            self.__vehicle.get_fleet_manager().get_ism_networking_layer().get_wlan_ap_by_name(last_ap).remove_backend_connector(self.__vehID)

        name = self.__file_name + '_' + self.__vehID + '_' + 'wlan_ap_association'
        if name not in self.__vehicle.get_used_file_names():
            self.__vehicle.get_used_file_names().add(name)
        if name not in self.__association_files:
            self.__association_files[name] = open(name, 'a', newline='')
        writer = csv.writer(self.__association_files[name])
        writer.writerow([current_time, association, ap_name])

    def check_for_beacons(self, current_time: float) -> None:
        """
        Check if a new Beacon message was received
        @param current_time The current simulation time
        """
        associated = self.is_associated()
        possible_association_aps = []
        remaining_messages = []
        for msg in self.__layer_2_in:
            if BeaconMsg.is_beacon_message(msg[0][0][1]):
                time_stamp, beacon_interval, ap_name = BeaconMsg.decode_message(msg[0][0][1])
                if associated and ap_name == self.__associated_ap:
                    self.__last_heartbeat = time_stamp
                    self.__timeout = 4 * beacon_interval
                if not associated:
                    possible_association_aps.append(msg)
            else:
                if associated and msg[1] == self.__associated_ap:
                    remaining_messages.append(msg)
        self.__layer_2_in = remaining_messages
        if len(possible_association_aps) > 0:
            best_beacon = sorted(possible_association_aps, key=lambda x: x[2])[0]
            time_stamp, beacon_interval, ap_name = BeaconMsg.decode_message(best_beacon[0][0][1])
            if  self.__vehicle.get_fleet_manager().get_ism_networking_layer().get_wlan_ap_by_name(ap_name).is_connectable():
                self.__associated_ap = ap_name
                self.__last_heartbeat = time_stamp
                self.__timeout = 4 * beacon_interval
                self.__new_association = True
                self.log_association(current_time, True, ap_name)
        if current_time >= self.__last_heartbeat + self.__timeout and self.__associated_ap is not None:
            tmp = self.__associated_ap
            self.__associated_ap = None
            self.log_association(current_time, False, "xxx", tmp)


    def send_to_layer_2(self, send_list: List, from_ap: str, distance: float) -> None:
        """
        Send messages to the layer 2 communication layer
        @param send_list The messages to send
        @param from_ap Sending WlanAP
        @param distance The reception distance
        """
        # incoming message from ISM Networking Layer
        if self.__associated_ap is None or from_ap == self.__associated_ap:
            save_information = {}
            for message in sorted(send_list, key=lambda x: x[0]):
                name = self.__file_name + '_' + self.__vehID + '_' + 'wlan_reception'
                if name not in self.__vehicle.get_used_file_names():
                    self.__vehicle.get_used_file_names().add(name)
                if name not in save_information:
                    save_information[name] = []
                save_information[name].append(
                    (message[0], MessageType(struct.unpack('<I', message[1][:1] + struct.pack('<I', 1)[1:])[0]).name))
            for file_name in save_information.keys():
                if file_name not in self.__reception_files:
                    self.__reception_files[file_name] = open(file_name, 'a', newline='')
                # Change this to log debug/result information into files
                #writer = csv.writer(self.__association_files[name])
                #writer.writerow([current_time, association, ap_name])
                #with open(name, 'a', newline='') as file:
                writer = csv.writer(self.__reception_files[file_name])
                #for message_0, message_time in save_information[file_name]:
                #    writer.writerow([message_0, message_time])
                writer.writerows(save_information[file_name])
                #writer.writerow(
                 #   [message[0],
                  #   MessageType(struct.unpack('<I', message[1][:1] + struct.pack('<I', 1)[1:])[0]).name])
            self.__layer_2_in.append((send_list, from_ap, distance))

    def send_to_layer_3(self, msg_tuple: tuple) -> None:
        """
        Send a message to layer 3
        @param msg_tuple The message
        """
        self.__layer_3_in.append(msg_tuple)

    def retrieve_received_messages(self) -> List:
        """
        Get the received messages
        @return The message list
        """
        messages = self.__layer_3_out
        self.__layer_3_out = []
        return messages

    def retrieve_send_messages(self) -> List:
        """
        Get the send messages
        @return The message list
        """
        messages = self.__layer_2_out
        self.__layer_2_out = []
        return messages

    def simulation_step(self, current_time: float) -> None:
        """
        Perform one simulation step in the WLAN Module
        @param current_time The current simulation time
        """
        self.check_for_beacons(current_time)
        if self.is_associated():
            self.__layer_3_out = self.__layer_2_in
        self.__layer_2_in = []
        for msg in self.__layer_3_in:
            if self.is_associated():
                self.__layer_2_out.append((msg, self.__associated_ap))
        self.__layer_3_in = []


    def reset(self) -> None:
        """
        Reset all features of the WLAN Module
        """
        self.__layer_2_in = []
        self.__layer_2_out = []
        self.__layer_3_in = []
        self.__layer_3_out = []
        self.__last_heartbeat = 0.0
        self.__associated_ap = None
        self.__timeout = 10.0
        self.__new_association = False

    def __init__(self, veh_id: str, file_name: str, vehicle: object):
        self.__layer_2_in = []
        self.__layer_2_out = []
        self.__layer_3_in = []
        self.__layer_3_out = []
        self.__associated_ap = None
        self.__last_heartbeat = 0.0
        self.__timeout = 10.0
        self.__new_association = False
        self.__vehID = veh_id
        self.__file_name = file_name
        self.__vehicle = vehicle
        self.__association_files = {}
        self.__reception_files = {}
        # layer 4 -> layer_3_in -> layer_2_out -> layer 1
        # layer 1 -> layer_2_in -> layer_3_out -> layer 4