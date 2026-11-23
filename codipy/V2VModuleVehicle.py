from typing import List
from MessageType import *
import struct


class V2VModuleVehicle:
    """
    @brief V2V Communication Module for Vehicles
    @author Michael Niebisch
    @bug No known bugs

    Class defining the V2V communication Module for Vehicle
    """
    def add_send_message(self, message_tuple: tuple, heartbeat=False) -> None:
        """
        Adds a message tuple to the send queue.
        @param message_tuple Message tuple to be added.
        @param heartbeat Is the message a heartbeat message
        """
        if heartbeat:
            self.__heartbeat_queue.append(message_tuple)
        else:
            self.__send_queue.append(message_tuple)
            self.__full_schedule = len(self.__send_queue) >= self.__max_packets

    def replace_send_messages(self, message_list: list) -> None:
        """
        Replace the current send queue with the given list
        @param message_list: New message list
        """
        self.__send_queue = message_list
        self.__full_schedule = len(self.__send_queue) >= self.__max_packets

    def __sort_messages(self, current_time: float, time_step: float) -> None:
        """
        Sorting of message list
        @param current_time The current time
        @param time_step The time step
        """
        current_time = round(current_time, 6)
        time_step = round(time_step, 6)
        time_duration = round(current_time - time_step, 6)
        # delete false send messages
        self.__delete_old_messages(time_duration)
        # delete wrong heartbeats
        if len(self.__heartbeat_queue) > 0:
            remaining_heartbeats = [heartbeat for heartbeat in self.__heartbeat_queue if heartbeat[0] >= time_duration]
            self.__heartbeat_queue = sorted(remaining_heartbeats, key=lambda x: x[0])
        result_list = self.__send_queue
        if len(self.__heartbeat_queue) > 0 and current_time > self.__heartbeat_queue[0][0] >= time_duration:
            heartbeat_element = self.__heartbeat_queue.pop(0)
            if len(result_list) > 0:
                for counter, element in enumerate(result_list):
                    if heartbeat_element[0] >= element[0]:
                        result_list.insert(counter, heartbeat_element)
                        break
            else:
                result_list.append(heartbeat_element)
        self.__send_queue = result_list

    def get_send_queue(self, current_time: float, time_step: float) -> List:
        """
        Return a list of messages that will have been sent in the last timestep
        @param current_time Current time in simulation.
        @param time_step Time step in simulation
        @return List of messages
        """
        current_time = round(current_time, 6)
        time_step = round(time_step, 6)
        time_duration = round(current_time - time_step, 6)
        self.__sort_messages(current_time, time_step)
        result_list = [element for element in self.__send_queue if current_time >= element[0] >= time_duration]
        return result_list

    def __delete_old_messages(self, time: float) -> None:
        """
        Delete all messages prior to time
        @param time Last valid time stamp
        """
        self.__send_queue = [item for item in self.__send_queue if item[0] >= time]
        sorted(self.__send_queue, key=lambda x: x[0])

    def get_received_messages(self) -> List:
        """
        Get the received messages sorted by time
        @return A time sorted list of messages
        """
        return_value = sorted(self.__receive_queue, key=lambda x: x[0])
        self.__receive_queue = []
        return return_value

    def receive_messages(self, messages: list, from_vehicle: str, distance: float) -> None:
        """
        Receives messages, logs the information and adds the message to the reception queue.
        @param messages A list of messages for the Vehicle
        @param from_vehicle ID of the sender Vehicle
        @param distance The distance from which the message was received
        """
        save_information = []
        name = self.__file_name + '_' + self.__vehID + '_' + 'reception' + '_' + from_vehicle
        if name not in self.__vehicle.get_used_file_names():
            self.__vehicle.get_used_file_names().add(name)
        for message in messages:
            save_information.append(
                (message[0], MessageType(struct.unpack('<I', message[1][:1] + struct.pack('<I', 1)[1:])[0]).name))
            self.__receive_queue.append((message[0], message[1], distance, from_vehicle))
        # Code used to write debug/result information into files
        #    if name not in self.__files_io:
        #        self.__files_io[name] = open(name, 'a', newline='')
        # with open(file_name, 'a', newline='') as file:
        #    writer = csv.writer(self.__files_io[name])
        # for message_0, message_time in save_information[name]:
        #    writer.writerow([message_0, message_time])
        #    writer.writerows(save_information)

    def __init__(self, vehicle_id, file_name, vehicle, packets_heartbeat_interval):
        """
        Initialize a V2V Module
        @param vehicle_id Vehicle ID
        @param file_name File Name
        @param vehicle A Vehicle Object
        @param packets_heartbeat_interval Interval between heartbeat messages
        """
        self.__send_queue = []
        self.__heartbeat_queue = []
        self.__receive_queue = []
        self.__vehicle = vehicle
        self.__vehID = vehicle_id
        self.__file_name = file_name
        self.__full_schedule = False
        self.__max_packets = packets_heartbeat_interval
        self.__files_io = {}
