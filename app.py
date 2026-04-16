import streamlit as st
from groq import Groq
from PIL import Image
import base64
import io
import re
import json

st.set_page_config(page_title="TURIDEX", layout="wide")

# ====================== CONFIGURACIÓN DE MODELOS (ROUTER) ======================
MODEL_CONFIG = {
    "VISION": "llama-3.2-11b-vision-preview",
    "TEXT": "llama-3.3-70b-versatile",
    "FALLBACK": "llama3-70b-8192"
}

# ====================== SESSION STATE ======================
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'historial' not in st.session_state: st.session_state.historial = []
if 'log' not in st.session_state: st.session_state.log = []

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title-box {background:#000; border:4px solid #DC0A2D; border-radius:12px; padding:15px; text-align:center; margin-bottom:10px;}
    .title {color:#FFDE00 !important; font-family:'Courier New'; font-size:3.6em; margin:0; text-shadow:0 0 15px #FFDE00;}
    .model-header {background:#111; color:#00FFAA; padding:10px; border-radius:8px; text-align:center; font-family:monospace; margin-bottom:15px;}
    .log-box {background:#0A0A0A; color:#00FF00; padding:10px; border-radius:6px; font-family:monospace; font-size:0.9em; margin:6px 0;}
    .data-card, .historia-box {background:rgba(255,255,255,0.95); backdrop-filter:blur(10px); padding:18px; border-radius:10px; margin:12px 0;}
    .variant-btn {background:linear-gradient(135deg,#FFCC00,#FFEB3B) !important; color:black !important; font-weight:bold !important;
                  border:3px solid black !important; border-radius:15px !important; padding:14px !important; margin:6px 0 !important;}
    .variant-btn:hover {transform:translateY(-4px);}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title-box'><h1 class='title'>⚡ TURIDEX ⚡</h1></div>", unsafe_allow_html=True)
st.markdown(f"<div class='model-header'>📡 MOTOR ACTIVO → VISION: {MODEL_CONFIG['VISION']} | TEXT: {MODEL_CONFIG['TEXT']}</div>", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def add_log(msg):
    st.session_state.log.append(msg)
    if len(st.session_state.log) > 8: st.session_state.log.pop(0)

def resize_image(image_file):
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    if img.width > 800 or img.height > 800:
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()

def get_prompt(is_image=True, item_name=None, category=None):
    if is_image:
        return """Responde **únicamente** con un JSON válido. No añadas texto fuera de él.

{
  "nombre": "Nombre claro",
  "categoria": "ANIMAL",
  "desc": "Descripción corta (máx 15 palabras)",
  "historia": "Dos párrafos cortos con datos reales",
  "stats": [85, 75, 70, 60],
  "evos": ["NombreCorto1", "NombreCorto2", "NombreCorto3"]
}

Reglas estrictas: Si es ANIMAL usa stats de Fuerza, Agilidad, Peligro, Rareza. Si es COMIDA usa Sabor, Picante, Salud, Rareza."""
    else:
        return f"""Responde **solo** con JSON válido sobre "{item_name}":

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
    # Fallback seguro
    return {
        "nombre": st.session_state.get('current_item', 'Elemento'),
        "categoria": st.session_state.get('current_category', 'ANIMAL'),
        "desc": "No se pudo extraer descripción.",
        "historia": "Error en el procesamiento del JSON.",
        "stats": [65, 70, 60, 55],
        "evos": ["Variante1", "Variante2", "Variante3"]
    }

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

    # Logs de sistema (cuadro blanco convertido en logs)
    st.markdown("**Sistema Logs**")
    for log in st.session_state.log:
        st.markdown(f"<div class='log-box'>{log}</div>", unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 2])

    with col_img:
        archivo = st.file_uploader("Carga una imagen", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True)
            if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                st.session_state.log = ["[INFO] Imagen cargada"]
                st.session_state.current_item = "Procesando imagen..."
                st.rerun()

    with col_info:
        if st.session_state.current_item == "Procesando imagen...":
            try:
                add_log("[VISION] Redimensionando imagen (800px, 85% calidad)...")
                bytes_opt = resize_image(archivo)
                b64 = base64.b64encode(bytes_opt).decode()
                add_log(f"[VISION] Enviando a {MODEL_CONFIG['VISION']}...")

                prompt = get_prompt(is_image=True)
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    model=MODEL_CONFIG["VISION"],
                    temperature=0.1,
                    max_tokens=900
                )
                add_log("[VISION] Respuesta recibida. Parseando JSON...")
                data = parse_json(response.choices[0].message.content)

                st.session_state.current_item = data.get("nombre", "Elemento")
                st.session_state.current_category = data.get("categoria", "ANIMAL")
                st.session_state.historial = st.session_state.historial[-2:] + [st.session_state.current_item]
                add_log(f"[OK] Análisis completado: {st.session_state.current_item}")
                st.rerun()

            except Exception as e:
                add_log(f"[ERROR] {str(e)}")
                st.error(f"Error: {str(e)}")

        elif st.session_state.current_item:
            # Mostrar resultado
            st.markdown(f"## {st.session_state.current_item}")
            st.markdown(f"<div class='data-card'><b>Categoría:</b> {st.session_state.current_category}</div>", unsafe_allow_html=True)
            st.info("Stats y variantes se mostrarán en la siguiente iteración una vez estabilizado el núcleo.")

    st.markdown("</div>", unsafe_allow_html=True)
