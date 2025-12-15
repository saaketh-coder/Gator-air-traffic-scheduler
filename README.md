# Gator Air Traffic Slot Scheduler

**Author:** Saaketh Balachendil  
**Course:** COP 5536 - Fall 2025 [cite: 2, 5]  
**Language:** Python  

## Project Overview

The Gator Air Traffic Slot Scheduler is a simulation of a non-preemptive, priority-based air traffic control system[cite: 7]. [cite_start]The core of the system is the `GatorAirTrafficScheduler` class, which manages all operations and data structures[cite: 8].

The system utilizes a **two-phase update** logic:
1.  **Phase 1:** Settles completed flights.
2.  **Phase 2:** Reschedules any unsatisfied flights before each operation to ensure optimal slot allocation[cite: 15].

## System Architecture

The project is structured into four main components[cite: 9]:

1.  [cite_start]**Main Execution:** Parses command-line arguments to get the input filename and reads the input line by line, routing commands to the scheduler [cite: 10-12].
2.  [cite_start]**Scheduler Class (`GatorAirTrafficScheduler`):** Holds all data structures and implements the 10 required public operations [cite: 13-14].
3.  [cite_start]**Custom Data Structures:** Self-contained implementations of `MinHeap` and `MaxPairingHeap` built from scratch[cite: 16].
4.  **Helper Classes:**
    * [cite_start]`Flight`: Holds info for a single flight (ID, priority, state, assigned times)[cite: 19].
    * [cite_start]`Runway`: Wrapper for runway items in the pool[cite: 20].
    * [cite_start]`HeapItem`: Wrapper for MinHeap tuple-based keys[cite: 21].
    * [cite_start]`PairingNode`: Node class for the MaxPairingHeap[cite: 22].

## Data Structures

[cite_start]The system relies on six specific data structures to maintain efficiency[cite: 26]:

1.  **Pending Flights Queue (`MaxPairingHeap`)**
    * **Purpose:** Stores flights in `PENDING` state.
    * [cite_start]**Ordering:** `(priority, submitTime, -flightID)` so the highest-priority flight is always popped first [cite: 30-31].

2.  **Runway Pool (`Binary MinHeap`)**
    * **Purpose:** Holds available runways.
    * [cite_start]**Ordering:** `(nextFreeTime, runwayID)` so the earliest available runway is selected[cite: 34].

3.  **Active Flights (`Hash Table` / `dict`)**
    * **Purpose:** Master record of all flights (`Pending`, `Scheduled`, `InProgress`). [cite_start]Maps `flightID` to `Flight` object for $O(1)$ lookup [cite: 38-39].

4.  **Timetable / Completions (`Binary MinHeap`)**
    * **Purpose:** Stores `SCHEDULED` and `INPROGRESS` flights.
    * [cite_start]**Ordering:** `(ETA, flightID)` to efficiently process completed flights in order [cite: 42-43].

5.  **Airline Index (`Hash Table` / `defaultdict`)**
    * **Purpose:** Maps `airlineID` to a set of `flightIDs`. [cite_start]Used by `GroundHold` to quickly find flights in a specific airline range [cite: 46-47].

6.  **Handles (`Hash Table` / `dict`)**
    * **Purpose:** Maps `flightID` to its `PairingNode` in the pending heap. [cite_start]Enables $O(\log n)$ updates for `Reprioritize` and `CancelFlight` [cite: 50-51].

## Supported Operations

[cite_start]The system supports the following commands via the input file [cite: 53-110]:

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
