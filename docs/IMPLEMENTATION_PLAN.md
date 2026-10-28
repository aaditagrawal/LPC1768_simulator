# LPC1768 local lab implementation

The supplied master prompt is the specification and authorizes implementation,
including the emulator spike and backend selection. No existing source or git
repository was supplied. Work stays in the named workspace.

1. Inspect installed Keil and manuals; execute genuinely compiled Cortex-M3 code
   with observable GPIO writes before creating the main UI.
2. Record backend evidence and manual mapping ambiguities in an ADR.
3. Test real firmware through a small memory-mapped LPC1768 subset and a fixed
   ten-wire board graph: LEDs, switch, seven-segment, LCD, matrix, ADC, PWM.
4. Add a localhost API, bounded execution worker, C/HEX validation and controls.
5. Build the photo-overlay React/TypeScript UI with manual cables and jumpers,
   optional guide, source editor, uploads and compiler/runtime messages.
6. Run firmware integration, API, frontend build and browser tests; document
   exact lab coverage and limitations. Provide a Windows launcher.

Verification focus: malformed HEX, byte/halfword GPIO access and masking,
incorrect/disconnected wires, pin multiplexing, failed compilation replacing
firmware, pause/reset state, missed LCD/segment transitions, ADC gating, and
interrupt handler execution rather than fabricated display results.

Tests use Keil-generated Intel HEX with genuine startup and SystemInit. They
assert peripheral behavior after CPU execution, including negative wiring cases.
No CPU instruction decoder or source-text interpretation will be implemented.
