# Vector evaluation board

The user requests that the entire simulated board become an accurate SVG of
the supplied ALS-SDA-ARMCTXM3-01 board. Replace the photograph with a top-down,
hand-drawn vector replica based on the clearer, uncabled supplied JPEG.

Keep the physical arrangement: UART and Ethernet at left; LCD above the
metal MCU module; seven-segment display above the keypad; power, relay,
motor and USB sections at right; LEDs and serial interfaces along the bottom.
Draw component bodies, sockets, pins, switches, silkscreen and passive parts.
Small components and traces are illustrative where the photographs cannot
establish exact geometry. Do not imply new peripheral emulation.

The requested SVG rules out retaining a raster background. Auto-tracing the
photograph would retain perspective, occlusion and unreadable labels, so use
native SVG geometry with reusable React drawing primitives instead.

Preserve real firmware-driven displays and manual wiring. Match the layout
coordinates and connector orientations to the new artwork. Keep keyboard,
pointer, focus, cable disconnection, jumper and potentiometer behavior.
The existing electrical mapping remains authoritative and unchanged.

Use React and SVG with no new dependencies or remote assets. Supply a
standalone SVG snapshot alongside the interactive rendering. Verify the
absence of raster dependencies, physical section placement, real firmware
outputs, input release, wiring, jumper behavior, zoom and narrow viewports.
