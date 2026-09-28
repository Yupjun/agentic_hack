"use client";
// deck.gl needs the browser (WebGL): load the globe on the client only.
import dynamic from "next/dynamic";
const RouteGlobe = dynamic(() => import("./RouteGlobe"), { ssr: false, loading: () => <div className="sheet h-[560px] p-5 text-body text-muted">loading globe…</div> });
export default RouteGlobe;
