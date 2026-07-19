from pathlib import Path
import base64
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

def _image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

def render_header() -> None:
    icon_path = ROOT / "assets" / "favicon.png"
    icon_uri = _image_data_uri(icon_path) if icon_path.exists() else ""

    st.markdown(
        f"""
        <div class="rv-header">
            <div class="rv-brand">
                <img class="rv-brand-icon" src="{icon_uri}" alt="Radar Value logo">
                <div>
                    <div class="rv-brand-title">RADAR VALUE</div>
                    <div class="rv-brand-subtitle">NBA market intelligence platform</div>
                </div>
            </div>
            <div class="rv-live">
                <span class="rv-live-dot"></span>
                ALPHA v0.2
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_section(kicker: str, title: str) -> None:
    st.markdown(
        f"""
        <div class="rv-section">
            <div class="rv-section-kicker">{kicker}</div>
            <div class="rv-section-title">{title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
