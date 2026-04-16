import streamlit as st
from groq import Groq
from PIL import Image
import base64
import io
import re
import json
import requests
import time
from io import BytesIO
from gtts import gTTS

st.set_page_config(page_title="TURIDEX", layout="wide")

SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'last_image_bytes' not in st.session_state: st.session_state.last_image_bytes = None
if 'original_image' not in st.session_state: st.session_state.original_image = None
if 'current_image' not in st.session_state: st.session_state.current_image = None
if 'current_audio' not in st.session_state: st.session_state.current_audio = None
if 'needs_analysis' not in st.session_state: st.session_state.needs_analysis = False
if 'source' not in st.session_state: st.session_state.source = None
if 'log' not in st.session_state: st.session_state.log = []
if 'last_request_time' not in st.session_state: st.session_state.last_request_time = 0
if 'request_count_today' not in st.session_state: st.session_state.request_count_today = 0

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
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.log.append(f"[{timestamp}] {msg}")
    if len(st.session_state.log) > 15: st.session_state.log.pop(0)

def rate_limit_check():
    now = time.time()
    if now - st.session_state.last_request_time < 2.5:
        time.sleep(2.5 - (now - st.session_state.last_request_time))
    st.session_state.last_request_time = now
    st.session_state.request_count_today += 1

def resize_image(image_file):
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((768, 768), Image.Resampling.LANCZOS)   # ← Aumentado como pediste
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)  # ← Quality 85
    return buffer.getvalue()

def generate_image(name):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, realistic, high quality, clean background, national geographic style')}"
        resp = requests.get(url + "?width=700&height=500&nologo=true", timeout=10)
        if resp.status_code == 200 and len(resp.content) > 5000:
            return Image.open(BytesIO(resp.content))
    except:
        pass
    return None

def get_prompt(is_image=True, item_name=None, category=None):
    if is_image:
        return """MIRA LA IMAGEN ADJUNTA con máxima atención. IDENTIFICA el objeto, lugar, animal o comida ESPECÍFICO que aparece. 
NO uses nombres genéricos como 'Edificio', 'Torre', 'Puerta', 'Animal', 'Planta' o 'Reloj'. 
Si es un monumento famoso, di SU NOMBRE PROPIO EXACTO (ej: 'Torre del Reloj de Cartagena', 'Puerta de San Felipe', 'Mona Lisa', 'León Blanco'). 
Si no estás 100% seguro del nombre oficial, da la descripción más específica posible en lugar de un nombre genérico. 
NO inventes. Responde **SOLO** con un JSON válido. No uses markdown. No escribas nada antes ni después del JSON.

{
  "nombre": "Nombre propio y específico",
  "categoria": "LUGAR",
  "desc": "Descripción corta máximo 15 palabras",
  "historia": "Dos párrafos largos y detallados (mínimo 180 palabras total) con origen, historia, características y curiosidades",
  "stats": [85, 80, 75, 70],
  "evos": ["NombreEspecífico1", "NombreEspecífico2", "NombreEspecífico3"]
}

Reglas: Para animales imponentes usa stats altos (Fuerza, Agilidad, Peligro >75). Las evos deben ser del mismo tipo."""
    else:
        return f"""Responde **solo** con un JSON válido sobre "{item_name}". No uses markdown. No escribas nada antes ni después.

{{
  "nombre": "{item_name}",
  "categoria": "{category or 'ANIMAL'}",
  "desc": "descripción corta",
  "historia": "dos párrafos extensos y bien documentados",
  "stats": [85, 82, 75, 68],
  "evos": ["Nombre1", "Nombre2", "Nombre3"]
}}"""

