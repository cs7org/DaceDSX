import random
import rle_generation


class V2VNetworkingLayer:
    """
	@brief Vehicle-to-Vehicle Networking Layer
	@author Michael Niebisch
	@bug No known bugs

	Class defining the V2V Networking Layer. It is used for the direct communication between vehicles.

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

    def simulation_step(self, current_time: float) -> None:
        """
		Conducts a simulation step in the V2V Networking Layer.
		@param current_time: Current simulation time
		"""
        # Get all vehicles in communication distance for every vehicle
        close_vehicles_dict = {}
        for vehicle_id in self.__allVehicles:
            vehicle = self.__allVehicles[vehicle_id]
            if vehicle.is_on_road():
                close_vehicles_o = self.__traci.vehicle.getContextSubscriptionResults(vehicle_id)
                close_vehicles = {k: v for k, v in close_vehicles_o.items() if k.startswith("vehicle")}
                if len(close_vehicles) > 1:
                    close_vehicles_dict[vehicle] = close_vehicles
        l = close_vehicles_dict.keys()
        # Deliver the messages from the vehicles to the other vehicles, that are in communication distance
        for vehicle_id in self.__allVehicles:
            vehicle = self.__allVehicles[vehicle_id]
            if vehicle.is_on_road():
                if vehicle in l:
                    send = vehicle.get_v2v_module().get_send_queue(current_time, self.__step_length)
                    if len(send) == 0:
                        continue

                    for id_close_vehicle in close_vehicles_dict[vehicle]:
                        if id_close_vehicle != vehicle_id and id_close_vehicle.startswith(
                                'vehicle') and id_close_vehicle in self.__allVehicles_id_set:
                            close_vehicle = self.__allVehicles[
                                id_close_vehicle]
                            send_list = []
                            inter_vehicle_distance = rle_generation.distance_calculation(
                                close_vehicles_dict[vehicle][id_close_vehicle][66][0],
                                close_vehicles_dict[vehicle][id_close_vehicle][66][1],
                                close_vehicles_dict[vehicle][vehicle_id][66][0],
                                close_vehicles_dict[vehicle][vehicle_id][66][1])
                            if self.__distance is not None and self.__data_rate is not None:
                                p = rle_generation.calculate_packet_reception_probability(inter_vehicle_distance,
                                                                                          self.__transmission_power,
                                                                                          self.__gain, self.__pathloss,
                                                                                          self.__loss_exponent,
                                                                                          self.__distance,
                                                                                          self.__log_shadow,
                                                                                          self.__shadow_slope,
                                                                                          self.__sigma, self.__two_ray,
                                                                                          self.__antenna_height,
                                                                                          self.__loss_exponent2,
                                                                                          self.__sigma2)

                            for element in send:
                                if self.__distance is None and self.__data_rate is None:
                                    # Use a 10 percent packet loss
                                    if random.random() >= 0.1:
                                        send_list.append(element)
                                else:
                                    if random.random() <= p:
                                        send_list.append(element)

                            if close_vehicle is not None:
                                close_vehicle.get_v2v_module().receive_messages(send_list, vehicle_id,
                                                                                inter_vehicle_distance)

    def add_vehicle(self, vehicle: object) -> None:
        """
		Add a vehicle to the V2V Layer
		@param vehicle A Vehicle
		"""
        self.__allVehicles[vehicle.get_veh_id()] = vehicle
        self.__allVehicles_id_set = set(self.__allVehicles.keys())

    def remove_vehicle(self, vehicle: object) -> None:
        """
		Remove a vehcile from the V2V Layer
		@param vehicle A Vehicle
		"""
        del self.__allVehicles[vehicle.get_veh_id()]
        self.__allVehicles_id_set = set(self.__allVehicles.keys())

    def __init__(self, traci: object, distance: float, data_rate: float, gain: int,
                 transmission_power: float, pathloss: float, noisepower: int, loss_exponent: float,
                 antenna_height: float, two_ray: bool, log_distance: bool, log_shadow: bool, shadow_slope: bool,
                 loss_exponent2: float, sigma: float, sigma2: float) -> None:
        """
		Create a V2V Networking Layer

		@bug The data rate is currently fixed and not parameterized
		@bug Heartbeat interval is currently fixed and not parameterized
		@bug Tested only for integer values of packet_rate.
		@param traci The TraCI interface
		@param distance The distance value
		@param data_rate The maximum data rate
		@param gain The transmission gain
		@param transmission_power The transmission power
		@param pathloss The path loss
		@param noisepower The power of noise
		@param loss_exponent The loss exponent
		@param antenna_height The height of the antenna
		@param two_ray The two-ray ground interference model is used
		@param log_distance The log distance model is used
		@param log_shadow The log shadowing model is used
		@param shadow_slope The shadow slope model is used
		@param loss_exponent2 The second loss exponent
		@param sigma The sigma value
		@param sigma2 The second sigma value
		"""
        self.__allVehicles = {}
        self.__allVehicles_id_set = set()
        self.__traci = traci
        self.__step_length = self.__traci.simulation.getDeltaT()
        self.__distance = distance
        self.__data_rate = data_rate  # Byte/s
        self.__gain = gain
        self.__transmission_power = transmission_power
        self.__pathloss = pathloss
        self.__noisepower = noisepower
        self.__loss_exponent = loss_exponent
        self.__antenna_height = antenna_height
        self.__two_ray = two_ray
        self.__log_distance = log_distance
        self.__log_shadow = log_shadow
        self.__shadow_slope = shadow_slope
        self.__loss_exponent2 = loss_exponent2
        self.__sigma = sigma
        self.__sigma2 = sigma2
        self.__counter = 0
        self.__values = 0
