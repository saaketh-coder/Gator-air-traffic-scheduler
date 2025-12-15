import sys
import os
from collections import defaultdict


class Flight:
    def __init__(self, flightID, airlineID, submitTime, priority, duration):
        self.flightID = flightID
        self.airlineID = airlineID
        self.submitTime = submitTime
        self.priority = priority
        self.duration = duration
        self.state = "PENDING"          # PENDING, SCHEDULED, INPROGRESS, LANDED
        self.runwayID = -1
        self.startTime = -1
        self.ETA = -1

    def __repr__(self):
        return (f"Flight(id={self.flightID}, state={self.state}, "
                f"prio={self.priority}, start={self.startTime}, ETA={self.ETA})")


class Runway:
    def __init__(self, runwayID, nextFreeTime):
        self.runwayID = runwayID
        self.nextFreeTime = nextFreeTime

    def __lt__(self, other):
        # First by free time, then by ID to break ties
        if self.nextFreeTime != other.nextFreeTime:
            return self.nextFreeTime < other.nextFreeTime
        return self.runwayID < other.runwayID


class HeapItem:
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __lt__(self, other):
        return self.key < other.key


class MinHeap:
    def __init__(self):
        self.heap = []

    def isEmpty(self):
        return len(self.heap) == 0

    def peek(self):
        return self.heap[0] if not self.isEmpty() else None

    def push(self, item):
        self.heap.append(item)
        self._siftUp(len(self.heap) - 1)

    def pop(self):
        if self.isEmpty():
            return None
        if len(self.heap) == 1:
            return self.heap.pop()

        root = self.heap[0]
        self.heap[0] = self.heap.pop()
        self._siftDown(0)
        return root

    def clear(self):
        self.heap = []

    def _siftUp(self, idx):
        while idx > 0:
            parent = (idx - 1) // 2
            if self.heap[idx] < self.heap[parent]:
                self.heap[idx], self.heap[parent] = self.heap[parent], self.heap[idx]
                idx = parent
            else:
                break

    def _siftDown(self, idx):
        n = len(self.heap) - 1
        while True:
            left = 2 * idx + 1
            right = 2 * idx + 2
            smallest = idx

            if left <= n and self.heap[left] < self.heap[smallest]:
                smallest = left
            if right <= n and self.heap[right] < self.heap[smallest]:
                smallest = right

            if smallest != idx:
                self.heap[idx], self.heap[smallest] = self.heap[smallest], self.heap[idx]
                idx = smallest
            else:
                break


class PairingNode:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.child = None
        self.sibling = None
        self.prev = None


class MaxPairingHeap:
    def __init__(self):
        self.root = None
        self._count = 0

    def isEmpty(self):
        return self.root is None

    def peek(self):
        return self.root.value if not self.isEmpty() else None

    def _merge(self, a, b):
        if not a: return b
        if not b: return a
        if a.key > b.key:
            b.prev = a
            b.sibling = a.child
            if a.child:
                a.child.prev = b
            a.child = b
            return a
        else:
            a.prev = b
            a.sibling = b.child
            if b.child:
                b.child.prev = a
            b.child = a
            return b

    def push(self, key, value):
        node = PairingNode(key, value)
        self.root = self._merge(self.root, node)
        self._count += 1
        return node

    def pop(self):
        if self.isEmpty():
            return None
        old_root = self.root
        val = old_root.value
        self.root = self._mergeSiblings(old_root.child)
        self._count -= 1
        return val

    def _mergeSiblings(self, first):
        if not first:
            return None
        if not first.sibling:
            return first

        nodes = []
        cur = first
        while cur:
            nxt = cur.sibling
            if nxt:
                nxt2 = nxt.sibling
                cur.prev = cur.sibling = None
                nxt.prev = nxt.sibling = None
                merged = self._merge(cur, nxt)
                nodes.append(merged)
                cur = nxt2
            else:
                cur.prev = cur.sibling = None
                nodes.append(cur)
                cur = None

        result = nodes.pop()
        while nodes:
            result = self._merge(nodes.pop(), result)
        return result

    def _cutNode(self, node):
        if not node.prev:
            return
        if node.prev.child == node:
            node.prev.child = node.sibling
        else:
            node.prev.sibling = node.sibling
        if node.sibling:
            node.sibling.prev = node.prev
        node.prev = node.sibling = None

    def updateKey(self, node, newKey):
        if newKey == node.key:
            return
        was_increase = newKey > node.key
        node.key = newKey

        if node == self.root or not was_increase:
            if not was_increase:
                self._cutNode(node)
                self.root = self._merge(self.root, node)
            return

        if node != self.root:
            self._cutNode(node)
            self.root = self._merge(self.root, node)

    def erase(self, node):
        if node == self.root:
            self.pop()
        else:
            self._cutNode(node)
            merged = self._mergeSiblings(node.child)
            self.root = self._merge(self.root, merged)
            self._count -= 1

    def clear(self):
        self.root = None
        self._count = 0


