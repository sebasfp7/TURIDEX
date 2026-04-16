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

SELECTED_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.95); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-size: 3.8em; text-align:center; text-shadow: 3px 3px #3B4CCA;}
    .header {background:#000; color:#0F0; padding:12px; border-radius:8px; text-align:center; font-family:monospace;}
    .log-box {background:#111; color:#0F0; padding:6px; border-radius:5px; font-family:monospace; font-size:0.85em; margin:2px 0;}
    .historia-box {background:white; padding:18px; border-radius:10px; border-left: 6px solid #DC0A2D; line-height:1.6; color: #111;}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# FILTRO DE REALIDAD: calcular_stats_realistas
# ──────────────────────────────────────────────────────────────────────────
def calcular_stats_realistas(nombre, categoria, desc=""):
    nombre_lower = (nombre + " " + desc).lower()
    cat = str(categoria).upper()
    
    if "COMIDA" in cat:
        sabor, picante, salud, rareza = 65, 15, 50, 35
        for p in ["salchipapa","bandeja paisa","lechona","hamburguesa","pizza","sushi","ramen","lasaña","taco","ceviche","arepa","empanada","brownie","cheesecake","croissant","churrasco"]:
            if p in nombre_lower: sabor = min(sabor+28,96); break
        
        if any(x in nombre_lower for x in ["habanero","ghost pepper","carolina reaper"]): picante=98
        elif any(x in nombre_lower for x in ["ají","picante","chile","jalapeño","sriracha","curry"]): picante=75
        elif any(x in nombre_lower for x in ["salchipapa","choripapa","hamburguesa","pizza","hot dog"]): picante=8
        else: picante=12
        
        if any(x in nombre_lower for x in ["ensalada","fruta fresca","quinoa","avena","smoothie verde","poke","gazpicho"]): salud=88
        elif any(x in nombre_lower for x in ["grilled","al vapor","pollo a la plancha","pescado al horno"]): salud=68
        elif any(x in nombre_lower for x in ["salchipapa","choripapa","hamburguesa","pizza","perro caliente","papas fritas","nachos","nuggets","bacon","chorizo"]): salud=12
        elif any(x in nombre_lower for x in ["bandeja paisa","lechona","fritada","chicharrón","morcilla"]): salud=20
        return [sabor, picante, salud, rareza]
    
    elif "ANIMAL" in cat:
        fuerza, agilidad, peligro, rareza = 50, 50, 30, 40
        if any(x in nombre_lower for x in ["elefante", "oso", "gorila", "rinoceronte"]): fuerza, peligro = 95, 85
        elif any(x in nombre_lower for x in ["león", "tigre", "tiburón", "cocodrilo"]): fuerza, peligro = 90, 95
        if any(x in nombre_lower for x in ["guepardo", "águila", "halcón"]): agilidad = 98
        if any(x in nombre_lower for x in ["conejo", "vaca", "koala", "tortuga"]): peligro = 5
        if any(x in nombre_lower for x in ["axolotl", "ornitorrinco", "narval"]): rareza = 90
        elif any(x in nombre_lower for x in ["perro", "gato", "paloma"]): rareza = 10
        return [fuerza, agilidad, peligro, rareza]
    
    else: # LUGAR / ARTE / OBJETO
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
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, realistic high quality, clean background')}?width=700&height=500&nologo=true"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200: return Image.open(BytesIO(resp.content))
    except: return None
    return None

# ──────────────────────────────────────────────────────────────────────────
# INTERFAZ Y PROCESAMIENTO
# ──────────────────────────────────────────────────────────────────────────
st.markdown("<h1 class='title'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)
st.markdown(f"<div class='header'>🛰️ NÚCLEO DE IA: {SELECTED_MODEL}</div>", unsafe_allow_html=True)

with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)
    col_img, col_info = st.columns([1, 1.8])

    with col_img:
        archivo = st.file_uploader("Subir Imagen del Objetivo", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True)
            if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
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
            progress = st.status("🚀 Iniciando análisis de Turidex...", expanded=True)
            try:
                # PASO 1: VISIÓN (Llama Vision)
                progress.update(label="👁️ [PASO 1/2] Analizando imagen...", state="running")
                b64_img = base64.b64encode(st.session_state.last_image_bytes).decode()
                res_v = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": "Describe con máximo detalle técnico este objeto, animal o lugar."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]}],
                    model="llama-3.2-11b-vision-preview"
                )
                descripcion_visual = res_v.choices[0].message.content
                add_log("[VISION-OK] Imagen analizada")

                # ══════════════════════════════════════
                # PASO 2: ANALISTA ESTRUCTURADO (EL "CEREBRO")
                # ══════════════════════════════════════
                progress.update(label="🧠 **[PASO 2/2] Consultando base de datos histórica...", state="running")
                add_log("[VISION-P2] Generando ficha TURIDEX estructurada...")
                
                prompt_p2 = f"""Eres TURIDEX, una base de datos enciclopédica experta.

Tienes esta DESCRIPCIÓN TÉCNICA analizada por un perito visual:

─── INICIO DESCRIPCIÓN ───
{descripcion_visual}
─── FIN DESCRIPCIÓN ───

IDENTIFICA el objeto/lugar/animal/comida ESPECÍFICO y genera su ficha.

REGLAS DE IDENTIFICACIÓN ABSOLUTAS:
- NUNCA uses nombres genéricos como "Edificio", "Animal", "Torre", "Comida"
- Si la descripción menciona: reloj + torre + Cartagena/amurallada/Colombia → "Torre del Reloj de Cartagena"
- Si describe: sonrisa enigmática + mujer renacentista + cuadro → "Mona Lisa (La Gioconda)"
- Si describe: felino grande + melena + África/sabana → "León Africano"
- Si describe: papas fritas + salchicha + salsa + calle/colombia → "Salchipapa Costeña"
- Da el NOMBRE PROPIO más específico posible. Si no estás 100% seguro, añade "(posible)"

REGLAS PARA "historia" (MUY IMPORTANTE - mínimo 180 palabras):
- Dos párrafos DENSOS y largos
- Párrafo 1: ORIGEN exacto, quién lo creó/descubrió, cuándo, dónde, cómo
- Párrafo 2: DATOS CURIOSOS reales, importancia cultural, por qué es famoso, variantes
- Incluye: fechas, nombres propios, lugares, datos numéricos reales
- Prohibido: "Es muy conocido", "Es importante", "La gente lo ama" (vago)
- Obligatorio: información documentada que demuestre conocimiento real

REGLAS PARA "evos" (Variantes relacionadas):
- Deben ser 3 variantes REALES o LÓGICAMENTE RELACIONADAS
- Ejemplo Salchipapa: ["Choripapa", "Salchipapa con huevo", "Choripapa mixta"]
- Ejemplo León: ["León Blanco", "León de Montaña", "Leona"]
- Ejemplo Torre del Reloj: ["Puerta del Reloj Santa Catalina", "Baluarte de Santiago", "Arco del Reloj"]
- NUNCA pongas cosas aleatorias sin relación

Responde SOLO con este JSON válido. Sin markdown. Sin texto extra:

{{
  "nombre": "Nombre propio específico",
  "categoria": "ANIMAL / LUGAR / COMIDA / ARTE / OBJETO",
  "desc": "Descripción corta, máximo 15 palabras, precisa y única",
  "historia": "Dos párrafos largos y detallados (mínimo 180 palabras). Origen + datos curiosos reales.",
  "stats": [50, 50, 50, 50],
  "evos": ["VarianteReal1", "VarianteReal2", "VarianteReal3"]
}}
"""
                response_p2 = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt_p2}],
                    model=SELECTED_MODEL,
                    temperature=0.1,
                    max_tokens=2048,
                    timeout=30.0
                )
                
                raw_content = response_p2.choices[0].message.content
                add_log(f"[RAW] {raw_content[:600]}...")
                add_log("[OK] Respuesta recibida")
                
                # ── LIMPIEZA Y PARSEO DEL JSON ──
                raw_content = raw_content.strip()
                if raw_content.startswith("```json"):
                    raw_content = raw_content.replace("```json", "", 1).replace("```", "", 1).strip()
                elif raw_content.startswith("```"):
                    raw_content = raw_content.replace("```", "", 1).replace("```", "", 1).strip()

                add_log(f"[RAW_CLEAN] {raw_content[:400]}...")
                data = parse_json(raw_content)
                
                if data:
                    # 💉 FILTRO DE REALIDAD: Sobreescribimos los stats de la IA
                    data["stats"] = calcular_stats_realistas(
                        data.get("nombre", ""),
                        data.get("categoria", ""),
                        data.get("desc", "")
                    )
                    add_log(f"[STATS] {data['nombre']} → {data['stats']}")
                    
                    st.session_state.current_data = data
                    st.session_state.current_image = generate_image(data.get("nombre"))
                    
                    # Generar Audio
                    try:
                        texto_tts = f"{data['nombre']}. {data['desc']}. {data['historia']}"
                        tts = gTTS(texto_tts, lang='es')
                        af = io.BytesIO()
                        tts.write_to_fp(af)
                        st.session_state.current_audio = af.getvalue()
                    except: pass

                    progress.update(label="✅ **Ficha TURIDEX generada!**", state="complete", expanded=False)
                    add_log(f"[SUCCESS] → {data.get('nombre')}")
                else:
                    add_log("[ERROR] No se pudo parsear el JSON final")
                    progress.update(label="❌ Error generando ficha", state="error")

            except Exception as e:
                add_log(f"[CRITICAL] {str(e)}")
                if 'progress' in locals(): progress.update(label=f"❌ Error: {str(e)[:60]}", state="error")
                st.error(f"Error crítico: {str(e)}")
            finally:
                st.session_state.needs_analysis = False
                st.rerun()

        # RENDERIZAR FICHA
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
            
            st.markdown("### 🔄 Variantes Relacionadas")
            vcols = st.columns(3)
            for idx, evo in enumerate(data.get("evos", [])[:3]):
                vcols[idx].button(evo, key=f"v_{evo}", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
