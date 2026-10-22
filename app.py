"""Rice yield forecasting dashboard; app.py is the sole application entry point."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
if __name__ == "__main__":
    if "--compare-crop-state-models" in sys.argv:
        from src.rice_crop_state_model import run
        print(run())
        raise SystemExit(0)
    if "--prepare-crop-state-export" in sys.argv:
        from src.rice_crop_state import prepare_export
        print(prepare_export())
        raise SystemExit(0)
    if "--check-crop-state-import" in sys.argv:
        from src.rice_crop_state import check_import
        try:
            print(check_import())
        except ValueError as error:
            print(f"Crop-state import stopped: {error}")
            raise SystemExit(1)
        raise SystemExit(0)
    if "--compare-annual-models" in sys.argv:
        from src.rice_annual_comparison import run
        print(run())
        raise SystemExit(0)
    if "--compare-models" in sys.argv:
        from src.rice_validation import run
        report = run()
        print(report)
        raise SystemExit(0)
    if "--audit-data" in sys.argv:
        from src.rice_foundation import build
        report = build()
        print(report["stage"])
        print(PROJECT_ROOT / "data/processed/rice/foundation/audit.json")
        raise SystemExit(0)
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx(suppress_warning=True) is None:
        from streamlit.web import cli
        cli.main(args=["run", str(PROJECT_ROOT / "app.py"), "--server.fileWatcherType=none", *sys.argv[1:]])
        raise SystemExit(0)

import streamlit as st

st.set_page_config(page_title="Rice Yield Outlook", layout="wide", initial_sidebar_state="expanded")
st.markdown("<style>" + (PROJECT_ROOT / "src/dashboard.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)
from src.rice_dashboard import render_dashboard

render_dashboard()
