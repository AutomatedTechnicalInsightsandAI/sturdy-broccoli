"""
app.py — Entry-point alias for the Sturdy Broccoli enterprise SEO content factory.

Running ``streamlit run app.py`` is equivalent to
``streamlit run gui_wrapper.py``.
"""
import runpy as _runpy
import os as _os
import pathlib as _pathlib

_gui = _pathlib.Path(__file__).with_name("gui_wrapper.py")
_runpy.run_path(str(_gui), run_name="__main__")
