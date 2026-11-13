"""Web interface for the cell edge analysis individual scripts (FastAPI + plain ES-module front end).

- app.py       FastAPI app: front end, JSON API under /api, STATIC_ENDPOINTS for the static GitHub Pages export
- analysis.py  runs the repo's step 1/2/5/6/7 functions (with the normalisation + statistic options) on in-memory stacks
- fluor.py     runs fluorescence_edge_experiments (detector.fluor_edge, edge_methods.METHODS) on in-memory stacks
- guide.py     the GUI's Help -> Analysis Guide text (gui_help_content) for the Guide page
- tiff_io.py   reads uploaded TIFF stacks with tifffile (incl. compressed files) and their pixel size
- static/      front end; edge_engine.js, intensity_engine.js, fluor_engine.js (+ contours.js, tiff.js) are JS ports
               tested against Python (*.test.mjs, fixture from scripts/make_web_fixture.py)
"""
