import math
import ast
from typing import Dict, List, Any


def register_access_points_from_file(traci_interface: "TraCIInterface", ap_coords_file_path: str) -> int:
    """
    Register WLAN Access Points from coordinates file.
    
    File format: One tuple per line: (x, y, communication_range_meters)
    Example:
        (534.56, 1974.48, 40.66)
        (424.23, 1813.27, 78.46)
    
    Creates POIs with IDs: wlan_ap_0, wlan_ap_1, wlan_ap_2, ...
    
    Args:
        traci_interface: The TraCIInterface instance to register POIs with
        ap_coords_file_path: Path to the AP coordinates file (from config <ap-coordinates>)
    
    Returns:
        Number of access points registered
    
    Example:
        >>> traci = TraCIInterface()
        >>> count = register_access_points_from_file(traci, "ap_coords.txt")
        >>> print(f"Registered {count} access points")
    """
    ap_count = 0
    
    with open(ap_coords_file_path, 'r') as coords_file:
        for i, line in enumerate(coords_file):
            line = line.strip()
            if not line:
                continue
            
            try:
                # Parse tuple: (x, y, range)
                coord_tuple = ast.literal_eval(line)
                
                if len(coord_tuple) != 3:
                    print(f"Warning: Skipping line {i+1} - expected 3 values, got {len(coord_tuple)}")
                    continue
                
                x, y, comm_range = coord_tuple
                poi_id = f"wlan_ap_{ap_count}"
                
                traci_interface.register_poi(
                    poi_id,
                    {"x": float(x), "y": float(y)},
                    float(comm_range)
                )
                
                ap_count += 1
                
            except (ValueError, SyntaxError) as e:
                print(f"Warning: Failed to parse line {i+1}: {line} - {e}")
                continue
    
    return ap_count


