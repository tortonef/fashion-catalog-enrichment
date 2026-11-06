"""Streamlit UI: sample gallery -> zero-shot tagging -> human review -> export."""

from __future__ import annotations

import io
import json
from pathlib import Path

import streamlit as st
from PIL import Image

from catalog_enrichment.config import ROOT, load_config
from catalog_enrichment.export import from_frame, to_csv, to_frame, to_json, to_record, validate
from catalog_enrichment.factory import build_tagger
from catalog_enrichment.metrics import ops_metrics
from catalog_enrichment.tagger import ItemResult, list_images

st.set_page_config(page_title="Catalog Enrichment", page_icon=":material/sell:", layout="wide")
cfg = load_config()
schema = json.loads(cfg["paths"]["schema"].read_text(encoding="utf-8"))


@st.cache_resource(show_spinner="Loading FashionCLIP from the local cache...")
def get_tagger():
    return build_tagger(cfg)


def rel(path: Path) -> str:
    """Path relative to the repo when possible, with forward slashes (as stored in records)."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


# ---------- Sidebar: inputs ----------
with st.sidebar:
    st.header("Images")
    folder_text = st.text_input(
        "Image folder (batch mode)", value=rel(cfg["paths"]["images"]),
        help="Every JPG/PNG/WEBP in this folder is tagged. Relative paths start from the repo.",
    )  # fmt: skip
    uploads = st.file_uploader(
        "Or add your own photos", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True
    )
    st.header("Review")
    threshold = st.slider(
        "Review threshold", 0.05, 0.95, float(cfg["review_threshold"]), 0.05,
        help="Attributes whose confidence is below this value are flagged 'needs review'.",
    )  # fmt: skip
    st.caption("Runs 100% locally on CPU. No data leaves this machine.")

folder = Path(folder_text)
folder = folder if folder.is_absolute() else ROOT / folder

# Each source: unique name -> (image path stored in the record, loader)
sources: dict[str, tuple[str, object]] = {p.name: (rel(p), p) for p in list_images(folder)}
for up in uploads or []:
    sources[f"upload: {up.name}"] = (up.name, up.getvalue())


def open_image(src: object) -> Image.Image:
    return Image.open(src if isinstance(src, Path) else io.BytesIO(src))


# ---------- Header ----------
st.title("Catalog Enrichment")
st.markdown(
    "Turn product photos into **catalog-ready attributes** with confidence scores. "
    "Low-confidence attributes are flagged for a human to check before export."
)

if not sources:
    st.info(
        f"No images found in `{folder_text}`. Add photos to that folder or upload some in the sidebar."
    )
    st.stop()

try:
    tagger = get_tagger()
except RuntimeError as e:
    st.error(
        f"{e}\n\nWindows: `powershell -ExecutionPolicy Bypass -File .\\setup.ps1` · macOS/Linux: `bash setup.sh`"
    )
    st.stop()

# ---------- Tagging (cached per image in the session) ----------
results: dict[str, ItemResult] = st.session_state.setdefault("results", {})
todo = [n for n in sources if n not in results]
if todo:
    bar = st.progress(0.0, text="Tagging images...")
    for i, name in enumerate(todo, 1):
        with open_image(sources[name][1]) as im:
            results[name] = tagger.tag(im, name)
        bar.progress(i / len(todo), text=f"Tagged {i}/{len(todo)}: {name}")
    bar.empty()

items = [results[n] for n in sources]
for it in items:  # the threshold is a review policy: apply it without re-running the model
    for a in it.attributes.values():
        a.needs_review = a.confidence < threshold

# ---------- Ops metrics ----------
m = ops_metrics(items)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Items", len(items))
c2.metric(
    "Auto-filled",
    f"{m['auto_filled_pct']:.0f}%",
    help="Confidence at or above the threshold",
)
c3.metric("Need review", f"{m['flagged_items_pct']:.0f}%")
c4.metric("Sec / image", f"{m['avg_seconds']:.2f} s", help="Measured on this machine, CPU only")

# key keeps the active tab when a table edit triggers a rerun
review_tab, table_tab = st.tabs(["Review an item", "Catalog table & export"], key="view")

# ---------- Review one item ----------
with review_tab:
    name = st.selectbox(
        "Item", list(sources),
        format_func=lambda n: f"{'⚠ ' if results[n].needs_review else '✓ '}{n}",
    )  # fmt: skip
    item = results[name]
    left, right = st.columns([2, 3], gap="large")
    with left, open_image(sources[name][1]) as im:
        st.image(im.convert("RGB"), width="stretch")
    with right:
        for attr in item.attributes.values():
            tags = (" · :orange[needs review]" if attr.needs_review else "") + (
                " · :gray[experimental]" if attr.experimental else ""
            )
            st.markdown(f"**{attr.group}**: {', '.join(attr.values)}{tags}")
            st.progress(attr.confidence, text=f"confidence {attr.confidence:.0%}")
            alternatives = [f"{k} {v:.0%}" for k, v in list(attr.scores.items())[1:4]]
            st.caption("Next best: " + ", ".join(alternatives))

# ---------- Edit + export ----------
with table_tab:
    st.markdown(
        "Correct any value directly in the table. Lists use `|` as separator (e.g. `black|white`). "
        "Name, brand and price cannot be read from a photo: fill them in or leave them empty."
    )
    records = [
        to_record(results[n], i, cfg["sku_prefix"], sources[n][0]) for i, n in enumerate(sources, 1)
    ]
    table = to_frame(records)
    table.insert(0, "review", ["⚠" if results[n].needs_review else "✓" for n in sources])
    props = schema["properties"]
    edited = st.data_editor(
        table,
        key=f"editor-{'|'.join(sources)}",
        hide_index=True,
        width="stretch",
        disabled=["review", "sku", "image"],
        column_config={
            "review": st.column_config.TextColumn("", width="small", help="⚠ = at least one attribute needs review"),
            "category": st.column_config.SelectboxColumn(options=props["category"]["enum"], required=True),
            "gender": st.column_config.SelectboxColumn(options=props["gender"]["enum"], required=True),
            "season": st.column_config.SelectboxColumn(options=props["season"]["enum"], required=True),
            "price_eur": st.column_config.NumberColumn(min_value=0.0, format="€ %.2f"),
        },
    )  # fmt: skip
    final = from_frame(edited)
    errors = validate(final, cfg["paths"]["schema"])
    if errors:
        st.error("Fix these values before exporting:\n\n" + "\n".join(f"- {e}" for e in errors))
    else:
        st.success(f"{len(final)} records valid against `schema/product.schema.json`.")
    d1, d2, _ = st.columns([1, 1, 1])
    d1.download_button(
        "Download CSV", to_csv(final), "catalog.csv", "text/csv", disabled=bool(errors)
    )
    d2.download_button(
        "Download JSON", to_json(final), "catalog.json", "application/json", disabled=bool(errors)
    )
