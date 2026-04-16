import streamlit as st
from groq import Groq
from PIL import Image
import base64
from gtts import gTTS
import io
import re
import json
import requests
from io import BytesIO

st.set_page_config(page_title="TURIDEX", layout="wide")

# ====================== SESSION STATE ======================
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'historial' not in st.session_state: st.session_state.historial = []
if 'status_log' not in st.session_state: st.session_state.status_log = []

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-family: 'Courier New', monospace; font-size: 3.8em;
            text-shadow: 0 0 20px #FFDE00, 0 0 35px #FF0000;}
    .header-status {background: #000000; color: #00FF41; padding: 12px; border-radius: 8px;
                    text-align: center; font-family: 'Courier New', monospace; margin-bottom: 15px;}
    .log {background: #111111; color: #00FF00; padding: 8px; border-radius: 5px; font-family: monospace; font-size: 0.9em;}
    .data-card, .historia-box {background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
                               padding: 18px; border-radius: 10px; margin: 10px 0;}
    .variant-btn {background: linear-gradient(135deg, #FFCC00, #FFEB3B) !important; color: black !important;
                  font-weight: bold !important; border: 3px solid black !important; border-radius: 15px !important;
                  padding: 14px !important; margin: 6px 0 !important;}
    .variant-btn:hover {transform: translateY(-4px);}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title' style='text-align:center'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# ====================== CACHÉ ======================
@st.cache_data(show_spinner=False, ttl=300)
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
        model = "llama3-8b-8192"  # Modelo más ligero para texto

    response = client.chat.completions.create(
        messages=messages,
        model=model,
        temperature=0.05,
        max_tokens=800,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

# ====================== PROMPT DEFINITIVO (JSON) ======================
def get_prompt(item_name=None, inherited_category=None):
    if item_name is None:
        return """Analiza la imagen y responde ÚNICAMENTE con un JSON válido con esta estructura exacta:
{
  "nombre": "string",
  "categoria": "COMIDA|ANIMAL|LUGAR|ARTE",
  "desc": "descripción corta máximo 15 palabras",
  "historia": "dos párrafos cortos",
  "stats": [85, 45, 20, 65],
  "evos": ["nombre1", "nombre2", "nombre3"]
}
Reglas: Si es animal usa stats de fuerza/agilidad/peligro/rareza. Si es comida usa sabor/picante/salud/rareza. Variantes deben ser solo nombres cortos."""
    
    else:
        return f"""{{
  "nombre": "{item_name}",
  "categoria": "{inherited_category}",
  "desc": "descripción corta máximo 15 palabras",
  "historia": "dos párrafos cortos y reales",
  "stats": [números entre 10 y 95 según categoría],
  "evos": ["nombre corto 1", "nombre corto 2", "nombre corto 3"]
}}
Reglas estrictas: 
- Solo responde con JSON válido.
- Las variantes deben ser sustantivos cortos del mismo tipo.
- No incluyas explicaciones ni texto fuera del JSON."""

# ====================== UTILIDADES ======================
def resize_image(image_file):
    img = Image.open(image_file)
    if img.width > 800:
        ratio = 800 / img.width
        new_size = (800, int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()

def parse_json_response(text):
    try:
        return json.loads(text)
    except:
        # Fallback si el JSON falla
        return {
            "nombre": st.session_state.current_item or "Desconocido",
            "categoria": st.session_state.current_category or "LUGAR",
            "desc": "No se pudo extraer descripción.",
            "historia": "No se pudo extraer historia.",
            "stats": [70, 65, 50, 60],
            "evos": ["Variante 1", "Variante 2", "Variante 3"]
        }

def get_labels(category):
    cat = str(category).upper()
    if "ANIMAL" in cat: return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif any(x in cat for x in ["LUGAR", "ARTE", "PERSONA"]): return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else: return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

# ====================== INTERFAZ ======================
with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)

    if st.button("🔄 Reiniciar TURIDEX"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    # Header dinámico
    status_text = st.session_state.current_item or "Esperando objetivo..."
    st.markdown(f"<div class='header-status'>📍 ANALIZANDO: {status_text}</div>", unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 2])

    if st.session_state.current_item and st.session_state.current_category:
        item = st.session_state.current_item
        cat = st.session_state.current_category

        with st.spinner("Procesando..."):
            try:
                prompt = get_prompt(item, cat)
                json_str = analizar_con_ia(prompt, None, is_text=True)
                data = parse_json_response(json_str)

                variantes = data.get("evos", ["Variante1", "Variante2", "Variante3"])[:3]
                stats = data.get("stats", [60, 60, 60, 60])
                labels = get_labels(data.get("categoria", cat))

                with col_img:
                    img = generate_image(item)  # Función optimizada
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.info("🌐 Visualización generada por IA")

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
                        if st.button(var, key=f"var_{var}", use_container_width=True):
                            st.session_state.current_item = var
                            st.session_state.current_category = data.get("categoria", cat)
                            st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    else:
        with col_img:
            archivo = st.file_uploader("Carga una imagen", type=["jpg","png","jpeg"])
            if archivo:
                st.image(archivo, use_container_width=True)
                if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                    bytes_optimizados = resize_image(archivo)
                    b64 = procesar_imagen_cache(bytes_optimizados)
                    
                    st.session_state.current_item = "Procesando imagen..."
                    st.session_state.current_category = "DESCONOCIDO"
                    
                    prompt = get_prompt()
                    json_str = analizar_con_ia(prompt, b64, is_text=False)
                    data = parse_json_response(json_str)
                    
                    st.session_state.current_item = data.get("nombre", "Elemento")
                    st.session_state.current_category = data.get("categoria", "LUGAR")
                    st.session_state.historial = [st.session_state.current_item]
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
