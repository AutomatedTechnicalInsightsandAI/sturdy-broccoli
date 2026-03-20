"""
app.py — Entry-point for the Sturdy Broccoli enterprise SEO content factory.

Run with:
    python app.py
or:
    streamlit run app.py

The server will start on port 8080 (Cloud Shell / Docker compatible).
"""
import sys
import os
import pathlib
import subprocess

_gui = pathlib.Path(__file__).with_name("gui_wrapper.py")


def _in_streamlit_context() -> bool:
    """Return True when this module is being executed inside a Streamlit runner."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except (ImportError, AttributeError):
        return False


if __name__ == "__main__":
    if _in_streamlit_context():
        # Already running inside `streamlit run app.py` — delegate to gui module.
        import runpy as _runpy
        _runpy.run_path(str(_gui), run_name="__main__")
    else:
        # Invoked as `python app.py` — spawn a proper Streamlit HTTP server.
        port = os.environ.get("PORT", "8080")
        cmd = [
            sys.executable, "-m", "streamlit", "run", str(_gui),
            f"--server.port={port}",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
        ]
        sys.exit(subprocess.run(cmd).returncode)
