import base64
from pathlib import Path
import streamlit.components.v1 as components


def render(uploaded_file):

    html_template = Path(
        "components/annotation.html"
    ).read_text(
        encoding="utf-8"
    )

    image_base64 = base64.b64encode(
        uploaded_file.getvalue()
    ).decode()

    html_code = html_template.replace(
        "__IMAGE__",
        f"data:{uploaded_file.type};base64,{image_base64}"
    )

    components.html(
        html_code,
        height=800,
        scrolling=True
    )

    return []