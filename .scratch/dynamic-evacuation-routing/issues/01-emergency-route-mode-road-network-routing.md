# 01 — Emergency Route Mode with Road-Network Routing

**What to build:** Let responders select an evacuation origin and destination on a reconstruction and view a shortest viable route generated from the semantic road mask.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [x] Route requests accept two scene points, validate that they are usable road locations, and return a deterministic route or a clear failure reason.
- [x] The route is rendered clearly over the reconstruction with start and destination markers.
- [x] A deterministic fixture demonstrates the feature without requiring model inference.
- [x] Backend and frontend tests cover valid routes, invalid points, and disconnected road networks.
