from typing import List

import WLAN_AP as wlanAP
import random
from shapely.geometry import Polygon, Point
import math

from Backend import Backend
from ISMNetworkingLayer import ISMNetworkingLayer


class WlanAPManager:
    """
    @brief WLAN / WiFi Access Point Manager
    @author Michael Niebisch
    @bug No known bugs

    Class defining a WLAN / WiFi Access Point (AP) Manager for WLAN AP coordination
    """
    def place_aps(self):
        """
        Places WLAN APs (passive mode: pre-configured coordinates only)
        """
        if self.__ap_placement == 4:
            # PASSIVE MODE: Use register_poi() instead of poi.add()
            for coords in self.__ap_coords:
                ap_id = "wlan_ap_%i" % self.__current_number_aps
                print(f"Registering AP: {ap_id} at ({coords[0]}, {coords[1]}) range={coords[2]}m")
                
                # Register POI with passive TraCI interface
                self.__traci.register_poi(
                    ap_id,
                    {"x": coords[0], "y": coords[1]},
                    coords[2]  # communication_range
                )
                
                ap = wlanAP.WlanAP(ap_id, coords[0], coords[1], coords[2], self.__traci,
                                   self.__beacon_interval,
                                   self.__backend, self.__wlan_data_rate, self.__max_number_connections)
                self.__ism_layer.add_wlan_ap(ap)
                self.__current_number_aps += 1
            return
        
        # PASSIVE MODE: Only pre-configured mode (4) is supported
        # Random placement modes (0-3) require active TraCI for poi.add() and polygon.getShape()
        raise ValueError(
            f"Passive mode only supports pre-configured AP placement (ap_placement='coords', mode=4). "
            f"Current mode: {self.__ap_placement}. "
            f"Please provide ap_coords parameter with pre-configured coordinates."
        )
        
        # OLD ACTIVE MODE CODE - DISABLED IN PASSIVE MODE
        # Removed: Random placement (mode 3), building-based placement (modes 0-2)
        # These required active TraCI APIs: poi.add(), polygon.getShape(), simulation.getNetBoundary()
        # Passive mode only supports pre-configured coordinates (mode 4)



    def __init__(self, traci: object, number_of_aps: int, ism_layer: ISMNetworkingLayer, backend: Backend,
                 buildings_tuple: tuple, ap_placement: str, communication_distance: float,
                 beacon_interval: float, wlan_data_rate: float, ap_coords: List = None,
                 max_number_connections: float = math.inf, wlan_ap_percentage: float = 100.0, seed: int = 0):
        self.__traci = traci
        self.__number_of_aps = number_of_aps
        self.__current_number_aps = 0
        self.__backend = backend
        self.__communication_distance = communication_distance
        self.__beacon_interval = beacon_interval
        self.__wlan_data_rate = wlan_data_rate
        self.__max_number_connections = max_number_connections
        self.__wlan_ap_percentage = wlan_ap_percentage
        self.__rng = random.Random()
        self.__rng.seed(seed)
        self.__seed = seed
        
        # PASSIVE MODE: Removed traci.simulation.getNetBoundary() call
        # Boundaries only needed for random placement modes (0-3)
        # Passive mode uses pre-configured mode (mode 4) only
        # If random placement ever needed, get bounds from config
        bounds = ((0, 0), (0, 0))  # Placeholder - not used in passive mode
        
        if self.__wlan_ap_percentage != 100.0:
            self.__ap_coords = self.__rng.sample(list(ap_coords), math.ceil((self.__wlan_ap_percentage/100.0) * len(list(ap_coords))))
        else:
            self.__ap_coords = ap_coords
        self.__minX = bounds[0][0]
        self.__minY = bounds[0][1]
        self.__maxX = bounds[1][0]
        self.__maxY = bounds[1][1]

        self.__minXBound = self.__minX - self.__communication_distance
        self.__minYBound = self.__minY - self.__communication_distance
        self.__maxXBound = self.__maxX + self.__communication_distance
        self.__maxYBound = self.__maxY + self.__communication_distance

        self.__ism_layer = ism_layer
        self.__building_id_list = buildings_tuple[0]
        self.__building_area_list = buildings_tuple[1]
        if ap_placement == "area":
            self.__ap_placement = 0
        elif ap_placement == "inverse area":
            self.__ap_placement = 1
        elif ap_placement == "area residential":
            self.__ap_placement = 2
        elif ap_placement == "random":
            self.__ap_placement = 3
        elif ap_placement == "coords":
            self.__ap_placement = 4
        self.place_aps()

