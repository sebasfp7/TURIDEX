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
# PASO 1: FILTRO DE REALIDAD (LÓGICA PROGRAMÁTICA)
# ──────────────────────────────────────────────────────────────────────────

def calcular_stats_realistas(nombre, categoria, desc=""):
    """
    SOBREESCRIBE los stats inventados por la IA con valores basados en REGLAS PROGRAMÁTICAS.
    """
    nombre_lower = (nombre + " " + desc).lower()
    cat = str(categoria).upper()
    
    # === CATEGORÍA: COMIDA [Sabor, Picante, Salud, Rareza] ===
    if "COMIDA" in cat:
        sabor, picante, salud, rareza = 65, 15, 50, 35
        
        # Sabor
        if any(x in nombre_lower for x in ["salchipapa", "bandeja paisa", "hamburguesa", "pizza", "sushi", "taco", "brownie"]):
            sabor = random.randint(88, 98)
        
        # Picante
        if any(x in nombre_lower for x in ["habanero", "ghost pepper", "carolina reaper"]):
            picante = 99
        elif any(x in nombre_lower for x in ["ají", "picante", "chile", "jalapeño", "wasabi"]):
            picante = random.randint(70, 90)
        
        # Salud (Evaluación Nutricional Real)
        if any(x in nombre_lower for x in ["ensalada", "fruta", "quinoa", "vapor", "plancha"]):
            salud = random.randint(80, 95)
        elif any(x in nombre_lower for x in ["salchipapa", "frito", "hamburguesa", "pizza", "chatarra"]):
            salud = random.randint(5, 15)
        elif any(x in nombre_lower for x in ["torta", "pastel", "dulce", "azúcar"]):
            salud = random.randint(10, 25)
            
        # Rareza
        if any(x in nombre_lower for x in ["trufa", "kobe", "caviar", "azafrán"]):
            rareza = 95
        elif any(x in nombre_lower for x in ["arroz", "pan", "huevo", "arepa"]):
            rareza = 15
            
        return [sabor, picante, salud, rareza]

    # === CATEGORÍA: ANIMAL [Fuerza, Agilidad, Peligro, Rareza] ===
    elif "ANIMAL" in cat:
        fuerza, agilidad, peligro, rareza = 50, 50, 50, 40
        
        # Depredadores Grandes
        if any(x in nombre_lower for x in ["león", "tigre", "oso", "tiburón", "orca", "jaguar"]):
            fuerza, agilidad, peligro = random.randint(85, 95), random.randint(70, 85), random.randint(90, 100)
        # Insectos/Pequeños
        elif any(x in nombre_lower for x in ["mosca", "mosquito", "hormiga", "abeja"]):
            fuerza = random.randint(1, 5)
            agilidad = random.randint(70, 95)
            peligro = 30 if "abeja" in nombre_lower or "mosquito" in nombre_lower else 5
        # Domésticos
        elif any(x in nombre_lower for x in ["perro", "gato", "hamster", "conejo"]):
            fuerza, peligro = random.randint(20, 40), random.randint(5, 20)
            agilidad = random.randint(60, 85)
            
        return [fuerza, agilidad, peligro, rareza]

    # === CATEGORÍA: LUGAR / ARTE [Historia, Belleza, Cultura, Rareza] ===
    else:
        historia, belleza, cultura, rareza = 60, 70, 60, 50
        
        # Maravillas o Sitios UNESCO
        if any(x in nombre_lower for x in ["machu picchu", "pirámide", "coliseo", "muralla", "torre eiffel", "cartagena"]):
            historia, cultura, rareza = random.randint(90, 100), random.randint(85, 98), random.randint(80, 95)
        # Museos/Arte famoso
        elif any(x in nombre_lower for x in ["louvre", "mona lisa", "guernica", "botero"]):
            historia, belleza, cultura = random.randint(80, 95), random.randint(90, 100), random.randint(90, 100)
            
        return [historia, belleza, cultura, rareza]

# ──────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y SESIÓN
# ──────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="TURIDEX", layout="wide")
SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Inicializar estados
for key in ['current_item', 'current_category', 'current_data', 'last_image_bytes', 
            'original_image', 'current_image', 'current_audio', 'needs_analysis', 
            'source', 'log', 'last_request_time', 'request_count_today']:
    if key not in st.session_state:
        if key == 'log': st.session_state[key] = []
        elif key in ['request_count_today', 'last_request_time']: st.session_state[key] = 0
        elif key == 'needs_analysis': st.session_state[key] = False
        else: st.session_state[key] = None

