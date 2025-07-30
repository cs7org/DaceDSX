"""
SUMO Manager - Main interface for SUMO operations

This class encapsulates all SUMO setup, initialization, and cleanup operations.
It provides a clean API for starting and stopping SUMO simulations.
"""

import os
import sys
from typing import List, Optional


class SumoManager:
    """
    Manages SUMO environment setup, process lifecycle, and TraCI connection.
    """
    
    def __init__(self):
        self.traci = None
        self._is_initialized = False
        self._is_running = False
        
    def initialize_sumo_environment(self) -> None:
        """
        Initialize SUMO environment by setting up SUMO_HOME and importing TraCI.
        
        Raises:
            SystemExit: If SUMO_HOME environment variable is not set
        """
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare environment variable 'SUMO_HOME'")
            
        # Import traci after setting up the path
        import traci
        import traci.constants as tc
        
        self.traci = traci
        self.tc = tc
        self._is_initialized = True
        
    def start_simulation(self, sumo_binary: str, sumo_cfg: str, seed: int, 
                        additional_args: Optional[List[str]] = None) -> None:
        """
        Start SUMO simulation with specified configuration.
        
        Args:
            sumo_binary: Path to SUMO executable
            sumo_cfg: Path to SUMO configuration file
            seed: Random seed for simulation
            additional_args: Additional command line arguments for SUMO
        """
        if not self._is_initialized:
            raise RuntimeError("SUMO environment not initialized. Call initialize_sumo_environment() first.")
            
        sumo_cmd = [sumo_binary, "-c", sumo_cfg, "--seed", str(int(seed)), "-S"]
        if additional_args:
            sumo_cmd.extend(additional_args)
            
        self.traci.start(sumo_cmd)
        self._is_running = True
        
    def close_simulation(self) -> None:
        """
        Close the SUMO simulation and clean up TraCI connection.
        """
        if self._is_running and self.traci:
            self.traci.close()
            self._is_running = False
            
    def is_running(self) -> bool:
        """
        Check if SUMO simulation is currently running.
        
        Returns:
            True if simulation is running, False otherwise
        """
        return self._is_running
        
    def get_traci_instance(self):
        """
        Get the TraCI instance for direct access if needed.
        
        Returns:
            TraCI instance
        """
        if not self._is_initialized:
            raise RuntimeError("SUMO environment not initialized.")
        return self.traci