def parse_json(text):
    if not text or not isinstance(text, str):
        return None
    text = text.strip()
    text = re.sub(r'```json\s*|\s*```', '', text)
    text = re.sub(r'^.*?(\{.*\})', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'(\{.*\}).*?$', r'\1', text, flags=re.DOTALL)
    try:
        return json.loads(text)
    except:
        try:
            match = re.search(r'(\{.*\})', text, re.DOTALL)
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
                st.session_state.last_image_bytes = resize_image(archivo)
                st.session_state.original_image = archivo.getvalue()
                st.session_state.needs_analysis = True
                st.session_state.source = "image"
                st.session_state.current_item = "Procesando imagen..."
                st.rerun()

    with col_info:
        if st.session_state.get('needs_analysis', False):
            try:
                rate_limit_check = lambda: (time.sleep(max(0, 2.5 - (time.time() - st.session_state.last_request_time))), 
                                          setattr(st.session_state, 'last_request_time', time.time()),
                                          setattr(st.session_state, 'request_count_today', st.session_state.request_count_today + 1))
                rate_limit_check()

                add_log(f"[PIPELINE] Source: {st.session_state.source}")

                if st.session_state.source == "image" and st.session_state.last_image_bytes:
                    b64 = base64.b64encode(st.session_state.last_image_bytes).decode()
                    add_log(f"[B64_LEN] {len(b64)} chars | starts with: {b64[:30]}...")
                    add_log("[VISION] Enviando imagen al modelo Scout...")
                    prompt = get_prompt(is_image=True)
                    response = client.chat.completions.create(
                        messages=[{"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "auto"
                            }}
                        ]}],
                        model=SELECTED_MODEL,
                        temperature=0.1,
                        max_tokens=2048,
                        timeout=30.0
                    )
                else:
                    add_log(f"[TEXT] Analizando variante: {st.session_state.current_item}")
                    prompt = get_prompt(is_image=False, item_name=st.session_state.current_item, 
                                      category=st.session_state.current_category)
                    response = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=SELECTED_MODEL,
                        temperature=0.1,
                        max_tokens=2048,
                        timeout=30.0
                    )

                raw_content = response.choices[0].message.content
                add_log(f"[RAW] {raw_content[:600]}...")
                add_log("[OK] Respuesta recibida")

                data = parse_json(raw_content)
                if data:
                    st.session_state.current_item = data.get("nombre", st.session_state.current_item)
                    st.session_state.current_category = data.get("categoria", "ANIMAL")
                    st.session_state.current_data = data
                    st.session_state.current_image = generate_image(st.session_state.current_item)
                    add_log(f"[SUCCESS] Análisis completado → {st.session_state.current_item}")
                else:
                    add_log("[ERROR] No se pudo parsear el JSON")
                    st.session_state.current_data = None
                    st.session_state.current_item = "Error de análisis"

            except Exception as e:
                add_log(f"[CRITICAL] {str(e)}")
                st.error(f"Error crítico: {str(e)}")
                st.session_state.current_data = None
                st.session_state.current_item = "Error de análisis"
            finally:
                st.session_state.needs_analysis = False
                st.rerun()

        elif st.session_state.current_data:
            data = st.session_state.current_data
            labels = get_labels(data.get("categoria", "ANIMAL"))
            stats = data.get("stats", [80, 80, 75, 65])
            variantes = data.get("evos", ["Tigre", "Leopardo", "Jaguar"])[:3]

            with col_img:
                if st.session_state.current_image:
                    st.image(st.session_state.current_image, use_container_width=True, caption=data.get("nombre"))
                elif st.session_state.get('original_image'):
                    st.image(st.session_state.original_image, use_container_width=True)

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
                        st.session_state.needs_analysis = True
                        st.session_state.source = "text"
                        st.rerun()

                if st.session_state.current_audio is None and data.get('historia'):
                    try:
                        text = f"{data.get('nombre')}. {data.get('desc', '')}. {data.get('historia', '')}"
                        tts = gTTS(text, lang='es')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.session_state.current_audio = fp.getvalue()
                    except:
                        pass
                if st.session_state.current_audio:
                    st.audio(st.session_state.current_audio)

    st.markdown("</div>", unsafe_allow_html=True)
