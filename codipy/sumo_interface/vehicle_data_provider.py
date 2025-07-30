"""
Vehicle Data Provider - Interface for accessing vehicle information from SUMO

This class provides methods to query vehicle-specific data such as position,
speed, route information, and other vehicle state data from SUMO.
"""

from typing import Tuple, List, Optional


class VehicleDataProvider:
    """
    Provides access to vehicle data from SUMO simulation.
    """
    
    def __init__(self, traci_instance):
        """
        Initialize vehicle data provider with TraCI instance.
        
        Args:
            traci_instance: TraCI instance from SumoManager
        """
        self.traci = traci_instance
        
    def get_vehicle_position(self, vehicle_id: str) -> Tuple[float, float]:
        """
        Get vehicle's current position.
        
        Args:
            vehicle_id: Vehicle identifier
            
        Returns:
            Tuple of (x, y) coordinates
        """
        return self.traci.vehicle.getPosition(vehicle_id)
        
    def get_vehicle_speed(self, vehicle_id: str) -> float:
        """
        Get vehicle's current speed.
        
        Args:
            vehicle_id: Vehicle identifier
            
        Returns:
            Current speed in m/s
        """
        return self.traci.vehicle.getSpeed(vehicle_id)
        
    def get_vehicle_route(self, vehicle_id: str) -> List[str]:
        """
        Get vehicle's planned route.
        
        Args:
            vehicle_id: Vehicle identifier
            
        Returns:
            List of edge IDs representing the vehicle's route
        """
        return self.traci.vehicle.getRoute(vehicle_id)
        
    def get_vehicle_road_id(self, vehicle_id: str) -> str:
        """
        Get the current road (edge) ID where the vehicle is located.
        
        Args:
            vehicle_id: Vehicle identifier
            
        Returns:
            Current road/edge ID
        """
        return self.traci.vehicle.getRoadID(vehicle_id)
        
    def get_vehicle_lane_id(self, vehicle_id: str) -> str:
        """
        Get the current lane ID where the vehicle is located.
        
        Args:
            vehicle_id: Vehicle identifier
            
        Returns:
            Current lane ID
        """
        return self.traci.vehicle.getLaneID(vehicle_id)
        
    def get_vehicle_angle(self, vehicle_id: str) -> float:
        """
        Get vehicle's current heading angle.
        
        Args:
            vehicle_id: Vehicle identifier
            
        Returns:
            Heading angle in degrees
        """
        return self.traci.vehicle.getAngle(vehicle_id)
        
    def get_distance_between_vehicles(self, vehicle_id1: str, vehicle_id2: str) -> float:
        """
        Calculate Euclidean distance between two vehicles.
        
        Args:
            vehicle_id1: First vehicle identifier
            vehicle_id2: Second vehicle identifier
            
        Returns:
            Distance in meters
        """
        pos1 = self.get_vehicle_position(vehicle_id1)
        pos2 = self.get_vehicle_position(vehicle_id2)
        
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        
        return (dx * dx + dy * dy) ** 0.5
        
    def get_vehicles_in_range(self, reference_vehicle_id: str, max_distance: float) -> List[str]:
        """
        Get all vehicles within a specified range of a reference vehicle.
        
        Args:
            reference_vehicle_id: Reference vehicle identifier
            max_distance: Maximum distance in meters
            
        Returns:
            List of vehicle IDs within range
        """
        vehicles_in_range = []
        all_vehicles = self.traci.vehicle.getIDList()
        
        for vehicle_id in all_vehicles:
            if vehicle_id != reference_vehicle_id:
                distance = self.get_distance_between_vehicles(reference_vehicle_id, vehicle_id)
                if distance <= max_distance:
                    vehicles_in_range.append(vehicle_id)
                    
        return vehicles_in_range
        
    def vehicle_exists(self, vehicle_id: str) -> bool:
        """
        Check if a vehicle exists in the simulation.
        
        Args:
            vehicle_id: Vehicle identifier
            
        Returns:
            True if vehicle exists, False otherwise
        """
        return vehicle_id in self.traci.vehicle.getIDList()
