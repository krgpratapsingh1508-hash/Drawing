import random

import streamlit as st

from drawing import THEMES, generate_book

st.set_page_config(page_title="Drawing Book", page_icon="🎨", layout="wide")

st.title("🎨 Bacho ki Drawing Book")
st.write("Har baar naya drawing book! Download karo, print karo aur rang bharo. 🖍️")

if "seed" not in st.session_state:
    # Har naya visitor / refresh = naya seed = naye drawing pages
    st.session_state.seed = random.SystemRandom().randrange(10 ** 9)

with st.sidebar:
    st.header("Settings")
    n_pages = st.slider("Kitne pages?", 1, 12, 4)
    chosen = st.multiselect("Kaunse themes?", list(THEMES), default=list(THEMES))

if st.button("🔄 Naya Drawing Book Do", type="primary"):
    st.session_state.seed = random.SystemRandom().randrange(10 ** 9)


@st.cache_data(show_spinner="Drawing book ban rahi hai... ✏️", max_entries=20)
def build(seed, n, themes):
    return generate_book(seed, list(themes), n)


seed = st.session_state.seed
pngs, pdf = build(seed, n_pages, tuple(chosen or THEMES))

st.download_button(
    "📄 Poori book PDF me download karo",
    data=pdf,
    file_name=f"drawing_book_{seed}.pdf",
    mime="application/pdf",
)

cols = st.columns(2)
for i, png in enumerate(pngs):
    with cols[i % 2]:
        st.image(png, caption=f"Page {i + 1}")
        st.download_button(
            f"⬇️ Page {i + 1} download",
            data=png,
            file_name=f"drawing_{seed}_{i + 1}.png",
            mime="image/png",
            key=f"dl_{seed}_{i}",
        )
