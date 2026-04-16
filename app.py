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
import random

# ──────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y ESTILOS
# ──────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="TURIDEX", layout="wide")

# MODELO UNIFICADO (Soporta Texto e Imagen)
SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.96); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px; box-shadow: 0 8px 32px rgba(0,0,0,0.3);}
    .title {color: #FFDE00 !important; font-size: 3.8em; text-align:center; text-shadow: 3px 3px #3B4CCA; -webkit-text-stroke: 1px black;}
    .header {background:#000; color:#0F0; padding:12px; border-radius:8px; text-align:center; font-family:monospace; margin-bottom: 15px;}
    .log-box {background:#111; color:#0F0; padding:6px; border-radius:5px; font-family:monospace; font-size:0.85em; margin:2px 0;}
    .historia-box {background:white; padding:20px; border-radius:10px; border-left: 8px solid #DC0A2D; line-height:1.6; color: #111;}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# FILTRO DE REALIDAD (STATS)
# ──────────────────────────────────────────────────────────────────────────
def calcular_stats_realistas(nombre, categoria, desc=""):
    nombre_lower = (nombre + " " + desc).lower()
    cat = str(categoria).upper()
    
    if "COMIDA" in cat:
        sabor, picante, salud, rareza = 65, 15, 50, 35
        for p in ["salchipapa","bandeja paisa","lechona","hamburguesa","pizza","sushi","ramen","lasaña","taco","ceviche","arepa","empanada","brownie"]:
            if p in nombre_lower: sabor = min(sabor+28,96); break
        if any(x in nombre_lower for x in ["habanero","ghost pepper","carolina reaper"]): picante=98
        elif any(x in nombre_lower for x in ["ají","picante","chile","jalapeño","sriracha"]): picante=75
        elif any(x in nombre_lower for x in ["salchipapa","hamburguesa","pizza"]): picante=8
        if any(x in nombre_lower for x in ["ensalada","fruta","quinoa","avena","poke"]): salud=88
        elif any(x in nombre_lower for x in ["salchipapa","hamburguesa","pizza","frito"]): salud=12
        elif any(x in nombre_lower for x in ["bandeja paisa","lechona","chicharrón"]): salud=20
        return [sabor, picante, salud, rareza]
    
    elif "ANIMAL" in cat:
        fuerza, agilidad, peligro, rareza = 50, 50, 30, 40
        if any(x in nombre_lower for x in ["elefante", "oso", "gorila", "rinoceronte"]): fuerza, peligro = 95, 85
        elif any(x in nombre_lower for x in ["león", "tigre", "tiburón", "cocodrilo"]): fuerza, peligro = 90, 95
        if any(x in nombre_lower for x in ["guepardo", "águila", "halcón"]): agilidad = 98
        if any(x in nombre_lower for x in ["conejo", "vaca", "tortuga"]): peligro = 5
        if any(x in nombre_lower for x in ["axolotl", "ornitorrinco", "okapi"]): rareza = 90
        elif any(x in nombre_lower for x in ["perro", "gato", "paloma"]): rareza = 10
        return [fuerza, agilidad, peligro, rareza]
    
    else:
        historia, belleza, cultura, rareza = 60, 60, 50, 45
        iconos = ["eiffel", "coliseo", "machu picchu", "taj mahal", "mona lisa", "reloj", "libertad", "guernica"]
        for i in iconos:
            if i in nombre_lower: historia, belleza, cultura, rareza = 95, 92, 95, 85; break
        return [historia, belleza, cultura, rareza]

# ──────────────────────────────────────────────────────────────────────────
# UTILIDADES Y SISTEMA
# ──────────────────────────────────────────────────────────────────────────
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

if 'log' not in st.session_state: st.session_state.log = []
if 'current_data' not in st.session_state: st.session_state.current_data = None
if 'needs_analysis' not in st.session_state: st.session_state.needs_analysis = False

def add_log(msg):
    st.session_state.log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    if len(st.session_state.log) > 10: st.session_state.log.pop(0)

def parse_json(text):
    try:
        text = re.sub(r'```json\s*|\s*```', '', text.strip())
        return json.loads(text)
    except:
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match: return json.loads(match.group(1))
    return None

def generate_image(name):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, realistic high quality, national geographic style')}?width=700&height=500&nologo=true"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200: return Image.open(BytesIO(resp.content))
    except: return None
    return None

# ──────────────────────────────────────────────────────────────────────────
# INTERFAZ Y PROCESAMIENTO
# ──────────────────────────────────────────────────────────────────────────
st.markdown("<h1 class='title'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='header'>🛰️ NÚCLEO MULTIMODAL ACTIVO: {SELECTED_MODEL}</div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)
    col_img, col_info = st.columns([1, 1.8])

    with col_img:
        archivo = st.file_uploader("Subir evidencia (Imagen)", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True)
            if st.button("🔍 INICIAR ESCANEO", type="primary", use_container_width=True):
                img = Image.open(archivo)
                if img.mode != "RGB": img = img.convert("RGB")
                img.thumbnail((768, 768))
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                st.session_state.last_image_bytes = buf.getvalue()
                st.session_state.needs_analysis = True
                st.rerun()
        
        for log in st.session_state.log:
            st.markdown(f"<div class='log-box'>{log}</div>", unsafe_allow_html=True)

    with col_info:
        if st.session_state.needs_analysis:
            progress = st.status("🚀 Iniciando procesamiento multimodal...", expanded=True)
            try:
                # PASO 1: VISIÓN (Usamos el MISMO modelo Scout)
                progress.update(label="👁️ [PASO 1/2] Analizando imagen con Scout Vision...", state="running")
                b64_img = base64.b64encode(st.session_state.last_image_bytes).decode()
                res_v = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": "Describe con máximo detalle técnico este objeto, animal o lugar. Sé específico sobre colores, formas, texturas y cualquier texto visible."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]}],
                    model=SELECTED_MODEL,
                    temperature=0.2,
                    max_tokens=1024
                )
                descripcion_visual = res_v.choices[0].message.content
                add_log("[VISION-OK] Imagen analizada con Scout")

                # PASO 2: ANALISTA ESTRUCTURADO (EL "CEREBRO")
                progress.update(label="🧠 [PASO 2/2] Consultando base de datos histórica...", state="running")
                add_log("[CEREBRO] Generando ficha técnica...")
                
                prompt_p2 = f"""Eres TURIDEX, base de datos experta. Analiza: {descripcion_visual}
                
                Reglas:
                - Nombre PROPIO específico (ej: "Torre del Reloj de Cartagena").
                - Historia: Mínimo 180 palabras, 2 párrafos densos (Origen + Datos Curiosos reales).
                - JSON válido con: nombre, categoria (ANIMAL, COMIDA, LUGAR, ARTE, OBJETO), desc, historia, stats [50,50,50,50], evos [3 reales].
                - Responde SOLO JSON."""

                response_p2 = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_p2}],
                    model=SELECTED_MODEL,
                    temperature=0.1,
                    max_tokens=2048
                )
                
                raw_content = response_p2.choices[0].message.content
                data = parse_json(raw_content)
                
                if data:
                    # 💉 FILTRO DE REALIDAD
                    data["stats"] = calcular_stats_realistas(data.get("nombre",""), data.get("categoria",""), data.get("desc",""))
                    st.session_state.current_data = data
                    st.session_state.current_image = generate_image(data.get("nombre"))
                    
                    # Audio
                    try:
                        tts = gTTS(f"{data['nombre']}. {data['desc']}. {data['historia']}", lang='es')
                        af = io.BytesIO(); tts.write_to_fp(af)
                        st.session_state.current_audio = af.getvalue()
                    except: pass

                    progress.update(label="✅ Ficha TURIDEX generada!", state="complete", expanded=False)
                    add_log(f"[SUCCESS] → {data.get('nombre')}")
            except Exception as e:
                st.error(f"Error crítico: {e}")
                add_log(f"[ERROR] {str(e)}")
            finally:
                st.session_state.needs_analysis = False
                st.rerun()

        # RENDERIZADO DE RESULTADOS
        if st.session_state.current_data:
            data = st.session_state.current_data
            st.markdown(f"## 💠 {data['nombre']}")
            st.info(f"**Categoría:** {data['categoria']} | {data['desc']}")
            
            if st.session_state.get('current_image'):
                st.image(st.session_state.current_image, use_container_width=True)
            
            st.markdown("### 📜 Registros Históricos")
            st.markdown(f"<div class='historia-box'>{data['historia']}</div>", unsafe_allow_html=True)
            
            if st.session_state.get('current_audio'):
                st.audio(st.session_state.current_audio)

            st.markdown("### 📊 Atributos de Realidad")
            cat = data['categoria'].upper()
            labels = ["Stat 1", "Stat 2", "Stat 3", "Stat 4"]
            if "ANIMAL" in cat: labels = ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
            elif "COMIDA" in cat: labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
            else: labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
            
            c1, c2 = st.columns(2)
            for i, label in enumerate(labels):
                with (c1 if i < 2 else c2):
                    val = data['stats'][i]
                    st.write(f"{label}: **{val}%**")
                    st.progress(val/100)
            
            st.markdown("### 🔄 Variantes Relacionadas")
            vcols = st.columns(3)
            for idx, evo in enumerate(data.get("evos", [])[:3]):
                vcols[idx].button(evo, key=f"v_{evo}", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
