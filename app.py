import streamlit as st
from groq import Groq
from PIL import Image
import base64
from gtts import gTTS
import io
import re
import json

st.set_page_config(page_title="TURIDEX", layout="wide")

# ====================== SESSION STATE ======================
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'historial' not in st.session_state: st.session_state.historial = []

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-family: 'Courier New', monospace; font-size: 3.8em;
            text-shadow: 0 0 20px #FFDE00, 0 0 35px #FF0000;}
    .header-status {background: #000000; color: #00FF41; padding: 14px; border-radius: 8px;
                    text-align: center; font-family: 'Courier New', monospace; margin-bottom: 15px; font-size: 1.5em;}
    .data-card, .historia-box {background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
                               padding: 18px; border-radius: 10px; margin: 12px 0;}
    .variant-btn {background: linear-gradient(135deg, #FFCC00, #FFEB3B) !important; color: black !important;
                  font-weight: bold !important; border: 3px solid black !important; border-radius: 15px !important;
                  padding: 14px !important; margin: 6px 0 !important;}
    .variant-btn:hover {transform: translateY(-4px);}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title' style='text-align:center'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ====================== CACHÉ ======================
@st.cache_data(show_spinner=False, ttl=360)
def procesar_imagen_cache(_image_bytes):
    return base64.b64encode(_image_bytes).decode()

@st.cache_data(show_spinner=False, ttl=180)
def analizar_con_ia(prompt, image_b64=None, is_text=False):
    if image_b64:
        messages = [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
        ]}]
        model = "llama-4-scout-17b-16e-instruct"
    else:
        messages = [{"role": "user", "content": prompt}]
        model = "llama3-8b-8192"

    response = client.chat.completions.create(
        messages=messages,
        model=model,
        temperature=0.05,
        max_tokens=900
    )
    return response.choices[0].message.content

# ====================== PROMPT DEFINITIVO ======================
def get_prompt(item_name=None, inherited_category=None):
    if item_name is None:
        return """Analiza la imagen y responde **ÚNICAMENTE** con un JSON válido. No añadas nada más.

{
  "nombre": "nombre del elemento",
  "categoria": "ANIMAL",
  "desc": "descripción corta máximo 15 palabras",
  "historia": "dos párrafos cortos con información real",
  "stats": [80, 75, 65, 70],
  "evos": ["Nombre Corto 1", "Nombre Corto 2", "Nombre Corto 3"]
}

Reglas: categoria solo puede ser COMIDA, ANIMAL, LUGAR o ARTE. Las evos deben ser solo nombres cortos."""
    
    else:
        return f"""Responde **solo** con un JSON válido sobre "{item_name}" (categoría: {inherited_category}):

{{
  "nombre": "{item_name}",
  "categoria": "{inherited_category}",
  "desc": "descripción corta",
  "historia": "dos párrafos cortos",
  "stats": [75, 80, 70, 65],
  "evos": ["Nombre1", "Nombre2", "Nombre3"]
}}

No escribas nada fuera del JSON."""

def parse_json_response(text):
    try:
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return json.loads(text)
    except:
        return {
            "nombre": st.session_state.get('current_item', 'Elemento'),
            "categoria": st.session_state.get('current_category', 'LUGAR'),
            "desc": "No se pudo extraer descripción.",
            "historia": "No se pudo extraer historia.",
            "stats": [65, 70, 60, 55],
            "evos": ["Variante 1", "Variante 2", "Variante 3"]
        }

def get_labels(category):
    cat = str(category).upper()
    if "ANIMAL" in cat: return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif any(x in cat for x in ["LUGAR", "ARTE", "PERSONA"]): return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else: return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

def resize_image(image_file):
    """Versión corregida y robusta"""
    img = Image.open(image_file)
    # Convertir a RGB si tiene transparencia (RGBA, P)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    # Redimensionar manteniendo proporción
    if img.width > 800 or img.height > 800:
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()

# ====================== INTERFAZ ======================
with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)

    if st.button("🔄 Reiniciar TURIDEX"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    status = st.session_state.current_item or "Esperando objetivo..."
    st.markdown(f"<div class='header-status'>📍 ANALIZANDO: {status}</div>", unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 2])

    if st.session_state.current_item and st.session_state.current_category:
        item = st.session_state.current_item
        cat = st.session_state.current_category

        with st.spinner("Generando ficha..."):
            try:
                prompt = get_prompt(item, cat)
                raw_response = analizar_con_ia(prompt, None, is_text=True)
                data = parse_json_response(raw_response)

                stats = data.get("stats", [60, 60, 60, 60])
                variantes = [str(v) for v in data.get("evos", ["Var1", "Var2", "Var3"])][:3]
                labels = get_labels(data.get("categoria", cat))

                with col_img:
                    st.info(f"🌐 Visualización de **{data.get('nombre', item)}**")

                with col_info:
                    st.markdown(f"## {data.get('nombre', item)}")
                    st.markdown(f"<div class='data-card'><b>Categoría:</b> {data.get('categoria', cat)}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-card'>{data.get('desc', '')}</div>", unsafe_allow_html=True)
                    
                    st.markdown("### 📖 Historia")
                    st.markdown(f"<div class='historia-box'>{data.get('historia', '')}</div>", unsafe_allow_html=True)
                    
                    st.markdown("### 📊 Puntos Base")
                    c1, c2 = st.columns(2)
                    with c1:
                        for i in range(2):
                            st.write(f"{labels[i]}: **{stats[i]}%**")
                            st.progress(stats[i]/100)
                    with c2:
                        for i in range(2, 4):
                            st.write(f"{labels[i]}: **{stats[i]}%**")
                            st.progress(stats[i]/100)
                    
                    st.markdown("### 🔄 Variantes")
                    for var in variantes:
                        if st.button(str(var), key=f"var_{var}", use_container_width=True):
                            st.session_state.current_item = str(var)
                            st.session_state.current_category = data.get("categoria", cat)
                            st.rerun()

            except Exception as e:
                st.error(f"Error: {str(e)}")

    else:
        with col_img:
            archivo = st.file_uploader("Carga una imagen (JPG, PNG)", type=["jpg","png","jpeg"])
            if archivo:
                st.image(archivo, use_container_width=True)
                if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                    bytes_opt = resize_image(archivo)
                    b64 = procesar_imagen_cache(bytes_opt)
                    
                    st.session_state.current_item = "Procesando imagen..."
                    st.rerun()

                    prompt = get_prompt()
                    raw = analizar_con_ia(prompt, b64, is_text=False)
                    data = parse_json_response(raw)
                    
                    st.session_state.current_item = data.get("nombre", "Elemento")
                    st.session_state.current_category = data.get("categoria", "LUGAR")
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
