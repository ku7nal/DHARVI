# 02 — Dynamic Flood and Debris Avoidance

**What to build:** Let responders activate detected water hazards and draw temporary debris or blockage zones; recalculate an alternate evacuation route whenever the hazard state changes.

**Blocked by:** 01 — Emergency Route Mode with Road-Network Routing

**Status:** ready-for-agent

- [x] Water-mask cells are treated as impassable or high-risk during route generation.
- [x] Users can add, inspect, and remove temporary debris/blockage zones on the reconstruction.
- [x] The route recalculates after each hazard change and displays the updated path.
- [x] The interface explains which hazard caused the original route to change.
- [x] Tests cover flooded roads, manually blocked roads, cleared hazards, and no-alternate-route outcomes.
