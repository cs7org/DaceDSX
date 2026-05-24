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
        Places WLAN APs as POIs in the SUMO simulation
        """
        if self.__ap_placement == 4:
            for coords in self.__ap_coords:
                ap_id = "wlan_ap_%i" % self.__current_number_aps
                print(ap_id, coords[0], coords[1], (0xff, 0x0, 0x0, 0xff), "wlan", 3)
                self.__traci.poi.add(ap_id, coords[0], coords[1], (0xff, 0x0, 0x0, 0xff))#, "wlan", 3)
                ap = wlanAP.WlanAP(ap_id, coords[0], coords[1], coords[2], self.__traci,
                                   self.__beacon_interval,
                                   self.__backend, self.__wlan_data_rate, self.__max_number_connections)
                self.__ism_layer.add_wlan_ap(ap)
                self.__current_number_aps += 1
            return
        for ap in range(self.__number_of_aps):
            if self.__ap_placement == 3:
                x = self.__rng.uniform(self.__minXBound, self.__maxXBound)
                y = self.__rng.uniform(self.__minYBound, self.__maxYBound)
                ap_id = "wlan_ap_%i" % self.__current_number_aps
                self.__traci.poi.add(ap_id, x, y, (0xff, 0x0, 0x0, 0xff), "wlan", 3)
                ap = wlanAP.WlanAP(ap_id, x, y, self.__communication_distance, self.__traci, self.__beacon_interval,
                                   self.__backend, self.__wlan_data_rate, self.__max_number_connections)
                self.__ism_layer.add_wlan_ap(ap)
                self.__current_number_aps += 1
                continue
            if self.__ap_placement == 0 or self.__ap_placement == 2:
                random_building = self.__rng.choices(self.__building_id_list, weights=self.__building_area_list)
            if self.__ap_placement == 1:
                inverse_weights = []
                for element in self.__building_area_list:
                    inverse_weights.append(float(1/element))
                random_building = self.__rng.choices(self.__building_id_list, weights=inverse_weights)
            building_shape = self.__traci.polygon.getShape(random_building[0])
            building_polygon = Polygon(building_shape)
            minx, miny, maxx, maxy = building_polygon.bounds
            result_point = None
            while True:
                pnt = Point(self.__rng.uniform(minx, maxx), self.__rng.uniform(miny, maxy))
                if building_polygon.contains(pnt):
                    result_point = pnt
                    break
            x = result_point.x
            y = result_point.y
            ap_id = "wlan_ap_%i" % self.__current_number_aps
            self.__traci.poi.add(ap_id, x, y, (0xff, 0x0, 0x0, 0xff), "wlan", 3)
            ap = wlanAP.WlanAP(ap_id, x, y, self.__communication_distance, self.__traci, self.__beacon_interval, self.__backend, self.__wlan_data_rate, self.__max_number_connections)
            self.__ism_layer.add_wlan_ap(ap)
            self.__current_number_aps += 1



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
        bounds = traci.simulation.getNetBoundary()
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

