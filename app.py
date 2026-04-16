import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re
import requests
from io import BytesIO

st.set_page_config(page_title="TURIDEX", layout="wide")

if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'historial' not in st.session_state: st.session_state.historial = []

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-family: 'Courier New', monospace; font-size: 3.8em;
            text-shadow: 0 0 20px #FFDE00, 0 0 35px #FF0000;}
    .current-header {background: #000000; color: #00FF41; padding: 15px; border-radius: 10px;
                     text-align: center; font-size: 1.6em; font-weight: bold; margin-bottom: 15px;}
    .data-card, .historia-box {background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
                               padding: 18px; border-radius: 10px; margin: 12px 0;}
    .variant-btn {background: linear-gradient(135deg, #FFCC00, #FFEB3B) !important; color: black !important;
                  font-weight: bold !important; border: 3px solid black !important; border-radius: 15px !important;
                  padding: 14px !important; margin: 6px 0 !important;}
    .variant-btn:hover {transform: translateY(-4px);}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title' style='text-align:center'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Falta GROQ_API_KEY")

def clean_text(text):
    text = re.sub(r'[*#_\[\]]|Variante\d+:|Variante :', '', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()

def extract(tag, text):
    match = re.search(rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)", text, re.S | re.I)
    return clean_text(match.group(1)) if match else ""

def clean_variants(evos_text):
    """Limpieza agresiva de variantes"""
    items = re.split(r',|•|\n', evos_text)
    clean = []
    for item in items:
        item = re.sub(r'^.*?:', '', item).strip()  # Quita "Variante1:"
        item = re.sub(r'\..*', '', item).strip()   # Quita texto largo
        if item and len(item) > 2 and not any(bad in item.lower() for bad in ['la gioconda', 'ha sido', 'es considerada']):
            clean.append(item[:25])  # Limitar longitud
    return clean[:3]

def generate_image(name):
    try:
        prompt = f"{name}, high quality, clean background, encyclopedia style, no text, professional"
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=800&height=600&nologo=true&seed=42"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            return PIL.Image.open(BytesIO(resp.content))
    except:
        pass
    return None

def get_prompt(item_name=None, inherited_category=None):
    cat = inherited_category or "COMIDA"
    return f"""Eres TURIDEX. Responde **SIEMPRE** con el formato exacto. No añadas texto extra, explicaciones ni "Variante1:".

ELEMENTO: {item_name}
CATEGORÍA CONFIRMADA: {cat}

REGLAS ESTRICTAS:
- Si la categoría es ANIMAL → Stats: Fuerza, Agilidad, Peligro, Rareza
- Si la categoría es COMIDA → Stats: Sabor, Picante, Salud, Rareza
- Si la categoría es LUGAR o ARTE → Stats: Historia, Belleza, Cultura, Rareza

**EVOS DEBEN SER SOLO 3 NOMBRES CORTOS** (máximo 3 palabras cada uno). Ejemplos correctos:
- Para La Gioconda → Leonardo da Vinci, Venus de Milo, El Grito
- Para León → Tigre, Jaguar, Pantera

FORMATO OBLIGATORIO (copia exactamente):

NOMBRE: {item_name}
CATEGORIA: {cat}
DESC: [máximo 12 palabras]
HISTORIA: [Dos párrafos cortos]
STATS: [45, 65, 80, 75]
EVOS: [Nombre1, Nombre2, Nombre3]

Analiza ahora."""

def get_labels(category):
    category = str(category).upper()
    if "ANIMAL" in category:
        return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif any(x in category for x in ["LUGAR", "ARTE", "PERSONA"]):
        return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else:
        return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

# ====================== FLUJO ======================
with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)

    if st.button("🔄 Reiniciar TURIDEX"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    if st.session_state.current_item:
        st.markdown(f"<div class='current-header'>📍 ANALIZANDO: {st.session_state.current_item}</div>", unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 2])

    if st.session_state.current_item and st.session_state.current_category:
        item = st.session_state.current_item
        cat = st.session_state.current_category

        with st.spinner(f"Procesando {item}..."):
            try:
                prompt = get_prompt(item, cat)
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.05,
                    max_tokens=1000
                )
                res = response.choices[0].message.content

                nombre = extract("NOMBRE", res) or item
                categoria = extract("CATEGORIA", res).upper() or cat
                desc = extract("DESC", res)
                historia = extract("HISTORIA", res)
                stats_raw = extract("STATS", res)
                evos_raw = extract("EVOS", res)

                nums = [min(100, max(10, int(n))) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: nums.append(60)

                variantes = clean_variants(evos_raw)

                if nombre not in st.session_state.historial:
                    st.session_state.historial.append(nombre)
                st.session_state.current_category = categoria

                with col_img:
                    st.write(f"**Visualización de {nombre}**")
                    img = generate_image(nombre)
                    if img:
                        st.image(img, use_container_width=True)
                    else:
                        st.error("⚠️ No se pudo generar la imagen")
                        st.info("La API de imágenes está inestable. Prueba con otra variante.")

                with col_info:
                    st.markdown(f"## {nombre}")
                    st.markdown(f"<div class='data-card'><b>Categoría:</b> {categoria}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-card'>{desc}</div>", unsafe_allow_html=True)
                    
                    st.markdown("### 📖 Historia")
                    st.markdown(f"<div class='historia-box'>{historia}</div>", unsafe_allow_html=True)
                    
                    labels = get_labels(categoria)
                    
                    st.markdown("### 📊 Puntos Base")
                    c1, c2 = st.columns(2)
                    with c1:
                        for i in range(2):
                            st.write(f"{labels[i]}: **{nums[i]}%**")
                            st.progress(nums[i]/100)
                    with c2:
                        for i in range(2,4):
                            st.write(f"{labels[i]}: **{nums[i]}%**")
                            st.progress(nums[i]/100)
                    
                    st.markdown("### 🔄 Variantes")
                    for var in variantes:
                        if st.button(var, key=f"btn_{var}", use_container_width=True):
                            st.session_state.current_item = var
                            st.session_state.current_category = categoria
                            st.rerun()

            except Exception as e:
                st.error(f"Error: {e}")

    else:
        with col_img:
            archivo = st.file_uploader("Carga una imagen", type=["jpg","png","jpeg"])
            if archivo:
                st.image(archivo, use_container_width=True)
                if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                    st.session_state.current_item = "Procesando imagen..."
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
