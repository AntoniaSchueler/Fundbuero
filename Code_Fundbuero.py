# Fundbuero
import io
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageOps
from supabase import create_client
from tensorflow.keras.models import load_model

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
st.set_page_config(
    page_title="Fundbüro am Katharineum",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CATEGORIES = [
    "Trinkflaschen",
    "Schuhe",
    "T-Shirts",
    "Federtaschen",
    "Sonstiges",
]

MODEL_PATH = Path("model/keras_model.h5")
LABELS_PATH = Path("model/labels.txt")
BUCKET_NAME = "fundstuecke"

MAX_UPLOAD_MB = 8
MAX_IMAGE_SIZE = 1600

# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap');

    :root {
        --green: #145c2a;
        --green-light: #eaf4ec;
        --green-mid: #2e7d46;
        --cream: #fbfaf6;
        --ink: #18321f;
        --line: #145c2a;
    }

    .stApp {
        background: var(--cream);
        color: var(--ink);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 4rem;
    }

    h1, h2, h3 {
        font-family: 'Libre Baskerville', Georgia, serif !important;
        color: var(--green) !important;
    }

    .brand-title {
        font-family: 'Libre Baskerville', Georgia, serif;
        font-style: italic;
        font-size: clamp(2.2rem, 5vw, 4.2rem);
        line-height: 1.1;
        color: var(--green);
        margin: 1rem 0 2.2rem 0;
    }

    .brand-subtitle {
        color: var(--green-mid);
        font-size: 1.05rem;
        margin-top: -1.7rem;
        margin-bottom: 2rem;
    }

    .top-rule {
        height: 2px;
        background: var(--green);
        margin: 0.5rem 0 1.5rem 0;
    }

    .hero-card {
        border: 2px solid var(--line);
        padding: 2rem;
        background: rgba(255,255,255,0.45);
        min-height: 250px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .hero-card h2 {
        margin-top: 0;
        font-size: 2rem;
    }

    .category-card {
        border: 1.5px solid var(--line);
        padding: 1.2rem 0.7rem;
        text-align: center;
        min-height: 90px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: white;
    }

    .fund-card {
        border: 1.5px solid var(--line);
        background: white;
        padding: 0.65rem;
        height: 100%;
    }

    .fund-card img {
        width: 100%;
        aspect-ratio: 1 / 1;
        object-fit: cover;
        display: block;
    }

    .fund-category {
        color: var(--green);
        font-family: 'Libre Baskerville', Georgia, serif;
        font-weight: 700;
        margin-top: 0.7rem;
    }

    .fund-location {
        color: #526057;
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }

    div.stButton > button {
        border: 2px solid var(--green);
        color: var(--green);
        background: transparent;
        border-radius: 0;
        min-height: 3.2rem;
        font-family: 'Libre Baskerville', Georgia, serif;
        font-size: 1.05rem;
    }

    div.stButton > button:hover {
        color: white;
        background: var(--green);
        border-color: var(--green);
    }

    .primary-button div.stButton > button {
        background: var(--green);
        color: white;
    }

    [data-testid="stFileUploader"] {
        border: 1.5px dashed var(--green);
        padding: 0.5rem;
        background: white;
    }

    .footer {
        text-align: center;
        color: var(--green-mid);
        margin-top: 4rem;
        font-family: 'Libre Baskerville', Georgia, serif;
        font-style: italic;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .brand-title {
            font-size: 2.4rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# Supabase
# ------------------------------------------------------------
@st.cache_resource
def get_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    except Exception as exc:
        raise RuntimeError(
            "Supabase ist noch nicht eingerichtet. Bitte SUPABASE_URL und "
            "SUPABASE_SERVICE_ROLE_KEY in Streamlit Secrets hinterlegen."
        ) from exc
    return create_client(url, key)


# ------------------------------------------------------------
# Model
# ------------------------------------------------------------
@st.cache_resource
def get_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modell nicht gefunden: {MODEL_PATH}")
    return load_model(MODEL_PATH, compile=False)


@st.cache_data
def get_labels():
    if LABELS_PATH.exists():
        labels = []
        for line in LABELS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                # Teachable Machines labels.txt: "0 Trinkflaschen"
                parts = line.split(maxsplit=1)
                labels.append(parts[1] if len(parts) == 2 else line)
        if labels:
            return labels
    return CATEGORIES


def predict_category(image: Image.Image):
    model = get_model()
    labels = get_labels()

    image = ImageOps.exif_transpose(image).convert("RGB")
    image = image.resize((224, 224))
    array = np.asarray(image).astype(np.float32)
    array = array / 127.5 - 1.0
    array = np.expand_dims(array, axis=0)

    prediction = model.predict(array, verbose=0)[0]
    index = int(np.argmax(prediction))
    confidence = float(prediction[index])

    if index >= len(labels):
        label = CATEGORIES[index] if index < len(CATEGORIES) else "Sonstiges"
    else:
        label = labels[index]

    # Keep the app's official spelling/category list.
    if label not in CATEGORIES:
        label = "Sonstiges"

    return label, confidence, prediction


# ------------------------------------------------------------
# Image helpers
# ------------------------------------------------------------
def prepare_image(uploaded_file):
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image).convert("RGB")

    if max(image.size) > MAX_IMAGE_SIZE:
        image.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE))

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=88, optimize=True)
    return image, output.getvalue()


