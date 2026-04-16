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

# ====================== CONFIGURACIÓN DE MODELOS ======================
MODELS = {
    "vision": "meta-llama/llama-4-scout-17b-16e-instruct",
    "text": "llama-3.3-70b-versatile",
    "fallback": "llama3-70b-8192"
}

if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'current_image' not in st.session_state: st.session_state.current_image = None
if 'current_audio' not in st.session_state: st.session_state.current_audio = None
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
st.markdown(f"<div class='header'>📡 MODELO ACTIVO: {MODELS['vision']}</div>", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def add_log(msg):
    st.session_state.log.append(msg)
    if len(st.session_state.log) > 12: st.session_state.log.pop(0)

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
        resp = requests.get(url + "?width=700&height=500&nologo=true", timeout=12)
        if resp.status_code == 200:
            return Image.open(BytesIO(resp.content))
    except:
        pass
    return None

def get_prompt(is_image=True, item_name=None, category=None):
    if is_image:
        return """Analiza la imagen y responde **SOLO** con un JSON válido. La historia debe ser larga y detallada (mínimo 180 palabras en total).

{
  "nombre": "Nombre claro",
  "categoria": "ANIMAL",
  "desc": "Descripción corta máximo 15 palabras",
  "historia": "Dos párrafos extensos con origen, hábitat, comportamiento, curiosidades e importancia cultural",
  "stats": [88, 85, 78, 65],
  "evos": ["Tigre", "Leopardo", "Jaguar"]
}

Reglas: Para animales imponentes como leones, stats deben ser altos (Fuerza, Agilidad y Peligro >70)."""
    else:
        return f"""Responde **solo** con un JSON válido y detallado sobre "{item_name}":

{{
  "nombre": "{item_name}",
  "categoria": "{category or 'ANIMAL'}",
  "desc": "descripción corta",
  "historia": "dos párrafos extensos y bien documentados",
  "stats": [85, 82, 75, 68],
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

def get_labels(category):
    cat = str(category).upper()
    if "ANIMAL" in cat: return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif any(x in cat for x in ["LUGAR", "ARTE", "PERSONA"]): return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else: return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

def process_item(item_name, category=None, image_b64=None):
    try:
        prompt = get_prompt(is_image=bool(image_b64), item_name=item_name, category=category)
        if image_b64:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]}],
                model=MODELS["vision"],
                temperature=0.1,
                max_tokens=1200
            )
        else:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=MODELS["text"],
                temperature=0.1,
                max_tokens=1000
            )
        data = parse_json(response.choices[0].message.content)
        if data:
            return data
        return None
    except Exception as e:
        add_log(f"[ERROR] {str(e)}")
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
                bytes_opt = resize_image(archivo)
                b64 = base64.b64encode(bytes_opt).decode()
                st.session_state.current_item = "Procesando imagen..."
                st.session_state.current_data = None
                data = process_item("imagen_cargada", image_b64=b64)
                if data:
                    st.session_state.current_item = data.get("nombre", "León")
                    st.session_state.current_category = data.get("categoria", "ANIMAL")
                    st.session_state.current_data = data
                    st.session_state.current_image = generate_image(st.session_state.current_item)
                    add_log(f"[SUCCESS] Análisis completado → {st.session_state.current_item}")
                st.rerun()

    with col_info:
        if st.session_state.current_data:
            data = st.session_state.current_data
            labels = get_labels(data.get("categoria", "ANIMAL"))
            stats = data.get("stats", [80, 80, 75, 65])
            variantes = data.get("evos", ["Tigre", "Leopardo", "Jaguar"])[:3]

            with col_img:
                if st.session_state.current_image:
                    st.image(st.session_state.current_image, use_container_width=True, caption=data.get("nombre"))
                elif archivo:
                    st.image(archivo, use_container_width=True)

            with col_info:
                st.markdown(f"## {data.get('nombre', 'León')}")
                st.markdown(f"<div class='data-card'><b>Categoría:</b> {data.get('categoria', 'ANIMAL')}</div>", unsafe_allow_html=True)
                
                st.markdown("### 📖 Historia")
                st.markdown(f"<div class='historia-box'>{data.get('historia', 'Sin historia disponible.')}</div>", unsafe_allow_html=True)
                
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
                        add_log(f"[VARIANT] Cargando {var}...")
                        st.session_state.current_item = var
                        st.session_state.current_category = data.get("categoria", "ANIMAL")
                        st.session_state.current_data = None
                        st.session_state.current_image = None
                        st.session_state.current_audio = None
                        st.rerun()

                # Audio (caché)
                if st.session_state.current_audio is None:
                    try:
                        text = f"{data.get('nombre')}. {data.get('desc', '')}. {data.get('historia', '')}"
                        tts = gTTS(text, lang='es')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.session_state.current_audio = fp.getvalue()
                    except:
                        st.session_state.current_audio = b''
                if st.session_state.current_audio:
                    st.audio(st.session_state.current_audio)

    st.markdown("</div>", unsafe_allow_html=True)
