"""
SUMO Facade - Unified interface for all SUMO operations

This class provides a single entry point for all SUMO-related operations,
combining the functionality of SumoManager, SimulationController, and VehicleDataProvider.
"""

from typing import List, Tuple, Optional
from .sumo_manager import SumoManager
from .simulation_controller import SimulationController
from .vehicle_data_provider import VehicleDataProvider


class SumoFacade:
    """
    Unified facade for all SUMO operations.
    Provides a single interface that combines all SUMO-related functionality.
    """
    
    def __init__(self):
        self.sumo_manager = SumoManager()
        self.simulation_controller = None
        self.vehicle_data_provider = None
        
    def initialize_and_start(self, sumo_binary: str, sumo_cfg: str, seed: int,
                           additional_args: Optional[List[str]] = None) -> None:
        """
        Initialize SUMO environment and start simulation.
        
        Args:
            sumo_binary: Path to SUMO executable
            sumo_cfg: Path to SUMO configuration file
            seed: Random seed for simulation
            additional_args: Additional command line arguments for SUMO
        """
        # Initialize SUMO environment
        self.sumo_manager.initialize_sumo_environment()
        
        # Start simulation
        self.sumo_manager.start_simulation(sumo_binary, sumo_cfg, seed, additional_args)
        
        # Initialize controllers with TraCI instance
        traci_instance = self.sumo_manager.get_traci_instance()
        self.simulation_controller = SimulationController(traci_instance)
        self.vehicle_data_provider = VehicleDataProvider(traci_instance)
        
    def close(self) -> None:
        """Close the SUMO simulation and clean up resources."""
        self.sumo_manager.close_simulation()
        
    def is_running(self) -> bool:
        """Check if SUMO simulation is currently running."""
        return self.sumo_manager.is_running()
        
    # Simulation Control Methods
    def step(self) -> None:
        """Advance simulation by one time step."""
        if not self.simulation_controller:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        self.simulation_controller.step()
        
    def get_current_time(self) -> float:
        """Get current simulation time."""
        if not self.simulation_controller:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.simulation_controller.get_current_time()
        
    def get_arrived_vehicles(self) -> List[str]:
        """Get list of vehicles that have completed their routes."""
        if not self.simulation_controller:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.simulation_controller.get_arrived_vehicles()
        
    def get_departed_vehicles(self) -> List[str]:
        """Get list of vehicles that have entered the simulation."""
        if not self.simulation_controller:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.simulation_controller.get_departed_vehicles()
        
    def get_active_vehicles(self) -> List[str]:
        """Get list of all currently active vehicles."""
        if not self.simulation_controller:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.simulation_controller.get_active_vehicles()
        
    def is_simulation_finished(self) -> bool:
        """Check if simulation has finished."""
        if not self.simulation_controller:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.simulation_controller.is_simulation_finished()
        
    # Vehicle Data Methods
    def get_vehicle_position(self, vehicle_id: str) -> Tuple[float, float]:
        """Get vehicle's current position."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.get_vehicle_position(vehicle_id)
        
    def get_vehicle_speed(self, vehicle_id: str) -> float:
        """Get vehicle's current speed."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.get_vehicle_speed(vehicle_id)
        
    def get_vehicle_route(self, vehicle_id: str) -> List[str]:
        """Get vehicle's planned route."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.get_vehicle_route(vehicle_id)
        
    def get_vehicle_road_id(self, vehicle_id: str) -> str:
        """Get the current road ID where the vehicle is located."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.get_vehicle_road_id(vehicle_id)
        
    def get_vehicle_lane_id(self, vehicle_id: str) -> str:
        """Get the current lane ID where the vehicle is located."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.get_vehicle_lane_id(vehicle_id)
        
    def get_vehicle_angle(self, vehicle_id: str) -> float:
        """Get vehicle's current heading angle."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.get_vehicle_angle(vehicle_id)
        
    def get_distance_between_vehicles(self, vehicle_id1: str, vehicle_id2: str) -> float:
        """Calculate distance between two vehicles."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.get_distance_between_vehicles(vehicle_id1, vehicle_id2)
        
    def get_vehicles_in_range(self, reference_vehicle_id: str, max_distance: float) -> List[str]:
        """Get all vehicles within a specified range of a reference vehicle."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.get_vehicles_in_range(reference_vehicle_id, max_distance)
        
    def vehicle_exists(self, vehicle_id: str) -> bool:
        """Check if a vehicle exists in the simulation."""
        if not self.vehicle_data_provider:
            raise RuntimeError("Simulation not initialized. Call initialize_and_start() first.")
        return self.vehicle_data_provider.vehicle_exists(vehicle_id)
        
    # Direct TraCI access (for backward compatibility if needed)
    def get_traci_instance(self):
        """
        Get direct access to TraCI instance.
        Use this method sparingly - prefer using the facade methods.
        """
        return self.sumo_manager.get_traci_instance()
