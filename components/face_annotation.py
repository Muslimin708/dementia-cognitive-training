import base64
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components


# This file is located at:
# project/components/face_annotation.py
COMPONENT_DIRECTORY = Path(__file__).resolve().parent
FRONTEND_DIRECTORY = COMPONENT_DIRECTORY / "frontend"
INDEX_FILE = FRONTEND_DIRECTORY / "index.html"


# Register the bidirectional Streamlit component.
# The frontend directory must contain index.html.
_face_annotation_component = components.declare_component(
    "face_annotation",
    path=str(FRONTEND_DIRECTORY),
)


def _uploaded_file_to_data_url(uploaded_file: Any) -> str:
    """Convert a Streamlit UploadedFile into a browser-readable data URL."""
    if uploaded_file is None:
        raise ValueError("An image file is required.")

    file_bytes = uploaded_file.getvalue()
    if not file_bytes:
        raise ValueError("The uploaded image is empty.")

    mime_type = getattr(uploaded_file, "type", None) or "image/png"
    encoded_image = base64.b64encode(file_bytes).decode("utf-8")

    return f"data:{mime_type};base64,{encoded_image}"


def render(
    uploaded_file: Any,
    key: str = "face_annotation_component",
    height: int = 700,
) -> Any:
    """
    Render the Step 1 bidirectional test component.

    Step 1 only verifies that:
    1. Python can send the uploaded image to the HTML frontend.
    2. The HTML frontend can return a test value to Python.

    Drawing and face annotations will be added only after this test passes.
    """
    if uploaded_file is None:
        return None

    if not FRONTEND_DIRECTORY.exists():
        st.error(
            "The component frontend folder is missing. Create: "
            f"{FRONTEND_DIRECTORY}"
        )
        return None

    if not INDEX_FILE.exists():
        st.error(
            "The component frontend file is missing. Create: "
            f"{INDEX_FILE}"
        )
        return None

    try:
        image_data = _uploaded_file_to_data_url(uploaded_file)
    except ValueError as error:
        st.error(str(error))
        return None

    component_value = _face_annotation_component(
        image_data=image_data,
        default=None,
        key=key,
        height=height,
    )

    return component_value