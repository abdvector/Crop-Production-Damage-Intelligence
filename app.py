"""Rice yield forecasting dashboard; app.py is the sole application entry point."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)
if __name__ == "__main__":
    from streamlit.runtime.scriptrunner import get_script_run_ctx
    if get_script_run_ctx(suppress_warning=True) is None:
        from streamlit.web import cli
        cli.main(args=["run", str(PROJECT_ROOT / "app.py"), "--server.fileWatcherType=none", *sys.argv[1:]])
        raise SystemExit(0)

import streamlit as st

st.set_page_config(page_title="Rice Yield Outlook", layout="wide")
st.markdown("""<style>
.block-container {max-width:1350px;padding-top:2.5rem;}
[data-testid="stMetric"] {background:#111C2E;border:1px solid #26364C;border-radius:10px;padding:18px;}
[data-testid="stMetricLabel"] {color:#A9B8CA;}
h1 {letter-spacing:-0.03em;}
</style>""", unsafe_allow_html=True)
st.title("Rice Yield Outlook")
st.caption("Birla Institute of Technology, Mesra | Department of Quantitative Economics and Data Science | Guide: Dr. Manish Kumar Pandey")
with st.sidebar:
    st.header("Rice forecasting")
    view = st.radio("Workspace", ["Regional yield forecast", "Odisha Kharif study", "Molecular data audit", "Earlier research"])
    st.divider()
    st.write("Rice yield per hectare")
    st.caption("Historical annual and Kharif studies with later-year evaluation, source checks and explicit limitations.")
    st.caption("Earlier field, genetics and aluminium studies remain available as supporting research.")
if view == "Regional yield forecast":
    from src.rice_regional_ui import render_regional
    render_regional()
elif view == "Molecular data audit":
    from src.rice_molecular_ui import render_molecular_audit
    render_molecular_audit()
elif view == "Odisha Kharif study":
    from src.rice_odisha_ui import render_odisha
    render_odisha()
else:
    from src.rice_research_archive import render_research_archive
    render_research_archive()
