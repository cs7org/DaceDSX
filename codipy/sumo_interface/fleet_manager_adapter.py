"""
Fleet Manager Interface Adapter

This adapter provides FleetManager-specific SUMO operations through our interface,
including route management and vehicle lifecycle operations.
"""

from sumo_interface import SumoFacade
from typing import List, Tuple, Optional
import random


class FleetManagerAdapter:
    """
    Adapter to provide FleetManager-specific SUMO operations through our interface.
    """
    
    def __init__(self, sumo_facade: SumoFacade):
        self.sumo_facade = sumo_facade
        
    def find_route(self, edge_from: str, edge_to: str, vehicle_type: str = "DEFAULT_VEHTYPE") -> Optional[object]:
        """
        Find a route between two edges.
        
        Args:
            edge_from: Starting edge ID
            edge_to: Destination edge ID
            vehicle_type: Vehicle type for route planning
            
        Returns:
            Route object or None if no route exists
        """
        try:
            return self.sumo_facade.get_traci_instance().simulation.findRoute(edge_from, edge_to, vehicle_type)
        except:
            return None
            
    def add_route(self, route_id: str, edge_list: List[str]) -> None:
        """
        Add a route to the simulation.
        
        Args:
            route_id: Unique identifier for the route
            edge_list: List of edge IDs forming the route
        """
        self.sumo_facade.get_traci_instance().route.add(route_id, edge_list)
        
    def add_vehicle(self, vehicle_id: str, route_id: str, vehicle_type: str = "DEFAULT_VEHTYPE") -> None:
        """
        Add a vehicle to the simulation.
        
        Args:
            vehicle_id: Unique vehicle identifier
            route_id: Route identifier for the vehicle
            vehicle_type: Type of vehicle
        """
        self.sumo_facade.get_traci_instance().vehicle.add(vehicle_id, route_id, typeID=vehicle_type)
        
    def subscribe_vehicle_context(self, vehicle_id: str, distance: float, 
                                 variables: List[int]) -> None:
        """
        Subscribe to context information around a vehicle.
        
        Args:
            vehicle_id: Vehicle to subscribe to
            distance: Subscription radius
            variables: List of TraCI constants for variables to track
        """
        traci = self.sumo_facade.get_traci_instance()
        traci.vehicle.subscribeContext(
            vehicle_id, 
            traci.constants.CMD_GET_VEHICLE_VARIABLE,
            distance, 
            variables
        )
        
    def get_current_time(self) -> float:
        """Get current simulation time using the facade."""
        return self.sumo_facade.get_current_time()
        
    def get_edge_list(self) -> List[str]:
        """
        Get list of all edge IDs in the network.
        
        Returns:
            List of edge identifiers
        """
        return self.sumo_facade.get_traci_instance().edge.getIDList()
        
    def get_arrived_vehicles(self) -> List[str]:
        """Get vehicles that arrived using the facade."""
        return self.sumo_facade.get_arrived_vehicles()
        
    def get_departed_vehicles(self) -> List[str]:
        """Get vehicles that departed using the facade."""
        return self.sumo_facade.get_departed_vehicles()
        
    def get_active_vehicles(self) -> List[str]:
        """Get active vehicles using the facade."""
        return self.sumo_facade.get_active_vehicles()
        
    def get_vehicle_position(self, vehicle_id: str) -> Tuple[float, float]:
        """Get vehicle position using the facade."""
        return self.sumo_facade.get_vehicle_position(vehicle_id)
        
    def get_vehicle_speed(self, vehicle_id: str) -> float:
        """Get vehicle speed using the facade."""
        return self.sumo_facade.get_vehicle_speed(vehicle_id)
        
    def vehicle_exists(self, vehicle_id: str) -> bool:
        """Check if vehicle exists using the facade."""
        return self.sumo_facade.vehicle_exists(vehicle_id)
        
    # Convenience method for route generation with random selection
    def select_random_edges(self, edge_list: List[str], rng: random.Random) -> Tuple[str, str]:
        """
        Select two random edges for route generation.
        
        Args:
            edge_list: List of available edges
            rng: Random number generator
            
        Returns:
            Tuple of (from_edge, to_edge)
        """
        edge_from = rng.choice(edge_list)
        edge_to = rng.choice(edge_list)
        return edge_from, edge_to
