import streamlit as st
from groq import Groq
from PIL import Image
import base64
import io
import re
import json

st.set_page_config(page_title="TURIDEX", layout="wide")

# ====================== MODELO SOLICITADO ======================
SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# ====================== SESSION STATE ======================
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'log' not in st.session_state: st.session_state.log = []

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-size: 3.8em; text-align:center;}
    .header {background:#000; color:#0F0; padding:12px; border-radius:8px; text-align:center; font-size:1.4em;}
    .log-box {background:#111; color:#0F0; padding:10px; border-radius:5px; font-family:monospace; margin:8px 0;}
    .data-card, .historia-box {background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
                               padding: 18px; border-radius: 10px; margin: 12px 0;}
    .variant-btn {background: linear-gradient(135deg, #FFCC00, #FFEB3B) !important; color: black !important;
                  font-weight: bold !important; border: 3px solid black !important; border-radius: 15px !important;
                  padding: 14px !important; margin: 6px 0 !important;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='header'>📡 MODELO ACTIVO: {SELECTED_MODEL}</div>", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def add_log(msg):
    st.session_state.log.append(msg)
    if len(st.session_state.log) > 12: st.session_state.log.pop(0)

def resize_image(image_file):
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if img.width > 800 or img.height > 800:
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()

def get_prompt(is_image=True, item_name=None, category=None):
    if is_image:
        return """Analiza la imagen y responde **ÚNICAMENTE** con un JSON válido. No añadas nada más.

{
  "nombre": "Nombre claro del elemento",
  "categoria": "ANIMAL",
  "desc": "Descripción corta máximo 15 palabras",
  "historia": "Dos párrafos cortos con información real",
  "stats": [85, 75, 70, 60],
  "evos": ["NombreCorto1", "NombreCorto2", "NombreCorto3"]
}

Reglas estrictas: 
- categoria solo puede ser COMIDA, ANIMAL, LUGAR o ARTE
- Las evos deben ser solo nombres cortos, nunca frases largas."""
    else:
        return f"""Responde **solo** con un JSON válido sobre "{item_name}":

{{
  "nombre": "{item_name}",
  "categoria": "{category or 'ANIMAL'}",
  "desc": "descripción corta",
  "historia": "dos párrafos cortos",
  "stats": [80, 75, 70, 65],
  "evos": ["Nombre1", "Nombre2", "Nombre3"]
}}"""

def parse_json(text):
    try:
        match = re.search(r'(\{.*?\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        pass
    return {"nombre": "Error", "categoria": "ANIMAL", "desc": "Error de parsing", 
            "historia": "La IA no devolvió JSON válido.", "stats": [60,60,60,60], "evos": ["Var1","Var2","Var3"]}

def get_labels(category):
    cat = str(category).upper()
    if "ANIMAL" in cat: return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif any(x in cat for x in ["LUGAR", "ARTE", "PERSONA"]): return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else: return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)

    if st.button("🔄 Reiniciar TURIDEX"):
        st.session_state.clear()
        st.rerun()

    st.markdown("**Logs del Sistema**")
    for log in st.session_state.log:
        st.markdown(f"<div class='log-box'>{log}</div>", unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 2])

    with col_img:
        archivo = st.file_uploader("Carga una imagen", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True)
            if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                st.session_state.log = ["[START] Nueva petición iniciada"]
                st.session_state.current_item = "Procesando imagen..."
                st.rerun()

    with col_info:
        if st.session_state.current_item == "Procesando imagen...":
            try:
                add_log = lambda x: st.session_state.log.append(x)
                add_log("[1] Optimizando imagen (800px, calidad 85%)...")
                bytes_opt = resize_image(archivo)
                b64 = base64.b64encode(bytes_opt).decode()
                add_log("[2] Enviando petición al modelo meta-llama/llama-4-scout-17b-16e-instruct...")
                
                prompt = get_prompt(is_image=True)
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    model=SELECTED_MODEL,
                    temperature=0.1,
                    max_tokens=1000
                )
                add_log("[3] Respuesta recibida del modelo")
                add_log("[4] Parseando JSON...")
                
                data = parse_json(response.choices[0].message.content)
                
                st.session_state.current_item = data.get("nombre", "Elemento sin nombre")
                st.session_state.current_category = data.get("categoria", "ANIMAL")
                add_log(f"[SUCCESS] Análisis completado → {st.session_state.current_item}")
                st.rerun()
                
            except Exception as e:
                st.session_state.log.append(f"[ERROR] {str(e)}")
                st.error(f"Error crítico: {str(e)}")

        elif st.session_state.current_item:
            st.markdown(f"## {st.session_state.current_item}")
            st.markdown(f"<div class='data-card'><b>Categoría:</b> {st.session_state.current_category}</div>", unsafe_allow_html=True)
            st.info("El núcleo está funcionando. Ahora podemos mejorar las stats y las variantes.")

    st.markdown("</div>", unsafe_allow_html=True)
