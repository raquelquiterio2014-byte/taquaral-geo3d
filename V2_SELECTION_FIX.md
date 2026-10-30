# V2 selection fix — explicit A/B steps

## Problem and evidence

The original 3D handler posted every `plotly_click` event while the parent selection was active. Replaying two identical notifications before the parent acknowledgement sent two points, producing an unintended zero-distance A–B pair. A regression test failed with two outgoing picks instead of one before this fix.

The exact reason for duplicate notifications in the author's browser has not been established. This fix handles repeated events without relying on a timing-based debounce.

## Behavior

- **Select point A** starts a new selection; the first pick is locked synchronously before sending to the parent.
- After acknowledgement of A, **Select point B** must be pressed before the 3D surface accepts B.
- B at the same coordinate as A is rejected in this 3D flow, with instructions to choose a different surface location.
- Delayed unchanged state messages do not unlock pending picks.
- Clear/reset and shared selections originating on the 2D map remain supported.
- Controls remain visible while scrolling. A versioned script URL avoids reuse of the older cached script.

## Install in an existing V2 project

Stop Uvicorn, back up the two files and replace only:

- `assets/connected_exploration.html`
- `assets/connected_exploration.js`

Keep `main.py`, the Python modules, data files and the virtual environment. No additional dependency is needed. Restart Uvicorn and refresh the dashboard with Ctrl+F5.

1. Open V2 and select **Select point A**.
2. Click once on the surface; wait for the A-selected instruction.
3. Press **Select point B**, then click another surface location.
4. Verify nonzero distance and a multi-sample profile, then inspect the same points in Map & Measurements.

## Verification

`node --test tests/v2-selection.test.cjs`: six passing event-flow regression tests executing the actual V2 client script in a DOM/Plotly stub harness. Tests cover repeated events, explicit B arming, identical-coordinate rejection, stale state, clear/restart and map-origin selections. JavaScript syntax check passed.

This does not replace visual WebGL/browser verification on Windows, which remains pending. No geographic algorithms or source data were changed.
