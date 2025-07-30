# FleetManager and Vehicle Interface Update Plan

## Current State Analysis

### FleetManager.py Issues
- **19 direct TraCI calls** scattered throughout the class
- Passes raw TraCI instance to Vehicle objects  
- Uses TraCI for: route finding, vehicle addition, context subscriptions, time queries, edge lists

### Vehicle.py Issues  
- **3 direct TraCI calls** for colors and simulation delta time
- Gets raw TraCI instance from FleetManager
- Minimal usage but still bypasses our interface

## Recommended Updates

### Option 1: Minimal Changes (Recommended)
**Keep existing signatures but update internal implementation**

#### FleetManager Updates:
1. **Constructor**: Change parameter from `traci` to `fleet_adapter: FleetManagerAdapter`
2. **Internal methods**: Replace direct TraCI calls with adapter methods
3. **get_traci() method**: Return the adapter instead of raw TraCI

#### Vehicle Updates:
1. **Constructor**: Accept `VehicleAdapter` instead of getting raw TraCI
2. **Replace direct calls**: Use adapter methods for colors and delta time

### Option 2: Full Refactoring (Future Enhancement)
**Complete interface isolation with new method signatures**

#### Benefits of Option 1 (Minimal):
- ✅ Maintains existing API contracts
- ✅ Minimal breaking changes to other components  
- ✅ Easy to implement and test
- ✅ Backward compatibility maintained

#### Benefits of Option 2 (Full):
- ✅ Complete interface isolation
- ✅ Better long-term architecture
- ❌ Requires updating all dependent code
- ❌ More complex migration

## Implementation Plan (Option 1)

### Step 1: Update simulation_run.py (Already Done)
```python
# Create adapter for FleetManager
fleet_adapter = FleetManagerAdapter(sumo_facade)

# Pass adapter instead of raw TraCI
vehicle_fleet = fleetManager.FleetManager(fleet_adapter, ...)
```

### Step 2: Update FleetManager Constructor
```python
def __init__(self, fleet_adapter: FleetManagerAdapter, backend_server: object, ...):
    self.__fleet_adapter = fleet_adapter  # Store adapter
    # Replace all self.__traci calls with self.__fleet_adapter calls
```

### Step 3: Update FleetManager Methods
Replace direct TraCI usage:
```python
# Before:
route = self.__traci.simulation.findRoute(edge_from, edge_to, "DEFAULT_VEHTYPE")
self.__traci.route.add(route_name, list(route.edges))
self.__traci.vehicle.add(vehicle_id, route_id)

# After:  
route = self.__fleet_adapter.find_route(edge_from, edge_to, "DEFAULT_VEHTYPE")
self.__fleet_adapter.add_route(route_name, list(route.edges))
self.__fleet_adapter.add_vehicle(vehicle_id, route_id)
```

### Step 4: Update Vehicle Class
```python
# Constructor: Accept VehicleAdapter
def __init__(self, ..., vehicle_adapter: VehicleAdapter):
    self.__vehicle_adapter = vehicle_adapter
    self.__step_length = vehicle_adapter.get_simulation_delta_time()

# Update color method:
def set_color(self, colors):
    self.__vehicle_adapter.set_vehicle_color(self.__vehID, colors)
```

### Step 5: Update FleetManager's get_traci() method
```python
def get_traci(self):
    # Return vehicle adapter for backward compatibility
    return VehicleAdapter(self.__fleet_adapter.sumo_facade)
```

## Benefits of This Approach

### 1. **Clean Architecture**
- All SUMO interactions go through our interface
- Centralized SUMO logic in adapters
- Easy to mock for testing

### 2. **Maintainability**  
- SUMO API changes only affect adapters
- Clear separation of concerns
- Easier to debug SUMO-related issues

### 3. **Testability**
- Can mock adapters for unit testing
- No need for actual SUMO in tests
- Better isolation of business logic

### 4. **Type Safety**
- Proper type hints throughout
- IDE support and autocompletion
- Runtime error checking

## Migration Timeline

### Phase 1: FleetManager (Priority 1)
- Update constructor to accept FleetManagerAdapter
- Replace all direct TraCI calls with adapter methods
- Update get_traci() method

### Phase 2: Vehicle (Priority 2)  
- Update constructor to accept VehicleAdapter
- Replace direct TraCI calls with adapter methods
- Test vehicle color and timing functionality

### Phase 3: Testing & Validation
- Unit tests for both classes with mocked adapters
- Integration tests with actual SUMO
- Performance benchmarking

## Risk Assessment

### Low Risk:
- ✅ Maintains existing public APIs
- ✅ No changes to other dependent classes
- ✅ Can be done incrementally

### Medium Risk:
- ⚠️ Need to verify all TraCI usage patterns are covered
- ⚠️ Ensure adapters have all required functionality
- ⚠️ Test performance impact of additional abstraction layer

## Conclusion

**Recommendation: Proceed with Option 1 (Minimal Changes)**

This approach provides the benefits of clean interface architecture while minimizing disruption to the existing codebase. The adapters provide a clean abstraction layer that can be easily extended in the future.
