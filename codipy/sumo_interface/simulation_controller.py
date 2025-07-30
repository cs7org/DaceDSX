"""
Simulation Controller - Controls SUMO simulation execution

This class provides an interface for controlling the simulation step-by-step execution,
time management, and simulation state queries.
"""

from typing import List


class SimulationController:
    """
    Controls SUMO simulation execution and provides simulation state information.
    """
    
    def __init__(self, traci_instance):
        """
        Initialize simulation controller with TraCI instance.
        
        Args:
            traci_instance: TraCI instance from SumoManager
        """
        self.traci = traci_instance
        
    def step(self) -> None:
        """
        Advance simulation by one time step.
        """
        self.traci.simulationStep()
        
    def get_current_time(self) -> float:
        """
        Get current simulation time.
        
        Returns:
            Current simulation time in seconds
        """
        return self.traci.simulation.getTime()
        
    def get_arrived_vehicles(self) -> List[str]:
        """
        Get list of vehicles that have completed their routes in the current step.
        
        Returns:
            List of vehicle IDs that arrived at their destination
        """
        return self.traci.simulation.getArrivedIDList()
        
    def get_departed_vehicles(self) -> List[str]:
        """
        Get list of vehicles that have entered the simulation in the current step.
        
        Returns:
            List of vehicle IDs that departed (entered the network)
        """
        return self.traci.simulation.getDepartedIDList()
        
    def get_active_vehicles(self) -> List[str]:
        """
        Get list of all currently active vehicles in the simulation.
        
        Returns:
            List of all active vehicle IDs
        """
        return self.traci.vehicle.getIDList()
        
    def is_simulation_finished(self) -> bool:
        """
        Check if simulation has finished (no more vehicles to process).
        
        Returns:
            True if simulation is finished, False otherwise
        """
        return self.traci.simulation.getMinExpectedNumber() <= 0
