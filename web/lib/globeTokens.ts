// deck.gl palette as RGB tuples — the same values as app/globals.css (the palette's source of truth).
// No hex here: the design guard allows hex only in globals.css.
export type RGB = [number, number, number];
export const G = {
  ocean: [255, 255, 255] as RGB,      // sheet: the globe is paper too
  land: [233, 233, 229] as RGB,
  border: [198, 198, 193] as RGB,
  graticule: [228, 228, 224] as RGB,
  ink: [23, 23, 21] as RGB,
  muted: [107, 106, 101] as RGB,
  line: [222, 222, 218] as RGB,
  night: [23, 23, 21] as RGB,
  tomato: [214, 64, 43] as RGB,       // late / due passed
  green: [31, 129, 89] as RGB,        // delivered
};
// Mode colours carry meaning (categorical, fixed order; same as components/Timeline.tsx).
export const MODE_RGB: Record<string, RGB> = {
  air: [27, 62, 194],        // cobalt
  ocean: [125, 60, 100],     // plum
  parcel: [168, 123, 18],    // mustard
  truck: [139, 137, 133],    // graphite
  rail: [31, 129, 89],       // green
};
