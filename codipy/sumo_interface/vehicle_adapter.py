"""
Vehicle Interface Adapter

This adapter provides a clean interface for Vehicle class to interact with SUMO
through our abstracted interface instead of direct TraCI calls.
"""

from sumo_interface import SumoFacade
from typing import Tuple


class VehicleSimulationAdapter:
    """Helper class to provide simulation-related methods for Vehicle."""
    
    def __init__(self, sumo_facade: SumoFacade):
        self.sumo_facade = sumo_facade
        
    def getDeltaT(self) -> float:
        """Get simulation step length (delta time)."""
        return self.sumo_facade.get_traci_instance().simulation.getDeltaT()


class VehicleControlAdapter:
    """Helper class to provide vehicle control methods."""
    
    def __init__(self, sumo_facade: SumoFacade):
        self.sumo_facade = sumo_facade
        
    def setColor(self, vehicle_id: str, color: Tuple[int, int, int, int]) -> None:
        """Set vehicle color."""
        self.sumo_facade.get_traci_instance().vehicle.setColor(vehicle_id, color)


class VehicleAdapter:
    """
    Adapter to provide Vehicle-specific SUMO operations through our interface.
    Provides TraCI-like interface structure for backward compatibility.
    """
    
    def __init__(self, sumo_facade: SumoFacade):
        self.sumo_facade = sumo_facade
        # Provide TraCI-like interface structure
        self.simulation = VehicleSimulationAdapter(sumo_facade)
        self.vehicle = VehicleControlAdapter(sumo_facade)
        
    def get_simulation_delta_time(self) -> float:
        """
        Get the simulation step length (delta time).
        
        Returns:
            Step length in seconds
        """
        return self.simulation.getDeltaT()
        
    def set_vehicle_color(self, vehicle_id: str, color: Tuple[int, int, int, int]) -> None:
        """
        Set the color of a vehicle in the SUMO GUI.
        
        Args:
            vehicle_id: Vehicle identifier
            color: RGBA color tuple (red, green, blue, alpha)
        """
        self.vehicle.setColor(vehicle_id, color)
        
    def get_vehicle_position(self, vehicle_id: str) -> Tuple[float, float]:
        """Get vehicle position using the facade."""
        return self.sumo_facade.get_vehicle_position(vehicle_id)
        
    def get_vehicle_speed(self, vehicle_id: str) -> float:
        """Get vehicle speed using the facade."""
        return self.sumo_facade.get_vehicle_speed(vehicle_id)
        
    def vehicle_exists(self, vehicle_id: str) -> bool:
        """Check if vehicle exists using the facade."""
        return self.sumo_facade.vehicle_exists(vehicle_id)