# Estilos CSS
st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-size: 3.8em; text-align:center; text-shadow: 3px 3px #3B4CCA;}
    .header {background:#000; color:#0F0; padding:12px; border-radius:8px; text-align:center; font-family:monospace;}
    .log-box {background:#111; color:#0F0; padding:5px; border-radius:5px; font-family:monospace; font-size:0.8em; margin:2px 0;}
    .historia-box {background:white; padding:15px; border-radius:10px; border-left: 5px solid #DC0A2D; line-height:1.6;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def add_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.log.append(f"[{timestamp}] {msg}")
    if len(st.session_state.log) > 10: st.session_state.log.pop(0)

def parse_json(text):
    try:
        text = re.sub(r'```json\s*|\s*```', '', text.strip())
        return json.loads(text)
    except:
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match: return json.loads(match.group(1))
    return None

def resize_image(image_file):
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
    img.thumbnail((768, 768))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()

def generate_image(name):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, realistic, high quality, national geographic style')}?width=700&height=500&nologo=true"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200: return Image.open(BytesIO(resp.content))
    except: return None
    return None

# ──────────────────────────────────────────────────────────────────────────
# INTERFAZ Y LÓGICA PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────

with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)
    
    col_img, col_info = st.columns([1, 2])

    with col_img:
        archivo = st.file_uploader("Cargar Imagen del Objetivo", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True)
            if st.button("🔍 ESCANEAR", type="primary", use_container_width=True):
                st.session_state.last_image_bytes = resize_image(archivo)
                st.session_state.original_image = archivo.getvalue()
                st.session_state.needs_analysis = True
                st.session_state.source = "image"
                st.rerun()
        
        for log in st.session_state.log:
            st.markdown(f"<div class='log-box'>{log}</div>", unsafe_allow_html=True)

    with col_info:
        if st.session_state.needs_analysis:
            with st.spinner("Analizando con el filtro de realidad..."):
                try:
                    if st.session_state.source == "image":
                        b64 = base64.b64encode(st.session_state.last_image_bytes).decode()
                        # Paso 1: Visión
                        res_p1 = client.chat.completions.create(
                            messages=[{"role": "user", "content": [
                                {"type": "text", "text": "Describe este objeto con detalle técnico extremo para identificación."},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                            ]}],
                            model="llama-3.2-11b-vision-preview"
                        )
                        desc_v = res_p1.choices[0].message.content
                        
                        # Paso 2: Estructura
                        res_p2 = client.chat.completions.create(
                            messages=[{"role": "user", "content": f"Basado en: {desc_v}, genera un JSON con: nombre, categoria (ANIMAL, COMIDA, LUGAR, ARTE), desc (15 palabras), historia (2 párrafos), stats [0,0,0,0], evos [3 variantes]."}],
                            model=SELECTED_MODEL,
                            temperature=0.1
                        )
                        data = parse_json(res_p2.choices[0].message.content)
                        
                        if data:
                            # 🚨 APLICACIÓN DEL FILTRO DE REALIDAD
                            data["stats"] = calcular_stats_realistas(data["nombre"], data["categoria"], data["desc"])
                            st.session_state.current_data = data
                            st.session_state.current_image = generate_image(data["nombre"])
                            add_log(f"Identificado: {data['nombre']}")
                    
                except Exception as e:
                    st.error(f"Error: {e}")
                st.session_state.needs_analysis = False
                st.rerun()

        if st.session_state.current_data:
            data = st.session_state.current_data
            st.markdown(f"## {data['nombre']}")
            st.markdown(f"**Categoría:** {data['categoria']}")
            
            st.markdown("### 📖 Entrada de Datos")
            st.markdown(f"<div class='historia-box'>{data['historia']}</div>", unsafe_allow_html=True)
            
            # Mostrar Stats
            st.markdown("### 📊 Atributos Reales")
            labels = ["Stat 1", "Stat 2", "Stat 3", "Stat 4"]
            if "ANIMAL" in data["categoria"]: labels = ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
            elif "COMIDA" in data["categoria"]: labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
            else: labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
            
            c1, c2 = st.columns(2)
            for i, label in enumerate(labels):
                with (c1 if i < 2 else c2):
                    val = data["stats"][i]
                    st.write(f"{label}: **{val}%**")
                    st.progress(val/100)

            # Variantes
            st.markdown("### 🔄 Variantes Relacionadas")
            cols = st.columns(3)
            for i, evo in enumerate(data.get("evos", [])[:3]):
                if cols[i].button(evo, use_container_width=True):
                    # Lógica para buscar variante (similar al flujo de imagen pero solo texto)
                    st.session_state.current_item = evo
                    st.session_state.needs_analysis = True
                    st.session_state.source = "text" # Implementar lógica de texto similar
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
