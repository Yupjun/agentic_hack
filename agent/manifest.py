"""Tool manifest: name, description, HTTP binding, JSON schema. One place, data not code
(Rule of Representation). The loop and the prompt are both generated from this."""
TOOLS = [
    {"name": "nas_status", "method": "GET", "path": "/nas",
     "description": "FAA NAS status for an airport: closures, ground stops, ground delay programs (GDP) with average/max delay, departure/arrival delays. Live public feed; entries marked synthetic are scenario injections.",
     "parameters": {"type": "object", "properties": {"airport": {"type": "string", "description": "FAA id e.g. JFK or ICAO KJFK"}}, "required": ["airport"]}},
    {"name": "wx", "method": "GET", "path": "/wx",
     "description": "Aviation weather for an ICAO station: METAR (flight category, wind, visibility), TAF, SIGMET/AIRMET near it, 24h surface wind/precip/visibility forecast.",
     "parameters": {"type": "object", "properties": {"icao": {"type": "string"}}, "required": ["icao"]}},
    {"name": "flight_status", "method": "GET", "path": "/flight",
     "description": "Live aircraft position by ICAO callsign from public ADS-B feeds (404 = not airborne/seen now).",
     "parameters": {"type": "object", "properties": {"callsign": {"type": "string"}}, "required": ["callsign"]}},
    {"name": "hazards", "method": "GET", "path": "/hazards",
     "description": "GDACS natural hazard events (EQ, TC, FL, VO, DR, WF) of the last N days, optional bbox minLon,minLat,maxLon,maxLat.",
     "parameters": {"type": "object", "properties": {"days": {"type": "integer"}, "bbox": {"type": "string"}}, "required": []}},
    {"name": "schedule", "method": "GET", "path": "/schedule",
     "description": "Transport options from origin (dest optional: omit it to see EVERY leg departing origin, including truck feeders to neighbouring hubs) with remaining capacity_kg, depart/arrive ISO, rate_per_kg_usd. Capacity is synthetic scenario data. Modes: air, truck, ocean. Omit mode to list ALL modes; truck feeder legs to a neighbouring hub (then air) are part of the option set.",
     "parameters": {"type": "object", "properties": {"origin": {"type": "string"}, "dest": {"type": "string"}, "mode": {"type": "string"}, "not_before": {"type": "string"}}, "required": ["origin"]}},
    {"name": "cost", "method": "POST", "path": "/cost",
     "description": "Cost and timing of a candidate plan: legs[{option_id, chargeable_kg}] (times and rate are taken from the schedule by option_id; never restate them), awb_count, cutoff, final_dest, total_kg -> feasible, capacity_violations, delivered_kg_to_final_dest vs required_kg, stranded_kg_by_node (cargo left at an intermediate hub) (planned kg over an option's capacity), total_usd, final_arrival, meets_cutoff, slack_hours. Pass option_id on every leg so capacity is checked.",
     "parameters": {"type": "object", "properties": {"awb_count": {"type": "integer"}, "cutoff": {"type": "string"}, "legs": {"type": "array", "items": {"type": "object"}}}, "required": ["awb_count", "cutoff", "legs"]}},
    {"name": "allocate", "method": "POST", "path": "/allocate",
     "description": "Pack whole AWBs into ROUTES by capacity (first-fit decreasing). A route is a chain of option ids, e.g. [\"TRK-JFK-EWR\",\"UAL16-0929\"] (truck feeder then flight) or [\"KAL251-0929\"]; capacity = bottleneck hop; an AWB rides every hop of its route so flow is conserved. Input: awbs[{awb, chargeable_kg}], routes[[option_id,...],...] in preferred order, already_loaded_kg{option_id: kg} from earlier groups. Returns plan_legs (paste into cost / PLAN_JSON), routes summary, assignment, unplaced. Use this instead of packing arithmetic.",
     "parameters": {"type": "object", "properties": {"awbs": {"type": "array", "items": {"type": "object"}}, "routes": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}, "already_loaded_kg": {"type": "object"}}, "required": ["awbs", "routes"]}},
    {"name": "vessel", "method": "GET", "path": "/vessel",
     "description": "Live ship position by 9-digit MMSI via AIS (needs AISSTREAM_API_KEY; 503 if unset).",
     "parameters": {"type": "object", "properties": {"mmsi": {"type": "string"}}, "required": ["mmsi"]}},
    {"name": "notam", "method": "GET", "path": "/notam",
     "description": "NOTAMs for an ICAO location via FAA NOTAM API (needs FAA API credentials; 503 if unset).",
     "parameters": {"type": "object", "properties": {"icao": {"type": "string"}}, "required": ["icao"]}},
]

BY_NAME = {t["name"]: t for t in TOOLS}
