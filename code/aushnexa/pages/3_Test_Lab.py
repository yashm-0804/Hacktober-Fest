"""Safety Test Lab: runs the 4 preset safety cases on real brand data (FE-5)."""
import pandas as pd
import streamlit as st

from core.testlab import run_cases

st.set_page_config(page_title="Safety Test Lab", page_icon="🧪", layout="wide")
st.title("Safety Test Lab")
st.caption("Four preset regimens built from real Indian brands, run through the deterministic safety checks.")

if st.button("Run the 4 cases", type="primary"):
    with st.spinner("Running cases…"):
        st.session_state["testlab_results"] = run_cases()

results = st.session_state.get("testlab_results")
if results:
    passed = sum(r["passed"] for r in results)
    msg = f"{passed}/{len(results)} passed"
    (st.success if passed == len(results) else st.error)(msg)
    df = pd.DataFrame([{"Result": "✅ PASS" if r["passed"] else "❌ FAIL", "Case": r["case"],
                        "Expected": r["expected"], "Got": r["got"]} for r in results])
    st.dataframe(df, hide_index=True, width="stretch")
else:
    st.info("Press the button to run the cases.")
