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

# ====================== SESSION STATE ======================
if 'current_item' not in st.session_state:
    st.session_state.current_item = None
if 'current_category' not in st.session_state:
    st.session_state.current_category = None
if 'historial' not in st.session_state:
    st.session_state.historial = []
if 'last_image' not in st.session_state:
    st.session_state.last_image = None

# ====================== ESTILOS ======================
st.markdown("""
<style>
    .stApp { background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
             background-size: cover; background-attachment: fixed; }
    .frame {
        background: rgba(255,255,255,0.88);
        backdrop-filter: blur(12px);
        border: 4px solid #DC0A2D;
        border-radius: 20px;
        padding: 25px;
    }
    .title-box {
        background-color: #000000;
        border: 4px solid #DC0A2D;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin-bottom: 15px;
    }
    .title {
        color: #FFDE00 !important;
        font-family: 'Courier New', monospace;
        font-size: 3.6em;
        text-shadow: 0 0 15px #FFDE00, 0 0 25px #FF0000;
        animation: glow 2s infinite alternate;
    }
    @keyframes glow { from {text-shadow: 0 0 10px #FFDE00;} to {text-shadow: 0 0 25px #FFDE00, 0 0 35px #FF0000;} }
    
    .breadcrumb {
        background: rgba(0,0,0,0.8); color: #00FF00; padding: 10px; border-radius: 8px;
        font-family: 'Courier New', monospace; text-align: center; margin-bottom: 15px;
    }
    .variant-btn {
        background: linear-gradient(135deg, #FFCC00, #FFEB3B) !important;
        color: black !important;
        font-weight: bold !important;
        border: 3px solid black !important;
        border-radius: 15px !important;
        padding: 12px !important;
        margin: 6px 0 !important;
        transition: all 0.3s;
    }
    .variant-btn:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 15px rgba(220,10,45,0.6) !important;
        background: linear-gradient(135deg, #FFD700, #FF9800) !important;
    }
    .data-card, .historia-box {
        background: rgba(255,255,255,0.95);
        backdrop-filter: blur(8px);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title-box'><h1 class='title'>⚡ TURIDEX ⚡</h1></div>", unsafe_allow_html=True)

if st.session_state.historial:
    st.markdown(f"<div class='breadcrumb'>📍 {' → '.join(st.session_state.historial)}</div>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Falta la GROQ_API_KEY en secrets.toml")

# ====================== FUNCIONES ======================
def encode_image(file):
    return base64.b64encode(file.getvalue()).decode()

def clean_text(text):
    text = re.sub(r'[*#_\[\]]', '', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()

def extract(tag, text):
    match = re.search(rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)", text, re.S | re.I)
    return clean_text(match.group(1)) if match else "No disponible"

def generate_image(name, category):
    try:
        style = {
            "COMIDA": "professional food photography, studio lighting, clean background",
            "ANIMAL": "national geographic style wildlife photography, sharp detail",
            "LUGAR": "professional travel photography, cinematic lighting, 4k"
        }.get(category, "high quality encyclopedia illustration")
        
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, {style}, realistic')}"
        response = requests.get(url + "?width=700&height=700&nologo=true", timeout=12)
        return PIL.Image.open(BytesIO(response.content)) if response.ok else None
    except:
        return None

def get_prompt(is_image=False, item_name=None, inherited_category=None):
    if is_image:
        return """Eres TURIDEX. Analiza la imagen con Chain-of-Thought.

PASO 1: Identifica claramente si es COMIDA, ANIMAL o LUGAR.
PASO 2: Extrae nombre real.
PASO 3: Asigna stats según categoría.
PASO 4: Da exactamente 3 variantes del MISMO tipo (solo sustantivos).

Responde EXACTAMENTE así:
NOMBRE: 
CATEGORIA: 
DESC: 
HISTORIA: 
STATS: [n1, n2, n3, n4]
EVOS: [var1, var2, var3]"""
    
    else:
        return f"""Eres TURIDEX. Dame información completa y precisa sobre: {item_name}

Categoría heredada: {inherited_category or 'la misma del contexto anterior'}

Sigue este formato exacto y no añadas nada más:

NOMBRE: {item_name}
CATEGORIA: {inherited_category or 'COMIDA'}
DESC: [máximo 15 palabras]
HISTORIA: [Dos párrafos reales, bien escritos]
STATS: [n1, n2, n3, n4]
EVOS: [Variante1, Variante2, Variante3]

Reglas:
- Si es COMIDA usa: Sabor, Picante, Salud, Rareza
- Si es ANIMAL usa: Fuerza, Agilidad, Peligro, Rareza
- Si es LUGAR usa: Historia, Belleza, Cultura, Rareza
- Las variantes deben ser del mismo tipo (nada de adjetivos)."""

def get_labels(category):
    if category == "ANIMAL":
        return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif category == "LUGAR":
        return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else:
        return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

# ====================== FLUJO PRINCIPAL ======================
with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)
    
    # --- BOTÓN DE RESET ---
    if st.button("🔄 Reiniciar TURIDEX"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    col1, col2 = st.columns([1, 2])

    # ====================== MODO VARIANTE (TEXTO) ======================
    if st.session_state.current_item and st.session_state.current_category:
        item = st.session_state.current_item
        cat = st.session_state.current_category
        
        with st.spinner(f"Buscando información de **{item}**..."):
            try:
                prompt = get_prompt(is_image=False, item_name=item, inherited_category=cat)
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.1,
                    max_tokens=1200
                )
                res = response.choices[0].message.content

                nombre = extract("NOMBRE", res)
                categoria = extract("CATEGORIA", res).upper() or cat
                desc = extract("DESC", res)
                historia = extract("HISTORIA", res)
                stats_raw = extract("STATS", res)
                evos_raw = extract("EVOS", res)

                nums = [min(100, max(0, int(n))) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: nums.append(10)
                
                variantes = [v.strip() for v in evos_raw.split(",") if v.strip()][:3]

                # Guardar en historial
                if nombre not in st.session_state.historial:
                    st.session_state.historial.append(nombre)
                
                st.session_state.current_category = categoria

                # ====================== RENDERIZADO ======================
                with col1:
                    img = generate_image(nombre, categoria)
                    if img:
                        st.image(img, use_container_width=True, caption=f"{nombre}")
                    else:
                        st.info(f"🖼️ Visualización de **{nombre}**")

                with col2:
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
                    
                    # Audio
                    try:
                        tts = gTTS(f"{nombre}. {desc}. {historia[:150]}", lang='es')
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        st.audio(fp)
                    except:
                        pass

            except Exception as e:
                st.error(f"Error: {e}")

    # ====================== MODO IMAGEN ======================
    else:
        with col1:
            archivo = st.file_uploader("Sube una imagen", type=["jpg","png","jpeg"])
            if archivo:
                st.image(archivo, use_container_width=True)
                if st.button("🔍 ESCANEAR CON TURIDEX", type="primary", use_container_width=True):
                    with st.spinner("Analizando imagen..."):
                        try:
                            b64 = encode_image(archivo)
                            prompt = get_prompt(is_image=True)
                            response = client.chat.completions.create(
                                messages=[{
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": prompt},
                                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                                    ]
                                }],
                                model="meta-llama/llama-4-scout-17b-16e-instruct",
                                temperature=0.1
                            )
                            res = response.choices[0].message.content
                            
                            nombre = extract("NOMBRE", res)
                            categoria = extract("CATEGORIA", res).upper()
                            
                            st.session_state.current_item = nombre
                            st.session_state.current_category = categoria
                            st.session_state.historial = [nombre]
                            st.session_state.last_image = archivo
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error al analizar imagen: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