class GatorAirTrafficScheduler:
    def __init__(self, outputFileHandle):
        self.outputFile = outputFileHandle
        self.currentTime = 0
        self.nextRunwayID = 1
        self.pendingFlights = MaxPairingHeap()      # priority queue for pending flights
        self.runwayPool = MinHeap()                 # available runways
        self.activeFlights = {}                     # flightID -> Flight
        self.timetable = MinHeap()                  # (ETA, flightID) -> flightID
        self.airlineIndex = defaultdict(set)        # airlineID -> set(flightIDs)
        self.handles = {}                           # flightID -> PairingNode

    def _write(self, msg):
        self.outputFile.write(msg + "\n")

    def _printChangedEtas(self, changed):
        if not changed:
            return
        changed.sort()
        parts = [f"{fid}: {eta}" for fid, eta in changed]
        self._write(f"Updated ETAs: [{', '.join(parts)}]")

    def _advanceTime(self, newTime):
        if newTime < self.currentTime:
            return

        landed = []
        # Phase 1: Advance time and land completed flights
        if newTime > self.currentTime:
            self.currentTime = newTime

            while (not self.timetable.isEmpty() and
                   self.timetable.peek().key[0] <= self.currentTime):
                item = self.timetable.pop()
                eta, fid = item.key
                flight = self.activeFlights.get(fid)

                if not flight or flight.state == "LANDED":
                    continue

                flight.state = "LANDED"
                landed.append(flight)
                self._removeFlightFromSystemIndices(fid)
                self.activeFlights.pop(fid, None)

            # Report landings in order
            landed.sort(key=lambda f: (f.ETA, f.flightID))
            for f in landed:
                self._write(f"Flight {f.flightID} has landed at time {f.ETA}")

        # Transition scheduled -> in progress
        for flight in list(self.activeFlights.values()):
            if flight.state == "SCHEDULED" and flight.startTime <= self.currentTime:
                flight.state = "INPROGRESS"

        # Phase 2: Reschedule any unsatisfied flights
        changed = self._rescheduleUnsatisfied()
        self._printChangedEtas(changed)

    def _rescheduleUnsatisfied(self):
        old_etas = {}
        to_reschedule = []

        # Gather all pending/scheduled flights that need rescheduling
        for flight in list(self.activeFlights.values()):
            if flight.state == "SCHEDULED":
                old_etas[flight.flightID] = flight.ETA
                flight.state = "PENDING"
                to_reschedule.append(flight)

        # Pull all pending flights from heap
        while not self.pendingFlights.isEmpty():
            fid = self.pendingFlights.pop()
            self.handles.pop(fid, None)
            flight = self.activeFlights.get(fid)
            if flight and flight.state == "PENDING":
                to_reschedule.append(flight)

        # Rebuild runway pool
        self.runwayPool.clear()
        in_progress_end = {}
        self.timetable.clear()

        for flight in self.activeFlights.values():
            if flight.state == "INPROGRESS":
                in_progress_end[flight.runwayID] = max(
                    in_progress_end.get(flight.runwayID, 0), flight.ETA
                )
                key = (flight.ETA, flight.flightID)
                self.timetable.push(HeapItem(key, flight.flightID))

        for rid in range(1, self.nextRunwayID):
            free_at = in_progress_end.get(rid, 0)
            free_at = max(self.currentTime, free_at)
            self.runwayPool.push(Runway(rid, free_at))

        # Sort flights by priority, then reverse submit time, then reverse ID
        to_reschedule.sort(
            key=lambda f: (f.priority, -f.submitTime, -f.flightID),
            reverse=True
        )

        new_etas = {}
        self.pendingFlights.clear()
        self.handles.clear()

        if self.runwayPool.isEmpty():
            for flight in to_reschedule:
                flight.state = "PENDING"
                flight.runwayID = flight.startTime = flight.ETA = -1
                key = (flight.priority, -flight.submitTime, -flight.flightID)
                node = self.pendingFlights.push(key, flight.flightID)
                self.handles[flight.flightID] = node
        else:
            for flight in to_reschedule:
                runway = self.runwayPool.pop()
                start = max(self.currentTime, runway.nextFreeTime)
                eta = start + flight.duration

                flight.startTime = start
                flight.ETA = eta
                flight.runwayID = runway.runwayID
                flight.state = "SCHEDULED"

                new_etas[flight.flightID] = eta

                runway.nextFreeTime = eta
                self.runwayPool.push(runway)

                key = (eta, flight.flightID)
                self.timetable.push(HeapItem(key, flight.flightID))

        # Compute changed ETAs
        changed = []
        for fid, new_eta in new_etas.items():
            if fid in old_etas and old_etas[fid] != new_eta:
                changed.append((fid, new_eta))

        for fid in old_etas:
            if fid not in new_etas:
                changed.append((fid, -1))

        return changed

    def _removeFlightFromSystemIndices(self, flightID):
        flight = self.activeFlights.get(flightID)
        if not flight:
            return
        if flight.airlineID in self.airlineIndex:
            self.airlineIndex[flight.airlineID].discard(flightID)
            if not self.airlineIndex[flight.airlineID]:
                del self.airlineIndex[flight.airlineID]
        if flightID in self.handles:
            node = self.handles.pop(flightID)
            try:
                self.pendingFlights.erase(node)
            except:
                pass

    def Initialize(self, runwayCount):
        if runwayCount <= 0:
            self._write("Invalid input. Please provide a valid number of runways.")
            return
        self.currentTime = 0
        self.nextRunwayID = runwayCount + 1
        self._write(f"{runwayCount} Runways are now available")

    def SubmitFlight(self, flightID, airlineID, submitTime, priority, duration):
        self._advanceTime(submitTime)

        if flightID in self.activeFlights:
            self._write("Duplicate FlightID")
            return

        flight = Flight(flightID, airlineID, submitTime, priority, duration)
        self.activeFlights[flightID] = flight
        self.airlineIndex[airlineID].add(flightID)

        key = (priority, -submitTime, -flightID)
        node = self.pendingFlights.push(key, flightID)
        self.handles[flightID] = node

        changed = self._rescheduleUnsatisfied()
        self._write(f"Flight {flightID} scheduled - ETA: {flight.ETA}")
        self._printChangedEtas(changed)

    def CancelFlight(self, flightID, currentTime):
        self._advanceTime(currentTime)
        flight = self.activeFlights.get(flightID)

        if not flight:
            self._write(f"Flight {flightID} does not exist")
            return
        if flight.state in ("INPROGRESS", "LANDED"):
            self._write(f"Cannot cancel. Flight {flightID} has already departed")
            return

        self._removeFlightFromSystemIndices(flightID)
        self.activeFlights.pop(flightID, None)
        self._write(f"Flight {flightID} has been canceled")

        changed = self._rescheduleUnsatisfied()
        self._printChangedEtas(changed)

    def Reprioritize(self, flightID, currentTime, newPriority):
        self._advanceTime(currentTime)
        flight = self.activeFlights.get(flightID)

        if not flight:
            self._write(f"Flight {flightID} not found")
            return
        if flight.state in ("INPROGRESS", "LANDED"):
            self._write(f"Cannot reprioritize. Flight {flightID} has already departed")
            return

        old_prio = flight.priority
        flight.priority = newPriority

        if flight.state == "PENDING" and flightID in self.handles:
            node = self.handles[flightID]
            new_key = (newPriority, -flight.submitTime, -flightID)
            self.pendingFlights.updateKey(node, new_key)

        self._write(f"Priority of Flight {flightID} has been updated to {newPriority}")
        changed = self._rescheduleUnsatisfied()
        self._printChangedEtas(changed)

    def AddRunways(self, count, currentTime):
        self._advanceTime(currentTime)
        if count <= 0:
            self._write("Invalid input. Please provide a valid number of runways.")
            return

        self.nextRunwayID += count
        self._write(f"Additional {count} Runways are now available")

        changed = self._rescheduleUnsatisfied()
        self._printChangedEtas(changed)

    def GroundHold(self, airlineLow, airlineHigh, currentTime):
        self._advanceTime(currentTime)
        if airlineHigh < airlineLow:
            self._write("Invalid input. Please provide a valid airline range.")
            return

        to_remove = []
        for aid in range(airlineLow, airlineHigh + 1):
            if aid in self.airlineIndex:
                for fid in list(self.airlineIndex[aid]):
                    flight = self.activeFlights.get(fid)
                    if flight and flight.state in ("PENDING", "SCHEDULED"):
                        to_remove.append(flight)

        for flight in to_remove:
            self._removeFlightFromSystemIndices(flight.flightID)
            self.activeFlights.pop(flight.flightID, None)

        self._write(f"Flights of the airlines in the range [{airlineLow}, {airlineHigh}] have been grounded")
        changed = self._rescheduleUnsatisfied()
        self._printChangedEtas(changed)

    def PrintActive(self):
        if not self.activeFlights:
            self._write("No active flights")
            return

        flights = sorted(self.activeFlights.values(), key=lambda f: f.flightID)
        for f in flights:
            rwy = f.runwayID if f.state != "PENDING" else -1
            st = f.startTime if f.state != "PENDING" else -1
            eta = f.ETA if f.state != "PENDING" else -1
            self._write(f"[flight{f.flightID}, airline{f.airlineID}, "
                        f"runway{rwy}, start{st}, ETA{eta}]")

    def PrintSchedule(self, t1, t2):
        matches = []
        for flight in self.activeFlights.values():
            if (flight.state == "SCHEDULED" and
                flight.startTime > self.currentTime and
                t1 <= flight.ETA <= t2):
                matches.append(flight)

        matches.sort(key=lambda f: (f.ETA, f.flightID))

        if not matches:
            self._write("There are no flights in that time period")
            return
        for f in matches:
            self._write(f"[{f.flightID}]")

    def Tick(self, t):
        self._advanceTime(t)

    def Quit(self):
        self._write("Program Terminated!!")
        self.outputFile.close()
        sys.exit(0)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 gatorAirTrafficScheduler.py <input_file_name>")
        sys.exit(1)

    input_file = sys.argv[1]
    base = os.path.splitext(input_file)[0]
    output_file = f"{base}_output_file.txt"

    try:
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            scheduler = GatorAirTrafficScheduler(outfile)

            for raw_line in infile:
                line = raw_line.strip()
                if not line:
                    continue

                try:
                    cmd, rest = line.split("(", 1)
                    param_str = rest.strip()[:-1]
                    params = [int(p.strip()) for p in param_str.split(",")] if param_str else []

                    if cmd == "Initialize":
                        scheduler.Initialize(*params)
                    elif cmd == "SubmitFlight":
                        scheduler.SubmitFlight(*params)
                    elif cmd == "CancelFlight":
                        scheduler.CancelFlight(*params)
                    elif cmd == "Reprioritize":
                        scheduler.Reprioritize(*params)
                    elif cmd == "AddRunways":
                        scheduler.AddRunways(*params)
                    elif cmd == "GroundHold":
                        scheduler.GroundHold(*params)
                    elif cmd == "PrintActive":
                        scheduler.PrintActive()
                    elif cmd == "PrintSchedule":
                        scheduler.PrintSchedule(*params)
                    elif cmd == "Tick":
                        scheduler.Tick(*params)
                    elif cmd == "Quit":
                        scheduler.Quit()
                        break
                    else:
                        outfile.write(f"Unknown command: {cmd}\n")

                except Exception as e:
                    outfile.write(f"Error processing line '{line}': {e}\n")

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()