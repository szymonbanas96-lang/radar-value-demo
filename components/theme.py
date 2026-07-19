from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

def load_theme() -> None:
    css_path = ROOT / "assets" / "style.css"
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )
