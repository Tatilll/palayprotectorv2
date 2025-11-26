import streamlit as st
import requests

# =====================================
# CONFIG
# =====================================
st.set_page_config(page_title="Palay Protector", layout="centered")

# =====================================
# LANGUAGE SESSION
# =====================================
if "page" not in st.session_state:
    st.session_state.page = "language"

if "selected_language" not in st.session_state:
    st.session_state.selected_language = "en"

# =====================================
# 🌐 LINGVA TRANSLATOR (NO SIGNUP)
# =====================================
def translate_text(text):
    if st.session_state.selected_language == "en":
        return text
    try:
        url = f"https://lingva.ml/api/v1/en/{st.session_state.selected_language}/{text}"
        r = requests.get(url)
        if r.status_code == 200:
            return r.json().get("translation", text)
    except:
        return text
    return text

# =====================================
# 🌐 LANGUAGE SELECTION SCREEN
# =====================================
if st.session_state.page == "language":

    st.markdown("""
    <div style="max-width:400px;margin:auto;padding:30px;
    border-radius:20px;background:white;text-align:center;
    box-shadow:0 10px 25px rgba(0,0,0,0.2);">
    <h2 style="color:#2e7d32;">Select Language</h2>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🇺🇸 English"):
        st.session_state.selected_language = "en"

    if st.button("🇵🇭 Tagalog"):
        st.session_state.selected_language = "tl"

    if st.button("Continue"):
        st.session_state.page = "home"
        st.rerun()

# =====================================
# 🏠 HOME PAGE
# =====================================
elif st.session_state.page == "home":

    st.title(translate_text("Welcome to Palay Protector"))
    st.write(translate_text("This system helps farmers detect rice diseases and provides remedies."))

    if st.button(translate_text("Open Disease Library")):
        st.session_state.page = "library"
        st.rerun()

# =====================================
# 📚 LIBRARY + REMEDY (FULL)
# =====================================
elif st.session_state.page == "library":

    st.header(translate_text("Rice Disease Library"))

    diseases = [
        {
            "name": "Brown Spot",
            "desc": "A fungal disease causing brown circular lesions on rice leaves which weakens the plant and lowers yield.",
            "remedy": "Use resistant rice varieties, apply balanced fertilizer, and spray approved fungicides when necessary."
        },
        {
            "name": "Rice Blast",
            "desc": "A serious fungal disease that causes diamond-shaped lesions and leads to crop failure if untreated.",
            "remedy": "Use blast-resistant varieties, avoid excessive nitrogen fertilizer, and apply fungicides early."
        },
        {
            "name": "Bacterial Leaf Blight",
            "desc": "A bacterial infection that causes yellowing and drying of rice leaves from the edges.",
            "remedy": "Plant resistant varieties, ensure good drainage, and avoid over-irrigation."
        },
        {
            "name": "Sheath Blight",
            "desc": "A disease that attacks the leaf sheath and weakens the stem, causing lodging.",
            "remedy": "Maintain proper spacing and apply fungicides when symptoms appear."
        },
        {
            "name": "Leaf Scald",
            "desc": "Creates large white or gray lesions that reduce the photosynthesis capacity of rice leaves.",
            "remedy": "Use tolerant varieties and limit excessive nitrogen use."
        },
        {
            "name": "False Smut",
            "desc": "Produces green spore balls on grains, reducing grain quality and yield.",
            "remedy": "Spray fungicides at booting stage and remove infected grains after harvest."
        },
        {
            "name": "Tungro",
            "desc": "A viral disease spread by leafhoppers causing stunted growth and yellow-orange discoloration.",
            "remedy": "Control leafhopper populations and plant tungro-resistant varieties."
        },
        {
            "name": "Healthy Rice",
            "desc": "The rice plant shows no symptoms of disease and is growing normally.",
            "remedy": "Maintain proper care through balanced fertilization and regular monitoring."
        }
    ]

    for d in diseases:
        st.subheader(translate_text(d["name"]))
        st.write(translate_text(d["desc"]))
        st.markdown(f"**{translate_text('Recommended Remedy')}:** {translate_text(d['remedy'])}")
        st.markdown("---")

    if st.button(translate_text("Back to Home")):
        st.session_state.page = "home"
        st.rerun()
