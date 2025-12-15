# Gator Air Traffic Slot Scheduler

**Author:** Saaketh Balachendil  
**Course:** COP 5536 - Fall 2025  
**Language:** Python  

## Project Overview

The Gator Air Traffic Slot Scheduler is a simulation of a non-preemptive, priority-based air traffic control system. The core of the system is the `GatorAirTrafficScheduler` class, which manages all operations and data structures.

The system utilizes a **two-phase update** logic:
1.  **Phase 1:** Settles completed flights.
2.  **Phase 2:** Reschedules any unsatisfied flights before each operation to ensure optimal slot allocation.

## System Architecture

The project is structured into four main components:

1.  **Main Execution:** Parses command-line arguments to get the input filename and reads the input line by line, routing commands to the scheduler.
2.  **Scheduler Class (`GatorAirTrafficScheduler`):** Holds all data structures and implements the 10 required public operations.
3.  **Custom Data Structures:** Self-contained implementations of `MinHeap` and `MaxPairingHeap` built from scratch.
4.  **Helper Classes:**
    * `Flight`: Holds info for a single flight (ID, priority, state, assigned times).
    * `Runway`: Wrapper for runway items in the pool.
    * `HeapItem`: Wrapper for MinHeap tuple-based keys.
    * `PairingNode`: Node class for the MaxPairingHeap.

## Data Structures

The system relies on six specific data structures to maintain efficiency:

1.  **Pending Flights Queue (`MaxPairingHeap`)**
    * **Purpose:** Stores flights in `PENDING` state.
    * **Ordering:** `(priority, submitTime, -flightID)` so the highest-priority flight is always popped first.

2.  **Runway Pool (`Binary MinHeap`)**
    * **Purpose:** Holds available runways.
    * **Ordering:** `(nextFreeTime, runwayID)` so the earliest available runway is selected.

3.  **Active Flights (`Hash Table` / `dict`)**
    * **Purpose:** Master record of all flights (`Pending`, `Scheduled`, `InProgress`). Maps `flightID` to `Flight` object for $O(1)$ lookup.

4.  **Timetable / Completions (`Binary MinHeap`)**
    * **Purpose:** Stores `SCHEDULED` and `INPROGRESS` flights.
    * **Ordering:** `(ETA, flightID)` to efficiently process completed flights in order.

5.  **Airline Index (`Hash Table` / `defaultdict`)**
    * **Purpose:** Maps `airlineID` to a set of `flightIDs`. Used by `GroundHold` to quickly find flights in a specific airline range.

6.  **Handles (`Hash Table` / `dict`)**
    * **Purpose:** Maps `flightID` to its `PairingNode` in the pending heap. Enables $O(\log n)$ updates for `Reprioritize` and `CancelFlight`.

## Supported Operations

The system supports the following commands via the input file:

* `Initialize(runwayCount)`: Starts the system with a specific number of runways.
* `SubmitFlight(flightID, airlineID, submitTime, priority, duration)`: Adds a new flight request.
* `CancelFlight(flightID, currentTime)`: Removes a flight if it has not yet started.
* `Reprioritize(flightID, currentTime, newPriority)`: Changes a flight's priority before it starts.
* `AddRunways(count, currentTime)`: Adds new runways and triggers rescheduling.
* `GroundHold(airlineLow, airlineHigh, currentTime)`: Removes unsatisfied flights within an airline ID range.
* `PrintActive()`: Shows all flights currently in the system.
* `PrintSchedule(t1, t2)`: Shows scheduled (but not started) flights with ETAs in the range `[t1, t2]`.
* `Tick(t)`: Advances the system clock to time `t`.
* `Quit()`: Terminates the program.

## Usage

To run the program, execute the main script with the input filename as a command-line argument.

```bash
python main.py <input_filename>
