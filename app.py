import streamlit as st
from groq import Groq
from PIL import Image
import base64
import io
import re
import json

st.set_page_config(page_title="TURIDEX", layout="wide")

# ====================== CONFIGURACIÓN CENTRALIZADA DE MODELOS ======================
MODELS = {
    "vision": "pixtral-12b-2409",
    "text_smart": "llama-3.3-70b-versatile",
    "fallback": "llama3-70b-8192"
}

# ====================== SESSION STATE ======================
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'historial' not in st.session_state: st.session_state.historial = []
if 'log' not in st.session_state: st.session_state.log = []
if 'active_model' not in st.session_state: st.session_state.active_model = MODELS["vision"]

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
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title-box'><h1 class='title'>⚡ TURIDEX ⚡</h1></div>", unsafe_allow_html=True)
st.markdown(f"<div class='model-header'>📡 MOTOR: {st.session_state.active_model}</div>", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def add_log(msg):
    st.session_state.log.append(msg)
    if len(st.session_state.log) > 10: st.session_state.log.pop(0)

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
  "nombre": "Nombre claro del elemento",
  "categoria": "ANIMAL",
  "desc": "Descripción corta máximo 15 palabras",
  "historia": "Dos párrafos cortos con información real",
  "stats": [85, 75, 70, 60],
  "evos": ["NombreCorto1", "NombreCorto2", "NombreCorto3"]
}

Reglas: categoria solo puede ser COMIDA, ANIMAL, LUGAR o ARTE. Las evos deben ser solo nombres cortos."""
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

def call_groq(prompt, image_b64=None, use_vision=True):
    """Función con fallback automático"""
    models_to_try = [MODELS["vision"] if use_vision else MODELS["text_smart"], MODELS["fallback"]]
    
    for model in models_to_try:
        try:
            st.session_state.active_model = model
            add_log(f"[MODEL] Intentando con {model}...")
            
            if image_b64 and use_vision:
                messages = [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]}]
            else:
                messages = [{"role": "user", "content": prompt}]
            
            response = client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=0.1,
                max_tokens=900,
                response_format={"type": "json_object"} if not use_vision else None
            )
            add_log(f"[OK] Respuesta recibida de {model}")
            return response.choices[0].message.content
        except Exception as e:
            add_log(f"[FALLBACK] {model} falló: {str(e)[:80]}...")
            continue
    raise Exception("Todos los modelos fallaron")

with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)

    if st.button("🔄 Reiniciar TURIDEX"):
        st.session_state.clear()
        st.rerun()

    st.markdown("**Sistema Logs**")
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
                add_log("[VISION] Optimizando payload de imagen...")
                bytes_opt = resize_image(archivo)
                b64 = base64.b64encode(bytes_opt).decode()
                
                prompt = get_prompt(is_image=True)
                raw_response = call_groq(prompt, b64, use_vision=True)
                
                data = parse_json(raw_response)
                
                st.session_state.current_item = data.get("nombre", "Elemento")
                st.session_state.current_category = data.get("categoria", "ANIMAL")
                st.session_state.historial = st.session_state.historial[-2:] + [st.session_state.current_item]
                add_log(f"[SUCCESS] Análisis completado: {st.session_state.current_item}")
                st.rerun()
                
            except Exception as e:
                add_log(f"[CRITICAL ERROR] {str(e)}")
                st.error(f"Error crítico: {str(e)}")

        elif st.session_state.current_item:
            st.markdown(f"## {st.session_state.current_item}")
            st.markdown(f"<div class='data-card'><b>Categoría:</b> {st.session_state.current_category}</div>", unsafe_allow_html=True)
            st.info("✅ Núcleo estable. Listo para siguiente fase (stats inteligentes + navegación de variantes).")

    st.markdown("</div>", unsafe_allow_html=True)
