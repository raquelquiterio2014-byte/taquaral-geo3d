from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
MAIN_PATH = BASE_DIR / "main.py"
SURFACE_PATH = BASE_DIR / "outputs" / "taquaral_surface_3d.html"

MARKER = "# TAQUARAL_3D_DASHBOARD_INTEGRATION"


NAVIGATION = '''
        <style>
            [hidden] {
                display: none !important;
            }

            .dashboard-navigation {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                padding: 18px 20px 0;
            }

            .dashboard-navigation button {
                width: auto;
                min-width: 180px;
                margin: 0;
                background: #304b5c;
                color: #edf5fa;
            }

            .dashboard-navigation button[aria-pressed="true"] {
                background: #5de0be;
                color: #10202b;
            }

            #surface-view {
                padding: 20px;
            }

            .surface-panel {
                padding: 20px;
                background: #192f3d;
                border: 1px solid #304b5c;
                border-radius: 12px;
            }

            .surface-panel h2 {
                margin-top: 0;
            }

            .surface-panel a {
                color: #66e5c4;
            }

            #surface-frame {
                display: block;
                width: 100%;
                height: 78vh;
                min-height: 500px;
                border: 0;
                border-radius: 8px;
                background: #10202b;
            }
        </style>

        <nav class="dashboard-navigation" aria-label="Dashboard views">
            <button id="show-map" type="button"
                    aria-controls="map-view" aria-pressed="true">
                Map &amp; Measurements
            </button>

            <button id="show-surface" type="button"
                    aria-controls="surface-view" aria-pressed="false">
                3D Surface
            </button>
        </nav>
'''


SURFACE_SECTION = '''
        <section id="surface-view" hidden aria-label="3D surface viewer">
            <div class="surface-panel">
                <h2>3D Surface Exploration</h2>

                <p class="note">
                    Rotate by dragging. Scroll to zoom.
                    Hover over the surface to inspect modeled elevations.
                </p>

                <p class="note">
                    Copernicus GLO-30 · Approximately 30 m sampling.
                    Surface model, not bathymetry.
                    Vertical reference: EGM2008.
                    No vertical exaggeration.
                </p>

                <p class="note">
                    <a href="/surface-3d" target="_blank"
                       rel="noopener noreferrer">
                        Open the 3D viewer in a separate tab
                    </a>
                </p>

                <iframe
                    id="surface-frame"
                    title="Taquaral interactive 3D surface"
                    data-source="/surface-3d">
                </iframe>
            </div>
        </section>
'''


NAVIGATION_SCRIPT = '''
        <script>
            (function () {
                const mapView = document.getElementById("map-view");
                const surfaceView = document.getElementById("surface-view");
                const mapButton = document.getElementById("show-map");
                const surfaceButton = document.getElementById("show-surface");
                const frame = document.getElementById("surface-frame");

                mapButton.addEventListener("click", function () {
                    mapView.hidden = false;
                    surfaceView.hidden = true;

                    mapButton.setAttribute("aria-pressed", "true");
                    surfaceButton.setAttribute("aria-pressed", "false");

                    // Let Leaflet recalculate its size after becoming visible.
                    requestAnimationFrame(function () {
                        window.dispatchEvent(new Event("resize"));
                    });
                });

                surfaceButton.addEventListener("click", function () {
                    mapView.hidden = true;
                    surfaceView.hidden = false;

                    mapButton.setAttribute("aria-pressed", "false");
                    surfaceButton.setAttribute("aria-pressed", "true");

                    // Load the 3D viewer only when first requested.
                    if (!frame.hasAttribute("src")) {
                        frame.src = frame.dataset.source;
                    }
                });
            })();
        </script>
'''


SURFACE_ROUTE = '''

# TAQUARAL_3D_DASHBOARD_INTEGRATION
@app.get("/surface-3d", include_in_schema=False)
def surface_3d_viewer():
    from fastapi.responses import FileResponse

    surface_path = (
        Path(__file__).resolve().parent
        / "outputs"
        / "taquaral_surface_3d.html"
    )

    if not surface_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="3D viewer not found. Run build_surface_3d.py first.",
        )

    return FileResponse(
        path=surface_path,
        media_type="text/html",
        headers={"Cache-Control": "no-cache"},
    )
'''


def main():
    if not MAIN_PATH.is_file():
        raise FileNotFoundError(
            "main.py was not found. Save this script in the project folder."
        )

    if not SURFACE_PATH.is_file():
        raise FileNotFoundError(
            "The 3D HTML was not found. Run build_surface_3d.py first."
        )

    source = MAIN_PATH.read_text(encoding="utf-8-sig")

    if MARKER in source:
        print("The 3D dashboard integration is already installed.")
        return

    # Stop without changing the file if its layout differs from expectations.
    for anchor in ("</header>", "<main>", "</main>", "</body>"):
        if source.count(anchor) != 1:
            raise ValueError(
                f"Expected exactly one {anchor} in main.py. "
                "No changes were made."
            )

    if '"/surface-3d"' in source:
        raise ValueError(
            "A /surface-3d route may already exist. No changes were made."
        )

    updated = source.replace(
        "</header>",
        "</header>" + NAVIGATION,
        1,
    )

    updated = updated.replace(
        "<main>",
        '<main id="map-view">',
        1,
    )

    updated = updated.replace(
        "</main>",
        "</main>" + SURFACE_SECTION,
        1,
    )

    updated = updated.replace(
        "</body>",
        NAVIGATION_SCRIPT + "</body>",
        1,
    )

    updated = updated.replace(
        "3D terrain is not yet included.",
        "3D surface exploration is available in the 3D Surface tab.",
    )

    updated += SURFACE_ROUTE

    # Check Python syntax before saving any changes.
    compile(updated, str(MAIN_PATH), "exec")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = BASE_DIR / f"main_backup_{timestamp}.py"

    backup_path.write_text(source, encoding="utf-8")
    MAIN_PATH.write_text(updated, encoding="utf-8")

    print("Dashboard integration complete.")
    print(f"Backup saved to: {backup_path}")
    print("Start the server with:")
    print("python -m uvicorn main:app --reload")
    print("Then open http://127.0.0.1:8000")


if __name__ == "__main__":
    main()