def make_storage_path():
    now = datetime.now(timezone.utc)
    return f"{now:%Y/%m/%d}/{uuid.uuid4().hex}.jpg"


def signed_image_url(supabase, storage_path, expires_in=3600):
    result = (
        supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_url(storage_path, expires_in)
    )

    if isinstance(result, dict):
        return result.get("signedURL") or result.get("signedUrl")

    # Compatibility with response objects in different supabase-py versions.
    return getattr(result, "signed_url", None) or getattr(result, "signedURL", None)


# ------------------------------------------------------------
# Database helpers
# ------------------------------------------------------------
def cleanup_old_items(supabase):
    """
    Automatic cleanup:
    - collected items older than 7 days
    - all other items older than 365 days

    This is triggered whenever the app is used. For a strict background
    deletion even when nobody opens the app, configure an external scheduled
    job in Supabase later.
    """
    now = datetime.now(timezone.utc)
    one_week_ago = (now - timedelta(days=7)).isoformat()
    one_year_ago = (now - timedelta(days=365)).isoformat()

    collected = (
        supabase.table("fundstuecke")
        .select("id, image_path")
        .eq("status", "abgeholt")
        .lt("collected_at", one_week_ago)
        .execute()
    ).data or []

    expired = (
        supabase.table("fundstuecke")
        .select("id, image_path")
        .neq("status", "abgeholt")
        .lt("created_at", one_year_ago)
        .execute()
    ).data or []

    to_delete = collected + expired

    if not to_delete:
        return

    ids = [item["id"] for item in to_delete]
    paths = [item["image_path"] for item in to_delete if item.get("image_path")]

    if paths:
        try:
            supabase.storage.from_(BUCKET_NAME).remove(paths)
        except Exception:
            # The database records should still be removed if an orphaned image
            # cannot be deleted.
            pass

    supabase.table("fundstuecke").delete().in_("id", ids).execute()


