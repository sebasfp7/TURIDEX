import streamlit as st
from groq import Groq
from PIL import Image
import base64
import io
import re
import json

st.set_page_config(page_title="TURIDEX", layout="wide")

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

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def add_log(msg):
    st.session_state.log.append(msg)

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
        return """Analiza la imagen y responde **ÚNICAMENTE** con un JSON válido. No escribas nada más.

{
  "nombre": "Nombre claro",
  "categoria": "ANIMAL",
  "desc": "Descripción corta máximo 15 palabras",
  "historia": "Dos párrafos cortos",
  "stats": [85, 75, 70, 60],
  "evos": ["Nombre1", "Nombre2", "Nombre3"]
}

Categorías permitidas: COMIDA, ANIMAL, LUGAR, ARTE"""
    else:
        return f"""Responde **solo** con un JSON válido:

{{
  "nombre": "{item_name}",
  "categoria": "{category}",
  "desc": "descripción corta",
  "historia": "dos párrafos cortos",
  "stats": [80, 75, 70, 65],
  "evos": ["Nombre1", "Nombre2", "Nombre3"]
}}"""

def parse_json(text):
    try:
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        pass
    return {"nombre": "Elemento", "categoria": "ANIMAL", "desc": "No se pudo analizar", 
            "historia": "Error en el procesamiento de la respuesta.", "stats": [60,60,60,60], "evos": ["Var1","Var2","Var3"]}

def get_labels(category):
    cat = str(category).upper()
    if "ANIMAL" in cat: return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif any(x in cat for x in ["LUGAR", "ARTE", "PERSONA"]): return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else: return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

# ====================== INTERFAZ ======================
with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)

    if st.button("🔄 Reiniciar TURIDEX"):
        st.session_state.clear()
        st.rerun()

    st.markdown(f"<div class='header'>📍 {st.session_state.current_item or 'Esperando imagen...'}</div>", unsafe_allow_html=True)

    if st.session_state.log:
        st.markdown("**Logs:**")
        for log in st.session_state.log[-10:]:
            st.markdown(f"<div class='log-box'>{log}</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        archivo = st.file_uploader("Carga una imagen (JPG, PNG)", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True)
            if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                st.session_state.log = ["1. Imagen cargada correctamente"]
                st.session_state.current_item = "Procesando imagen..."
                st.rerun()

    with col2:
        if st.session_state.current_item == "Procesando imagen...":
            try:
                add_log = lambda x: st.session_state.log.append(x)
                add_log("2. Optimizando imagen (800px, calidad 85%)...")
                bytes_opt = resize_image(archivo)
                add_log("3. Codificando imagen...")
                b64 = base64.b64encode(bytes_opt).decode()
                add_log("4. Enviando a Groq (llama-3.3-70b-versatile)...")
                
                prompt = get_prompt(is_image=True)
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}],
                    model="llama-3.3-70b-versatile",   # ← Modelo actual estable
                    temperature=0.1,
                    max_tokens=1000
                )
                add_log("5. Respuesta recibida")
                add_log("6. Procesando JSON...")
                
                data = parse_json(response.choices[0].message.content)
                
                st.session_state.current_item = data.get("nombre", "Elemento sin nombre")
                st.session_state.current_category = data.get("categoria", "ANIMAL")
                add_log(f"✅ COMPLETADO → {st.session_state.current_item}")
                st.rerun()
                
            except Exception as e:
                st.session_state.log.append(f"❌ ERROR: {str(e)}")
                st.error(f"Error: {str(e)}")

    # Mostrar resultado
    if st.session_state.current_item and st.session_state.current_item != "Procesando imagen...":
        with col2:
            st.success(f"**{st.session_state.current_item}**")
            st.info("Análisis completado. En próximas versiones añadiremos stats y variantes funcionales.")

    st.markdown("</div>", unsafe_allow_html=True)
