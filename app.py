import streamlit as st
from groq import Groq
from PIL import Image
import base64
import io
import re
import json
import requests
from io import BytesIO
from gtts import gTTS

st.set_page_config(page_title="TURIDEX", layout="wide")

SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'log' not in st.session_state: st.session_state.log = []

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-size: 3.8em; text-align:center;}
    .header {background:#000; color:#0F0; padding:12px; border-radius:8px; text-align:center; font-size:1.4em;}
    .log-box {background:#111; color:#0F0; padding:8px; border-radius:5px; font-family:monospace; margin:6px 0;}
    .data-card, .historia-box {background:rgba(255,255,255,0.95); backdrop-filter:blur(10px); padding:18px; border-radius:10px; margin:12px 0;}
    .variant-btn {background:linear-gradient(135deg,#FFCC00,#FFEB3B) !important; color:black !important; font-weight:bold !important;
                  border:3px solid black !important; border-radius:15px !important; padding:14px !important; margin:6px 0 !important;}
    .variant-btn:hover {transform:translateY(-4px); box-shadow:0 8px 15px rgba(220,10,45,0.5);}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='header'>📡 MODELO: {SELECTED_MODEL}</div>", unsafe_allow_html=True)

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

def generate_image(name):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, realistic, high quality, clean background, national geographic style')}"
        resp = requests.get(url + "?width=700&height=500&nologo=true", timeout=10)
        if resp.status_code == 200:
            return Image.open(BytesIO(resp.content))
    except:
        pass
    return None

def get_prompt(is_image=True, item_name=None, category=None):
    if is_image:
        return """Analiza la imagen y responde **SOLO** con un JSON válido:

{
  "nombre": "Nombre claro",
  "categoria": "ANIMAL",
  "desc": "Descripción corta máximo 15 palabras",
  "historia": "Dos párrafos cortos y reales",
  "stats": [85, 80, 75, 65],
  "evos": ["Tigre", "Leopardo", "Jaguar"]
}

Si es ANIMAL usa stats de Fuerza, Agilidad, Peligro, Rareza. Las evos deben ser solo nombres cortos y del mismo tipo."""
    else:
        return f"""Responde **solo** con un JSON válido sobre "{item_name}":

{{
  "nombre": "{item_name}",
  "categoria": "{category}",
  "desc": "descripción corta",
  "historia": "dos párrafos cortos",
  "stats": [80, 85, 70, 60],
  "evos": ["Nombre1", "Nombre2", "Nombre3"]
}}"""

def parse_json(text):
    try:
        match = re.search(r'(\{.*?\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        pass
    return None

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
                add_log("[1] Optimizando imagen...")
                bytes_opt = resize_image(archivo)
                b64 = base64.b64encode(bytes_opt).decode()
                add_log("[2] Enviando al modelo...")
                
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
                add_log("[3] Respuesta recibida")
                data = parse_json(response.choices[0].message.content)
                
                if data:
                    st.session_state.current_item = data.get("nombre", "León")
                    st.session_state.current_category = data.get("categoria", "ANIMAL")
                    st.session_state.current_data = data
                    add_log(f"[SUCCESS] → {st.session_state.current_item}")
                    st.rerun()
                else:
                    add_log("[ERROR] No se pudo parsear el JSON")
            except Exception as e:
                st.session_state.log.append(f"[ERROR] {str(e)}")
                st.error(f"Error: {str(e)}")

        elif st.session_state.current_item and st.session_state.current_data:
            data = st.session_state.current_data
            labels = get_labels(data.get("categoria", "ANIMAL"))
            stats = data.get("stats", [75, 80, 65, 55])
            variantes = data.get("evos", ["Tigre", "Leopardo", "Jaguar"])[:3]

            with col_img:
                img = generate_image(data.get("nombre", "León"))
                if img:
                    st.image(img, use_container_width=True, caption=data.get("nombre"))
                else:
                    st.image(archivo, use_container_width=True)  # fallback a imagen original

            with col_info:
                st.markdown(f"## {data.get('nombre', 'León')}")
                st.markdown(f"<div class='data-card'><b>Categoría:</b> {data.get('categoria', 'ANIMAL')}</div>", unsafe_allow_html=True)
                
                st.markdown("### 📖 Historia")
                st.markdown(f"<div class='historia-box'>{data.get('historia', 'Historia no disponible.')}</div>", unsafe_allow_html=True)
                
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
                        st.session_state.current_category = data.get("categoria", "ANIMAL")
                        st.session_state.current_data = None
                        st.rerun()

                # Audio
                try:
                    text_audio = f"{data.get('nombre')}. {data.get('desc', '')}. {data.get('historia', '')[:150]}"
                    tts = gTTS(text_audio, lang='es')
                    fp = io.BytesIO()
                    tts.write_to_fp(fp)
                    st.audio(fp)
                except:
                    pass

    st.markdown("</div>", unsafe_allow_html=True)