def insert_item(supabase, category, location, image_bytes, original_name):
    storage_path = make_storage_path()

    supabase.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=image_bytes,
        file_options={
            "content-type": "image/jpeg",
            "cache-control": "3600",
            "upsert": "false",
        },
    )

    row = {
        "category": category,
        "location": location.strip(),
        "image_path": storage_path,
        "original_filename": original_name[:255],
        "status": "verfuegbar",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        response = supabase.table("fundstuecke").insert(row).execute()
        return response.data[0]
    except Exception:
        # Avoid leaving an image behind if the database insert fails.
        try:
            supabase.storage.from_(BUCKET_NAME).remove([storage_path])
        except Exception:
            pass
        raise


def get_available_items(supabase, category=None):
    query = (
        supabase.table("fundstuecke")
        .select("id, category, location, image_path, created_at")
        .eq("status", "verfuegbar")
        .order("created_at", desc=True)
    )

    if category and category != "Alle":
        query = query.eq("category", category)

    return query.execute().data or []


def mark_collected(supabase, item_id):
    return (
        supabase.table("fundstuecke")
        .update(
            {
                "status": "abgeholt",
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", item_id)
        .eq("status", "verfuegbar")
        .execute()
    )


# ------------------------------------------------------------
# Navigation
# ------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "start"

try:
    supabase = get_supabase()
except Exception as exc:
    st.error(str(exc))
    st.info(
        "Die App-Struktur ist fertig. Für den Betrieb müssen zuerst die "
        "Supabase-Zugangsdaten in Streamlit Secrets eingetragen werden."
    )
    st.stop()

try:
    cleanup_old_items(supabase)
except Exception as exc:
    # Do not block normal use if cleanup temporarily fails.
    st.warning("Die automatische Aufräumroutine konnte gerade nicht ausgeführt werden.")


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
st.markdown('<div class="top-rule"></div>', unsafe_allow_html=True)
st.markdown(
    '<div class="brand-title">Fundbüro am<br> Katharineum</div>',
    unsafe_allow_html=True,
)

# Small navigation row
nav1, nav2, nav3 = st.columns([1, 1, 1])
with nav1:
    if st.button("Startseite", use_container_width=True):
        st.session_state.page = "start"
        st.rerun()
with nav2:
    if st.button("Gefunden", use_container_width=True):
        st.session_state.page = "gefunden"
        st.rerun()
with nav3:
    if st.button("Verwaltung", use_container_width=True):
        st.session_state.page = "verwaltung"
        st.rerun()

st.markdown("---")


# ------------------------------------------------------------
# Startseite
# ------------------------------------------------------------
def render_start():
    left, right = st.columns(2, gap="large")

    with left:
        st.markdown(
            """
            <div class="hero-card">
                <h2>Verloren</h2>
                <p>Du suchst einen Gegenstand? Durchsuche die aktuell
                gefundenen Sachen nach Kategorie.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("Gefundene Sachen ansehen", use_container_width=True):
            st.session_state.page = "gefunden"
            st.rerun()

    with right:
        st.markdown(
            """
            <div class="hero-card">
                <h2>Gefunden</h2>
                <p>Du hast etwas gefunden? Lade ein Foto hoch. Die KI hilft
                bei der Einordnung in eine Kategorie.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("Fundstück melden", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()

    st.markdown(
        '<div class="footer">Ein verlorener Gegenstand findet vielleicht seinen Weg zurück.</div>',
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Upload page
# ------------------------------------------------------------
def render_upload():
    st.header("Fundstück melden")
    st.write(
        "Lade ein Foto hoch. Die KI schlägt eine Kategorie vor. "
        "Du kannst die Kategorie vor dem Speichern korrigieren."
    )

    uploaded = st.file_uploader(
        "Foto auswählen",
        type=["jpg", "jpeg", "png"],
        help=f"Maximal {MAX_UPLOAD_MB} MB.",
    )

    if uploaded is None:
        st.info("Bitte zuerst ein Foto auswählen.")
        return

    if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
        st.error(f"Das Bild darf höchstens {MAX_UPLOAD_MB} MB groß sein.")
        return

    try:
        image, image_bytes = prepare_image(uploaded)
    except Exception:
        st.error("Das Bild konnte nicht gelesen werden.")
        return

    try:
        predicted, confidence, probabilities = predict_category(image)
    except Exception as exc:
        st.error(
            "Das KI-Modell konnte nicht geladen oder ausgeführt werden. "
            "Prüfe, ob keras_model.h5 im Ordner model liegt."
        )
        st.exception(exc)
        return

    left, right = st.columns(2, gap="large")

    with left:
        st.image(image, caption="Vorschau", use_container_width=True)

    with right:
        st.subheader("KI-Ergebnis")
        st.write(f"**Erkannte Kategorie:** {predicted}")
        st.progress(min(max(confidence, 0.0), 1.0))
        st.caption(f"Erkennungswahrscheinlichkeit: {confidence:.0%}")

        category = st.selectbox(
            "Kategorie bestätigen oder ändern",
            CATEGORIES,
            index=CATEGORIES.index(predicted) if predicted in CATEGORIES else 0,
        )

        location = st.text_input(
            "Fundort",
            placeholder="z. B. Sporthalle, Pausenhof, Raum 204 …",
            max_chars=200,
        )

        st.markdown('<div class="primary-button">', unsafe_allow_html=True)
        save = st.button("Fundstück speichern", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if save:
            if not location.strip():
                st.warning("Bitte gib einen kurzen Fundort an.")
            else:
                try:
                    insert_item(
                        supabase=supabase,
                        category=category,
                        location=location,
                        image_bytes=image_bytes,
                        original_name=uploaded.name,
                    )
                    st.success("Das Fundstück wurde gespeichert.")
                    st.session_state.page = "gefunden"
                    st.rerun()
                except Exception as exc:
                    st.error("Das Fundstück konnte nicht gespeichert werden.")
                    st.exception(exc)


# ------------------------------------------------------------
# Found items page
# ------------------------------------------------------------
def render_found():
    st.header("Gefundene Gegenstände")

    selected = st.selectbox(
        "Kategorie",
        ["Alle"] + CATEGORIES,
        index=0,
    )

    items = get_available_items(
        supabase,
        None if selected == "Alle" else selected,
    )

    if not items:
        st.info("Aktuell wurden keine passenden Fundstücke gefunden.")
        return

    cols = st.columns(3, gap="large")

    for index, item in enumerate(items):
        with cols[index % 3]:
            url = signed_image_url(supabase, item["image_path"], expires_in=3600)
            if url:
                st.image(url, use_container_width=True)

            st.markdown(
                f'<div class="fund-category">{item["category"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="fund-location">Fundort: {item["location"]}</div>',
                unsafe_allow_html=True,
            )

            try:
                dt = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                date_text = dt.astimezone().strftime("%d.%m.%Y")
                st.caption(f"Gefunden am {date_text}")
            except Exception:
                pass

            st.markdown("<br>", unsafe_allow_html=True)


# ------------------------------------------------------------
# Admin page
# ------------------------------------------------------------
def render_admin():
    st.header("Verwaltung")
    st.write(
        "Dieser Bereich ist für das Sekretariat. Hier können Fundstücke "
        "als abgeholt markiert werden."
    )

    admin_code = st.text_input(
        "Verwaltungscode",
        type="password",
        help="Der Code wird nicht im GitHub-Repository gespeichert.",
    )

    try:
        expected_code = st.secrets["ADMIN_CODE"]
    except Exception:
        st.error("ADMIN_CODE fehlt in den Streamlit Secrets.")
        return

    if not admin_code:
        st.info("Bitte Verwaltungscode eingeben.")
        return

    if admin_code != expected_code:
        st.error("Der Verwaltungscode ist nicht korrekt.")
        return

    st.success("Verwaltungsbereich geöffnet.")

    items = get_available_items(supabase)

    if not items:
        st.info("Es sind aktuell keine offenen Fundstücke vorhanden.")
        return

    for item in items:
        with st.container(border=True):
            left, middle, right = st.columns([1, 2, 1])

            with left:
                url = signed_image_url(supabase, item["image_path"], expires_in=900)
                if url:
                    st.image(url, use_container_width=True)

            with middle:
                st.subheader(item["category"])
                st.write(f"**Fundort:** {item['location']}")
                try:
                    dt = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                    st.write(f"**Gemeldet:** {dt.astimezone().strftime('%d.%m.%Y %H:%M')}")
                except Exception:
                    pass

            with right:
                confirm = st.checkbox(
                    "Als abgeholt markieren",
                    key=f"confirm_{item['id']}",
                )
                if confirm:
                    if st.button(
                        "Abholung speichern",
                        key=f"collect_{item['id']}",
                        use_container_width=True,
                    ):
                        try:
                            mark_collected(supabase, item["id"])
                            st.success("Erledigt.")
                            st.rerun()
                        except Exception as exc:
                            st.error("Status konnte nicht gespeichert werden.")
                            st.exception(exc)


# ------------------------------------------------------------
# Route
# ------------------------------------------------------------
if st.session_state.page == "start":
    render_start()
elif st.session_state.page == "gefunden":
    render_found()
elif st.session_state.page == "upload":
    render_upload()
elif st.session_state.page == "verwaltung":
    render_admin()
else:
    st.session_state.page = "start"
    render_start()