class TraCIInterface:
    """
    Consume-only replacement for the SUMO TraCI API.
    Builds an internal view of the world from raw vehicle messages.
    """

    def __init__(self, step_length: float = 0.1, vehicle_timeout: float = 5.0):
        self.current_time: float = 0.0
        self.step_length: float = step_length
        self.vehicle_timeout: float = vehicle_timeout

        self.vehicles: Dict[str, Dict[str, Any]] = {}
        self.vehicle_last_seen: Dict[str, float] = {}
        self.known_vehicle_ids: set[str] = set()

        self.departed_this_step: List[str] = []
        self.arrived_this_step: List[str] = []

        self._pois: Dict[str, Dict[str, Any]] = {}

        self.simulation = self._Simulation(self)
        self.vehicle = self._Vehicle(self)
        self.poi = self._POI(self)
        self.edge = self._Edge(self)
        self.constants = self._Constants()

    def process_vehicle_message(self, message: Dict[str, Any]):
        vehicle_id = message["vehicleID"]
        timestamp = message.get("timestamp")
        if timestamp is not None:
            self.current_time = timestamp

        self.vehicles[vehicle_id] = message
        self.vehicle_last_seen[vehicle_id] = self.current_time

        if vehicle_id not in self.known_vehicle_ids:
            self.departed_this_step.append(vehicle_id)
            self.known_vehicle_ids.add(vehicle_id)

    def simulationStep(self):
        timed_out = []
        for vehicle_id, last_seen in list(self.vehicle_last_seen.items()):
            if self.current_time - last_seen > self.vehicle_timeout:
                timed_out.append(vehicle_id)

        for vehicle_id in timed_out:
            self.arrived_this_step.append(vehicle_id)
            self.vehicle_last_seen.pop(vehicle_id, None)
            self.vehicles.pop(vehicle_id, None)

    def ingest_snapshot(
        self,
        current_time: float,
        vehicle_snapshots: List[Dict[str, Any]],
        departed_ids: List[str],
        arrived_ids: List[str],
    ) -> None:
        """Load a full-state snapshot coming from an external data source."""

        self.current_time = current_time
        self.departed_this_step = list(departed_ids)
        self.arrived_this_step = list(arrived_ids)

        for vehicle_id in arrived_ids:
            self.vehicle_last_seen.pop(vehicle_id, None)
            self.vehicles.pop(vehicle_id, None)
            self.known_vehicle_ids.discard(vehicle_id)

        for snapshot in vehicle_snapshots:
            vehicle_id = snapshot["vehicleID"]
            snapshot.setdefault("timestamp", current_time)
            self.vehicles[vehicle_id] = snapshot
            self.vehicle_last_seen[vehicle_id] = current_time
            self.known_vehicle_ids.add(vehicle_id)

    def start(self, _cmd: List[str]):
        return

    def close(self):
        return

    def register_poi(self, poi_id: str, position: Dict[str, float], communication_range: float) -> None:
        """
        Register a Point of Interest (WLAN Access Point) for proximity detection.
        
        Args:
            poi_id: POI identifier (e.g., "wlan_ap_0", "wlan_ap_1", ...)
            position: Position dict with keys {"x": float, "y": float}
            communication_range: Coverage radius in meters (per-AP value)
        
        Note:
            AP coordinates file format: (x, y, communication_range_meters)
            Example line: (534.56, 1974.48, 40.66)
            Where:
                x, y = position in meters
                communication_range_meters = per-AP coverage radius
        """
        self._pois[poi_id] = {
            "position": position,
            "range": communication_range,
        }

    class _Simulation:
        def __init__(self, parent: "TraCIInterface"):
            self._parent = parent

        def getTime(self) -> float:
            return self._parent.current_time

        def getDeltaT(self) -> float:
            return self._parent.step_length

        def getArrivedIDList(self) -> List[str]:
            arrived = self._parent.arrived_this_step.copy()
            self._parent.arrived_this_step.clear()
            return arrived

        def getDepartedIDList(self) -> List[str]:
            departed = self._parent.departed_this_step.copy()
            self._parent.departed_this_step.clear()
            return departed

    class _Vehicle:
        VAR_POSITION = 66

        def __init__(self, parent: "TraCIInterface"):
            self._parent = parent
            # Store subscription configs per vehicle (set by consumers like FleetManager)
            self._subscriptions: Dict[str, float] = {}

        def subscribeContext(
            self,
            vehicle_id: str,
            domain: int,
            range_meters: float,
            variables: List[int]
        ) -> None:
            """
            Configure context subscription for a vehicle (mimics TraCI API).
            Called by consumers (e.g., FleetManager) to set proximity detection range.
            
            Args:
                vehicle_id: Vehicle to subscribe
                domain: Domain constant (CMD_GET_VEHICLE_VARIABLE)
                range_meters: Communication/proximity range in meters
                variables: List of variable IDs to track (VAR_POSITION, VAR_SPEED, etc.)
            
            Example (from FleetManager):
                traci.vehicle.subscribeContext(
                    vehicle_id,
                    traci.constants.CMD_GET_VEHICLE_VARIABLE,
                    200.0,  # v2v_communication_distance from config
                    [traci.constants.VAR_SPEED, traci.constants.VAR_POSITION]
                )
            """
            self._subscriptions[vehicle_id] = range_meters

        def getContextSubscriptionResults(self, vehicle_id: str) -> Dict[str, Dict[int, List[float]]]:
            """
            Get nearby vehicles within subscribed range.
            Uses the range configured via subscribeContext() for this vehicle.
            """
            vehicles = self._parent.vehicles
            if vehicle_id not in vehicles:
                return {}

            # Get the range configured for this vehicle
            range_meters = self._subscriptions.get(vehicle_id)
            if range_meters is None:
                # Vehicle not subscribed - return empty (or could return all as fallback)
                return {}

            sender_pos = vehicles[vehicle_id]["position"]
            sender_xy = (sender_pos["x"], sender_pos["y"])

            results: Dict[str, Dict[int, List[float]]] = {
                vehicle_id: {self.VAR_POSITION: [sender_xy[0], sender_xy[1]]}
            }

            for other_id, other_data in vehicles.items():
                if other_id == vehicle_id:
                    continue

                other_pos = other_data["position"]
                other_xy = (other_pos["x"], other_pos["y"])
                distance = math.dist(sender_xy, other_xy)

                if distance <= range_meters:
                    results[other_id] = {self.VAR_POSITION: [other_xy[0], other_xy[1]]}

            return results

    class _POI:
        VAR_POSITION = 66

        def __init__(self, parent: "TraCIInterface"):
            self._parent = parent
            # Store subscription configs per POI (set by consumers like WLAN_AP)
            self._subscriptions: Dict[str, Dict[str, Any]] = {}

        def add(
            self,
            poi_id: str,
            x: float,
            y: float,
            color=None,
            poiType: str = "",
            layer: int = 0,
            imgFile: str = ""
        ) -> None:
            """
            Add a POI (Point of Interest) - compatibility wrapper for active TraCI API.
            Called by WlanAPManager.place_aps() in active mode for GUI rendering.
            In passive mode, registers POI for proximity calculation.
            
            Args:
                poi_id: POI identifier (e.g., "wlan_ap_0")
                x, y: Position coordinates
                color: GUI color (ignored in passive mode)
                poiType: POI type string (ignored in passive mode)
                layer: Display layer (ignored in passive mode)
                imgFile: Image file (ignored in passive mode)
            
            Note: Range will be set later via subscribeContext()
            """
            # Register POI with default range (will be updated by subscribeContext)
            self._parent.register_poi(poi_id, {"x": float(x), "y": float(y)}, 0.0)

        def subscribeContext(
            self,
            poi_id: str,
            domain: int,
            range_meters: float,
            variables: List[int]
        ) -> None:
            """
            Configure context subscription for a POI (mimics TraCI API).
            Called by consumers (e.g., WLAN_AP) to set coverage range.
            
            Args:
                poi_id: POI identifier (e.g., "wlan_ap_0")
                domain: Domain constant (CMD_GET_VEHICLE_VARIABLE)
                range_meters: Coverage range in meters (per-AP value)
                variables: List of variable IDs to track (VAR_POSITION, etc.)
            
            Example (from WLAN_AP.__init__):
                traci.poi.subscribeContext(
                    "wlan_ap_0",
                    traci.constants.CMD_GET_VEHICLE_VARIABLE,
                    40.66,  # Per-AP range from ap_coords.txt
                    [traci.constants.VAR_POSITION]
                )
            """
            self._subscriptions[poi_id] = {
                "range": range_meters,
                "variables": variables
            }
            
            # Update the POI's range if it was already registered via add()
            if poi_id in self._parent._pois:
                self._parent._pois[poi_id]["range"] = range_meters

        def getContextSubscriptionResults(self, poi_id: str) -> Dict[str, Dict[int, List[float]]]:
            """
            Get nearby vehicles within subscribed range.
            Uses the range configured via subscribeContext() for this POI.
            """
            subscription = self._subscriptions.get(poi_id)
            if subscription is None:
                # POI not subscribed - no results
                return {}

            # Note: We don't need explicit position registration anymore
            # The subscription itself defines the POI (will be set by WLAN_AP)
            # For now, return empty if no position data
            # In Phase 3/4, WLAN_AP will handle this properly
            
            range_meters = subscription["range"]
            
            # POI position should be tracked separately or passed
            # For now, maintain compatibility with register_poi if used
            poi_entry = self._parent._pois.get(poi_id)
            if poi_entry is None:
                # POI position not registered - can't calculate proximity
                return {}

            poi_pos = poi_entry["position"]
            poi_xy = (poi_pos["x"], poi_pos["y"])

            results: Dict[str, Dict[int, List[float]]] = {
                poi_id: {self.VAR_POSITION: [poi_xy[0], poi_xy[1]]}
            }

            for vehicle_id, data in self._parent.vehicles.items():
                vehicle_pos = data["position"]
                vehicle_xy = (vehicle_pos["x"], vehicle_pos["y"])
                distance = math.dist(poi_xy, vehicle_xy)

                if distance <= range_meters:
                    results[vehicle_id] = {self.VAR_POSITION: [vehicle_xy[0], vehicle_xy[1]]}

            return results

    class _Edge:
        """Edge (road network) API - minimal implementation for passive mode."""
        
        def __init__(self, parent: "TraCIInterface"):
            self._parent = parent
            self._edge_ids: List[str] = []

        def getIDList(self) -> List[str]:
            """
            Get list of edge IDs in the network.
            
            In passive mode, returns empty list since we don't have network topology.
            FleetManager uses this for route validation in active mode.
            In passive mode, vehicles come with pre-assigned routes from external sim.
            
            Returns:
                Empty list (no network topology in passive mode)
            """
            return self._edge_ids

    class _Constants:
        """TraCI constants for API compatibility."""
        
        # Context subscription domains
        CMD_GET_VEHICLE_VARIABLE = 0xa4
        CMD_GET_POI_VARIABLE = 0xa7
        
        # Variable IDs
        VAR_POSITION = 66
        VAR_SPEED = 64
        VAR_ACCELERATION = 114
        VAR_ANGLE = 67
        VAR_ROAD_ID = 80
        VAR_LANE_INDEX = 82