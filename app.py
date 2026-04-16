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

# El modelo específico solicitado
SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-attachment: fixed;
    }
    .frame {
        background: rgba(255,255,255,0.94); backdrop-filter: blur(10px);
        border: 5px solid #DC0A2D; border-radius: 20px; padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    .title {color: #FFDE00 !important; font-size: 3.8em; text-align:center; text-shadow: 4px 4px #3B4CCA; -webkit-text-stroke: 1px black;}
    .header {background:#000; color:#0F0; padding:12px; border-radius:8px; text-align:center; font-family:monospace; margin-bottom: 20px;}
    .log-box {background:#111; color:#0F0; padding:6px; border-radius:5px; font-family:monospace; font-size:0.85em; margin:2px 0; border: 1px solid #333;}
    .historia-box {background:white; padding:20px; border-radius:10px; border-left: 8px solid #DC0A2D; line-height:1.6; font-size: 1.1em; color: #111;}
    .stProgress > div > div > div > div { background-color: #DC0A2D; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# FILTRO DE REALIDAD (STATS PROGRAMÁTICOS)
# ──────────────────────────────────────────────────────────────────────────
def calcular_stats_realistas(nombre, categoria, desc=""):
    """Sobreescribe los stats de la IA con valores lógicos humanos"""
    nombre_lower = (nombre + " " + desc).lower()
    cat = str(categoria).upper()
    
    # === CATEGORÍA: COMIDA [Sabor, Picante, Salud, Rareza] ===
    if "COMIDA" in cat:
        sabor, picante, salud, rareza = 65, 12, 50, 30
        if any(x in nombre_lower for x in ["salchipapa", "hamburguesa", "pizza", "sushi", "bandeja paisa", "taco", "lechona", "empanada"]):
            sabor = random.randint(88, 98)
        if any(x in nombre_lower for x in ["ají", "picante", "chile", "habanero", "jalapeño", "sriracha"]):
            picante = 95 if "habanero" in nombre_lower else 75
        if any(x in nombre_lower for x in ["ensalada", "fruta", "quinoa", "avena", "smoothie", "vapor"]):
            salud = random.randint(85, 96)
        elif any(x in nombre_lower for x in ["salchipapa", "frito", "hamburguesa", "pizza", "donas", "gaseosa", "chorizo"]):
            salud = random.randint(5, 18)
        if any(x in nombre_lower for x in ["trufa", "kobe", "caviar", "azafrán"]): rareza = 95
        elif any(x in nombre_lower for x in ["pan", "arroz", "huevo", "arepa"]): rareza = 15
        return [sabor, picante, salud, rareza]

    # === CATEGORÍA: ANIMAL [Fuerza, Agilidad, Peligro, Rareza] ===
    elif "ANIMAL" in cat:
        fuerza, agilidad, peligro, rareza = 50, 50, 30, 40
        if any(x in nombre_lower for x in ["elefante", "rinoceronte", "hipopótamo", "oso", "gorila"]): 
            fuerza, peligro = random.randint(92, 99), random.randint(75, 90)
        elif any(x in nombre_lower for x in ["león", "tigre", "tiburón", "cocodrilo", "jaguar", "lobo"]): 
            fuerza, peligro = random.randint(85, 96), random.randint(92, 100)
        if any(x in nombre_lower for x in ["guepardo", "águila", "halcón", "colibrí", "lebrel"]): agilidad = 98
        if any(x in nombre_lower for x in ["conejo", "hamster", "vaca", "oveja", "tortuga", "koala", "panda"]): peligro = 5
        if any(x in nombre_lower for x in ["axolotl", "ornitorrinco", "okapi", "narval", "tardígrado"]): rareza = 92
        elif any(x in nombre_lower for x in ["perro", "gato", "paloma", "mosca", "rata"]): rareza = 10
        return [fuerza, agilidad, peligro, rareza]

    # === CATEGORÍA: LUGAR / ARTE / OTROS [Historia, Belleza, Cultura, Rareza] ===
    else:
        historia, belleza, cultura, rareza = 60, 65, 60, 45
        iconos = ["eiffel", "coliseo", "machu picchu", "taj mahal", "mona lisa", "reloj", "libertad", "guernica", "pirámide", "cartagena"]
        for i in iconos:
            if i in nombre_lower:
                historia, belleza, cultura, rareza = 98, 95, 96, 90
                break
        if any(x in nombre_lower for x in ["parque", "plaza", "calle", "tienda", "casa"]):
            rareza, belleza = 18, 40
        return [historia, belleza, cultura, rareza]

# ──────────────────────────────────────────────────────────────────────────
# LÓGICA DE SISTEMA
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
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, realistic high quality, national geographic style')}?width=800&height=600&nologo=true"
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200: return Image.open(BytesIO(resp.content))
    except: return None
    return None

# ──────────────────────────────────────────────────────────────────────────
# INTERFAZ DE USUARIO
# ──────────────────────────────────────────────────────────────────────────
st.markdown("<h1 class='title'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='header'>📡 CONECTADO AL NÚCLEO: {SELECTED_MODEL}</div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)
    
    col_img, col_info = st.columns([1, 1.8])

    with col_img:
        archivo = st.file_uploader("Subir evidencia (Imagen)", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True)
            if st.button("🔍 INICIAR ESCANEO", type="primary", use_container_width=True):
                # Preparar imagen
                img = Image.open(archivo)
                if img.mode != "RGB": img = img.convert("RGB")
                img.thumbnail((700, 700))
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                st.session_state.last_image_bytes = buf.getvalue()
                st.session_state.needs_analysis = True
                st.session_state.source = "image"
                st.rerun()
        
        st.markdown("---")
        for log in st.session_state.log:
            st.markdown(f"<div class='log-box'>{log}</div>", unsafe_allow_html=True)

    with col_info:
        if st.session_state.get('needs_analysis'):
            with st.spinner("🌀 Analizando estructura molecular..."):
                try:
                    # 1. Descripción visual (usando Llama Vision)
                    b64_img = base64.b64encode(st.session_state.last_image_bytes).decode()
                    res_v = client.chat.completions.create(
                        messages=[{"role": "user", "content": [
                            {"type": "text", "text": "Identifica este objeto/lugar/animal con precisión técnica."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                        ]}],
                        model="llama-3.2-11b-vision-preview"
                    )
                    descripcion = res_v.choices[0].message.content
                    add_log("Visión completada")

                    # 2. Generación de Ficha (Usando el modelo pedido: llama-4-scout)
                    prompt = f"""Basado en esta descripción: {descripcion}. 
                    Genera un JSON estrictamente válido:
                    {{
                        "nombre": "Nombre específico",
                        "categoria": "ANIMAL, COMIDA, LUGAR o ARTE",
                        "desc": "Máximo 15 palabras",
                        "historia": "Dos párrafos educativos y extensos sobre origen e importancia.",
                        "stats": [0,0,0,0],
                        "evos": ["Variante1", "Variante2", "Variante3"]
                    }}"""
                    
                    res_f = client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model=SELECTED_MODEL,
                        temperature=0.1
                    )
                    data = parse_json(res_f.choices[0].message.content)

                    if data:
                        # 💉 FILTRO DE REALIDAD
                        data["stats"] = calcular_stats_realistas(data["nombre"], data["categoria"], data["desc"])
                        st.session_state.current_data = data
                        st.session_state.current_image = generate_image(data["nombre"])
                        
                        # Audio TTS
                        try:
                            texto_tts = f"{data['nombre']}. {data['desc']}. {data['historia']}"
                            tts = gTTS(texto_tts, lang='es')
                            af = io.BytesIO()
                            tts.write_to_fp(af)
                            st.session_state.current_audio = af.getvalue()
                        except: st.session_state.current_audio = None
                        
                        add_log(f"Objetivo: {data['nombre']}")

                except Exception as e:
                    st.error(f"Error en el sistema: {e}")
                
                st.session_state.needs_analysis = False
                st.rerun()

        # Renderizar la ficha si existe
        if st.session_state.current_data:
            data = st.session_state.current_data
            st.markdown(f"## 💠 {data['nombre']}")
            st.info(f"**Categoría:** {data['categoria']} | {data['desc']}")
            
            if st.session_state.current_image:
                st.image(st.session_state.current_image, use_container_width=True)
            
            st.markdown("### 📜 Registros Históricos")
            st.markdown(f"<div class='historia-box'>{data['historia']}</div>", unsafe_allow_html=True)
            
            if st.session_state.get('current_audio'):
                st.audio(st.session_state.current_audio)

            # Estadísticas
            st.markdown("### 📊 Atributos de Realidad")
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
            
            # Variantes (Botones)
            st.markdown("### 🔄 Variantes Relacionadas")
            vcols = st.columns(3)
            for idx, evo in enumerate(data.get("evos", [])[:3]):
                if vcols[idx].button(evo, key=f"v_{idx}", use_container_width=True):
                    add_log(f"Cargando variante: {evo}")
                    st.session_state.current_item = evo
                    # (Aquí se podría disparar una búsqueda por texto similar)
                    st.toast(f"Buscando datos de {evo}...")

    st.markdown("</div>", unsafe_allow_html=True)
