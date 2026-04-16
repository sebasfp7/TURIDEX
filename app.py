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

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.9); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title-box {background-color: #000000; border: 4px solid #DC0A2D; border-radius: 12px;
                padding: 15px; text-align: center; margin-bottom: 10px;}
    .title {color: #FFDE00 !important; font-family: 'Courier New', monospace; font-size: 3.8em;
            text-shadow: 0 0 20px #FFDE00, 0 0 30px #FF0000; animation: glow 2s infinite alternate;}
    @keyframes glow { from {text-shadow: 0 0 15px #FFDE00;} to {text-shadow: 0 0 25px #FFDE00, 0 0 40px #FF0000;} }
    .current-header {background: #000000; color: #00FF00; padding: 12px; border-radius: 8px;
                     text-align: center; font-size: 1.4em; font-weight: bold; margin-bottom: 15px;}
    .data-card, .historia-box {background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
                               padding: 18px; border-radius: 10px; margin: 10px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.2);}
    .variant-btn {background: linear-gradient(135deg, #FFCC00, #FFEB3B) !important; color: black !important;
                  font-weight: bold !important; border: 3px solid black !important; border-radius: 15px !important;
                  padding: 14px !important; margin: 8px 0 !important; transition: all 0.3s;}
    .variant-btn:hover {transform: translateY(-5px); box-shadow: 0 10px 20px rgba(220,10,45,0.5) !important;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title-box'><h1 class='title'>⚡ TURIDEX ⚡</h1></div>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Configura GROQ_API_KEY")

def clean_text(text):
    return re.sub(r'[*#_\[\]]', '', re.sub(r'\n{3,}', '\n\n', text)).strip()

def extract(tag, text):
    match = re.search(rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)", text, re.S | re.I)
    return clean_text(match.group(1)) if match else "No disponible"

def generate_image(name, category):
    try:
        styles = {
            "COMIDA": "professional food photography, appetizing, studio lighting, clean background",
            "ANIMAL": "wildlife photography, national geographic style, sharp detail, realistic",
            "LUGAR": "cinematic travel photography, epic composition, 4k, professional"
        }
        prompt = f"{name}, {styles.get(category, 'high quality realistic')}"
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=800&height=600&nologo=true"
        resp = requests.get(url, timeout=10)
        return PIL.Image.open(BytesIO(resp.content)) if resp.ok else None
    except:
        return None

def get_prompt(item_name=None, inherited_category=None):
    if item_name is None:  # Análisis de imagen
        return """Eres TURIDEX. Analiza la imagen y responde EXACTAMENTE con este formato:

NOMBRE: 
CATEGORIA: 
DESC: 
HISTORIA: 
STATS: [n1,n2,n3,n4]
EVOS: [var1, var2, var3]"""
    
    else:  # Análisis de variante (texto)
        return f"""Eres TURIDEX. Analiza "{item_name}" de categoría {inherited_category}.

**REGLAS DE STATS REALISTAS (MUY IMPORTANTE):**

**ANIMALES:**
- Grandes felinos (León, Tigre, Leopardo, Jaguar): Fuerza 75-92, Agilidad 80-95, Peligro 65-88, Rareza 55-80
- Animales medianos/peligrosos: valores medios-altos
- Animales domésticos: valores más bajos

**COMIDA:**
- Comida chatarra/frita (salchipapa, hamburguesa): Sabor 75-90, Picante 10-40, Salud 8-25, Rareza 20-45
- Comida premium: Salud más alto (60+)

**LUGARES FAMOSOS:** Historia y Belleza casi siempre 80-98.

Usa valores coherentes y realistas. No seas demasiado conservador.

Responde EXACTAMENTE en este formato:
NOMBRE: {item_name}
CATEGORIA: {inherited_category}
DESC: [máximo 15 palabras]
HISTORIA: [Dos párrafos bien escritos]
STATS: [n1, n2, n3, n4]
EVOS: [Variante1, Variante2, Variante3]"""

def get_labels(category):
    if category == "ANIMAL": return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif category == "LUGAR": return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else: return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

# ====================== INTERFAZ ======================
with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)

    if st.button("🔄 Reiniciar TURIDEX"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Mostrar elemento ACTUAL en la parte superior
    if st.session_state.current_item:
        st.markdown(f"<div class='current-header'>📍 {st.session_state.current_item}</div>", unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 2])

    # ====================== MODO VARIANTE ======================
    if st.session_state.current_item and st.session_state.current_category:
        item = st.session_state.current_item
        cat = st.session_state.current_category

        with st.spinner(f"Analizando {item}..."):
            try:
                prompt = get_prompt(item, cat)
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.1,
                    max_tokens=1300
                )
                res = response.choices[0].message.content

                nombre = extract("NOMBRE", res)
                categoria = extract("CATEGORIA", res).upper() or cat
                desc = extract("DESC", res)
                historia = extract("HISTORIA", res)
                stats_raw = extract("STATS", res)
                evos_raw = extract("EVOS", res)

                nums = [min(100, max(0, int(n))) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: nums.append(30)

                variantes = [v.strip() for v in evos_raw.split(",") if len(v.strip()) > 2][:3]

                if nombre not in st.session_state.historial:
                    st.session_state.historial.append(nombre)
                st.session_state.current_category = categoria

                with col_img:
                    img = generate_image(nombre, categoria)
                    if img:
                        st.image(img, use_container_width=True, caption=f"Visualización de {nombre}")
                    else:
                        st.info(f"🌐 Visualización de **{nombre}**")

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
                        st.write(f"{labels[0]}: **{nums[0]}%**"); st.progress(nums[0]/100)
                        st.write(f"{labels[1]}: **{nums[1]}%**"); st.progress(nums[1]/100)
                    with c2:
                        st.write(f"{labels[2]}: **{nums[2]}%**"); st.progress(nums[2]/100)
                        st.write(f"{labels[3]}: **{nums[3]}%**"); st.progress(nums[3]/100)
                    
                    st.markdown("### 🔄 Variantes")
                    for var in variantes:
                        if st.button(var, key=f"var_{var}", use_container_width=True):
                            st.session_state.current_item = var
                            st.session_state.current_category = categoria
                            st.rerun()

                    # Audio
                    try:
                        tts_text = f"{nombre}. {desc}. {historia[:180]}"
                        tts = gTTS(clean_text(tts_text), lang='es')
                        fp = io.BytesIO(); tts.write_to_fp(fp)
                        st.audio(fp)
                    except:
                        pass

            except Exception as e:
                st.error(f"Error: {e}")

    # ====================== MODO IMAGEN ======================
    else:
        with col_img:
            archivo = st.file_uploader("Carga una imagen", type=["jpg","png","jpeg"])
            if archivo:
                st.image(archivo, use_container_width=True)
                if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                    with st.spinner("Analizando imagen..."):
                        try:
                            b64 = base64.b64encode(archivo.getvalue()).decode()
                            prompt = get_prompt()
                            resp = client.chat.completions.create(
                                messages=[{"role":"user","content":[
                                    {"type":"text","text":prompt},
                                    {"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}
                                ]}],
                                model="meta-llama/llama-4-scout-17b-16e-instruct",
                                temperature=0.1
                            )
                            data = resp.choices[0].message.content
                            nombre = extract("NOMBRE", data)
                            categoria = extract("CATEGORIA", data).upper()

                            st.session_state.current_item = nombre
                            st.session_state.current_category = categoria
                            st.session_state.historial = [nombre]
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
