"""Sole launcher: python app.py, or python app.py --train."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

if __name__ == "__main__":
    if "--train" in sys.argv:
        from src.model import build
        import json
        print(json.dumps(build(), indent=2))
        raise SystemExit(0)
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx(suppress_warning=True) is None:
        from streamlit.web import cli
        cli.main(args=["run", str(ROOT / "app.py"), "--server.fileWatcherType=none", *sys.argv[1:]])
        raise SystemExit(0)

import streamlit as st
from src.interface import render

st.set_page_config(page_title="Rice Yield", layout="wide", initial_sidebar_state="expanded")
st.markdown("<style>"+(ROOT / "src/dashboard.css").read_text(encoding="utf-8")+"</style>", unsafe_allow_html=True)
render()
