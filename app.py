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
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ──────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="TURIDEX", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; 
        background-attachment: fixed;
    }
    .frame {
        background: rgba(255,255,255,0.92); 
        backdrop-filter: blur(12px);
        border: 4px solid #DC0A2D; 
        border-radius: 20px; 
        padding: 25px;
    }
    .title {color: #FFDE00 !important; font-size: 3.8em; text-align:center; text-shadow: 3px 3px #3B4CCA;}
    .header {background:#000; color:#0F0; padding:12px; border-radius:8px; text-align:center; font-family:monospace; margin-bottom: 20px;}
    .log-box {background:#111; color:#0F0; padding:6px; border-radius:5px; font-family:monospace; font-size:0.85em; margin:3px 0;}
    .data-card, .historia-box {background:rgba(255,255,255,0.95); padding:18px; border-radius:10px; margin:12px 0; border-left: 6px solid #DC0A2D;}
    .variant-btn {background:linear-gradient(135deg,#FFCC00,#FFEB3B) !important; color:black !important; font-weight:bold !important; border:2px solid black !important;}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# LÓGICA DEL FILTRO DE REALIDAD (STATS PROGRAMÁTICOS)
# ──────────────────────────────────────────────────────────────────────────
def calcular_stats_realistas(nombre, categoria, desc=""):
    nombre_lower = (nombre + " " + desc).lower()
    cat = str(categoria).upper()
    
    # === CATEGORÍA: COMIDA [Sabor, Picante, Salud, Rareza] ===
    if "COMIDA" in cat:
        sabor, picante, salud, rareza = 65, 10, 50, 30
        if any(x in nombre_lower for x in ["salchipapa", "hamburguesa", "pizza", "sushi", "bandeja paisa", "taco", "postre"]):
            sabor = random.randint(85, 98)
        if any(x in nombre_lower for x in ["ají", "picante", "chile", "habanero", "wasabi"]):
            picante = random.randint(75, 99)
        if any(x in nombre_lower for x in ["ensalada", "fruta", "quinoa", "vapor", "poke"]):
            salud = random.randint(80, 95)
        elif any(x in nombre_lower for x in ["salchipapa", "frito", "hamburguesa", "pizza", "donut", "gaseosa"]):
            salud = random.randint(5, 18)
        if any(x in nombre_lower for x in ["trufa", "kobe", "caviar"]): rareza = 95
        elif any(x in nombre_lower for x in ["hamburguesa", "perro caliente", "arroz"]): rareza = 15
        return [sabor, picante, salud, rareza]

    # === CATEGORÍA: ANIMAL [Fuerza, Agilidad, Peligro, Rareza] ===
    elif "ANIMAL" in cat:
        fuerza, agilidad, peligro, rareza = 50, 50, 30, 40
        if any(x in nombre_lower for x in ["elefante", "rinoceronte", "oso", "gorila"]): 
            fuerza, peligro = random.randint(90, 98), random.randint(70, 85)
        elif any(x in nombre_lower for x in ["león", "tigre", "tiburón", "cocodrilo", "jaguar"]): 
            fuerza, peligro = random.randint(85, 95), random.randint(90, 100)
        if any(x in nombre_lower for x in ["guepardo", "águila", "halcón", "colibrí"]): agilidad = 98
        if any(x in nombre_lower for x in ["conejo", "hamster", "vaca", "tortuga", "koala"]): peligro = 5
        if any(x in nombre_lower for x in ["axolotl", "ornitorrinco", "narval"]): rareza = 90
        elif any(x in nombre_lower for x in ["perro", "gato", "paloma"]): rareza = 10
        return [fuerza, agilidad, peligro, rareza]

    # === CATEGORÍA: LUGAR / ARTE [Historia, Belleza, Cultura, Rareza] ===
    else:
        historia, belleza, cultura, rareza = 60, 65, 60, 45
        iconos = ["eiffel", "coliseo", "machu picchu", "taj mahal", "mona lisa", "reloj", "libertad", "guernica", "pirámide"]
        for i in iconos:
            if i in nombre_lower:
                historia, belleza, cultura, rareza = 96, 94, 95, 88
                break
        if any(x in nombre_lower for x in ["parque", "plaza", "calle", "centro comercial", "casa"]):
            rareza, belleza = 15, 45
        return [historia, belleza, cultura, rareza]

# ──────────────────────────────────────────────────────────────────────────
# UTILIDADES Y ESTADO DE SESIÓN
# ──────────────────────────────────────────────────────────────────────────
SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

for key in ['current_item', 'current_category', 'current_data', 'last_image_bytes', 
            'original_image', 'current_image', 'current_audio', 'needs_analysis', 
            'source', 'log', 'last_request_time']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'log' else None

def add_log(msg):
    st.session_state.log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    if len(st.session_state.log) > 12: st.session_state.log.pop(0)

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
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, realistic, high quality, national geographic style')}?width=700&height=500&nologo=true"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200: return Image.open(BytesIO(resp.content))
    except: return None
    return None

# ──────────────────────────────────────────────────────────────────────────
# INTERFAZ PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────
st.markdown("<h1 class='title'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='header'>📡 SISTEMA ACTIVO | MODELO: {SELECTED_MODEL}</div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)
    
    col_img, col_info = st.columns([1, 2])

    with col_img:
        archivo = st.file_uploader("Cargar Imagen del Objetivo", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True, caption="Objetivo detectado")
            if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                img = Image.open(archivo)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.thumbnail((768, 768))
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                st.session_state.last_image_bytes = buf.getvalue()
                st.session_state.original_image = archivo.getvalue()
                st.session_state.needs_analysis = True
                st.session_state.source = "image"
                st.rerun()
        
        st.markdown("---")
        for log in st.session_state.log:
            st.markdown(f"<div class='log-box'>{log}</div>", unsafe_allow_html=True)

    with col_info:
        # LÓGICA DE PROCESAMIENTO
        if st.session_state.get('needs_analysis'):
            with st.spinner("⚡ Procesando con Filtro de Realidad..."):
                try:
                    if st.session_state.source == "image":
                        b64 = base64.b64encode(st.session_state.last_image_bytes).decode()
                        # Paso 1: Descripción Visual
                        res_v = client.chat.completions.create(
                            messages=[{"role": "user", "content": [{"type": "text", "text": "Describe este objeto/lugar con detalle técnico extremo."},
                                                                   {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}],
                            model="llama-3.2-11b-vision-preview"
                        )
                        desc_tecnica = res_v.choices[0].message.content
                        add_log("Descripción visual completada")

                        # Paso 2: Ficha Estructurada
                        prompt_f = f"Basado en: {desc_tecnica}, genera un JSON con: nombre, categoria (ANIMAL, COMIDA, LUGAR, ARTE), desc (15 palabras), historia (2 párrafos), stats [0,0,0,0], evos [3 variantes reales]."
                        res_f = client.chat.completions.create(messages=[{"role": "user", "content": prompt_f}], model=SELECTED_MODEL, temperature=0.1)
                        data = parse_json(res_f.choices[0].message.content)
                    else:
                        # Para variantes de texto
                        prompt_t = f"Genera ficha TURIDEX JSON para: {st.session_state.current_item}. categoria: {st.session_state.current_category}. stats [0,0,0,0]."
                        res_t = client.chat.completions.create(messages=[{"role": "user", "content": prompt_t}], model=SELECTED_MODEL)
                        data = parse_json(res_t.choices[0].message.content)

                    if data:
                        # 💉 INYECCIÓN DEL FILTRO DE REALIDAD
                        data["stats"] = calcular_stats_realistas(data.get("nombre",""), data.get("categoria",""), data.get("desc",""))
                        st.session_state.current_data = data
                        st.session_state.current_image = generate_image(data["nombre"])
                        add_log(f"Ficha generada: {data['nombre']}")
                        
                        # Generar Audio
                        text_audio = f"{data['nombre']}. {data['desc']}. {data['historia']}"
                        tts = gTTS(text_audio, lang='es')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.session_state.current_audio = fp.getvalue()
                except Exception as e:
                    st.error(f"Error en escaneo: {e}")
                    add_log(f"Error: {str(e)}")
                
                st.session_state.needs_analysis = False
                st.rerun()

        # MOSTRAR RESULTADOS
        if st.session_state.current_data:
            data = st.session_state.current_data
            st.markdown(f"## {data['nombre']}")
            st.markdown(f"<div class='data-card'><b>Categoría:</b> {data['categoria']} <br> <i>{data['desc']}</i></div>", unsafe_allow_html=True)
            
            if st.session_state.current_image:
                st.image(st.session_state.current_image, use_container_width=True)
            
            st.markdown("### 📖 Historia y Datos")
            st.markdown(f"<div class='historia-box'>{data['historia']}</div>", unsafe_allow_html=True)
            
            if st.session_state.current_audio:
                st.audio(st.session_state.current_audio)

            # Barras de Stats
            st.markdown("### 📊 Puntos Base Reales")
            cat = data['categoria'].upper()
            if "ANIMAL" in cat: labels = ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
            elif "COMIDA" in cat: labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
            else: labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
            
            c1, c2 = st.columns(2)
            for i, label in enumerate(labels):
                with (c1 if i < 2 else c2):
                    val = data['stats'][i]
                    st.write(f"{label}: **{val}%**")
                    st.progress(val/100)
            
            st.markdown("### 🔄 Variantes Detectadas")
            cols = st.columns(3)
            for i, var in enumerate(data.get("evos", [])[:3]):
                if cols[i].button(var, key=f"btn_{var}", use_container_width=True):
                    st.session_state.current_item = var
                    st.session_state.current_category = data['categoria']
                    st.session_state.source = "text"
                    st.session_state.needs_analysis = True
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
