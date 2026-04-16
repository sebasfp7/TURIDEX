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
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'historial' not in st.session_state: st.session_state.historial = []

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.9); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-family: 'Courier New', monospace; font-size: 3.8em;
            text-shadow: 0 0 20px #FFDE00, 0 0 35px #FF0000;}
    .current-header {background: linear-gradient(90deg, #000000, #1a1a1a); color: #00FF41; 
                     padding: 15px; border-radius: 10px; text-align: center; font-size: 1.5em; 
                     font-weight: bold; margin-bottom: 15px; border: 2px solid #00FF41;}
    .data-card, .historia-box {background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
                               padding: 18px; border-radius: 10px; margin: 12px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.25);}
    .variant-btn {background: linear-gradient(135deg, #FFCC00, #FFEB3B) !important; color: black !important;
                  font-weight: bold !important; border: 3px solid black !important; border-radius: 15px !important;
                  padding: 15px !important; margin: 8px 0 !important;}
    .variant-btn:hover {transform: translateY(-5px); box-shadow: 0 10px 20px rgba(220,10,45,0.6) !important;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title' style='text-align:center'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Configura tu GROQ_API_KEY")

def clean_text(text):
    return re.sub(r'[*#_\[\]]', '', re.sub(r'\n{3,}', '\n\n', text)).strip()

def extract(tag, text):
    match = re.search(rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)", text, re.S | re.I)
    return clean_text(match.group(1)) if match else ""

def generate_image(name, category):
    try:
        style = {
            "ANIMAL": "realistic wildlife photography, national geographic, sharp detail, dramatic lighting",
            "COMIDA": "professional appetizing food photography, studio lighting, high detail",
            "LUGAR": "epic cinematic landscape photography, national geographic style, 4k"
        }.get(category, "high quality realistic photography")
        
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(f'{name}, {style}, no text, clean background')}"
        response = requests.get(url + "?width=800&height=600&nologo=true&enhance=true", timeout=12)
        if response.status_code == 200:
            return PIL.Image.open(BytesIO(response.content))
        return None
    except:
        return None

def get_prompt(item_name=None, inherited_category=None):
    if item_name is None:  # Modo imagen
        return """Analiza la imagen y responde EXACTAMENTE con este formato:

NOMBRE: 
CATEGORIA: [COMIDA, ANIMAL o LUGAR]
DESC: 
HISTORIA: 
STATS: [n1,n2,n3,n4]
EVOS: [var1,var2,var3]"""
    
    else:  # Modo variante (texto)
        return f"""Eres TURIDEX. Analiza "{item_name}".

**REGLA ABSOLUTA DE CATEGORÍA:**
Categoría confirmada: {inherited_category}
Solo usa los stats correspondientes a esa categoría. No mezcles nunca.

**STATS OBLIGATORIOS POR CATEGORÍA:**

→ SI ES ANIMAL: Usa **Fuerza, Agilidad, Peligro, Rareza**
→ SI ES COMIDA: Usa **Sabor, Picante, Salud, Rareza**
→ SI ES LUGAR: Usa **Historia, Belleza, Cultura, Rareza**

**EJEMPLOS REALISTAS:**
- León / Leopardo / Tigre → Fuerza:80-90, Agilidad:85-95, Peligro:70-85, Rareza:60-80
- Comida frita (salchipapa) → Sabor:75-90, Picante:20-50, Salud:10-25, Rareza:30-50
- Lugares famosos → Historia y Belleza casi siempre >85

Responde **exactamente** con este formato:

NOMBRE: {item_name}
CATEGORIA: {inherited_category}
DESC: [máximo 15 palabras]
HISTORIA: [Dos párrafos bien escritos]
STATS: [n1, n2, n3, n4]
EVOS: [Variante1, Variante2, Variante3]"""

def get_labels(category):
    category = category.upper()
    if "ANIMAL" in category:
        return ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
    elif "LUGAR" in category:
        return ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    else:  # COMIDA por defecto
        return ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

# ====================== INTERFAZ ======================
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

        with st.spinner(f"Generando ficha de {item}..."):
            try:
                prompt = get_prompt(item, cat)
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.07,
                    max_tokens=1400
                )
                res = response.choices[0].message.content

                nombre = extract("NOMBRE", res) or item
                categoria = extract("CATEGORIA", res).upper() or cat
                desc = extract("DESC", res)
                historia = extract("HISTORIA", res)
                stats_raw = extract("STATS", res)
                evos_raw = extract("EVOS", res)

                nums = [min(100, max(5, int(n))) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: nums.append(50)

                variantes = [v.strip() for v in evos_raw.split(",") if len(v.strip()) > 2][:3]

                if nombre not in st.session_state.historial:
                    st.session_state.historial.append(nombre)
                st.session_state.current_category = categoria

                # ====================== RENDER ======================
                with col_img:
                    st.markdown(f"**Visualización de {nombre}**")
                    with st.spinner("Generando imagen..."):
                        img = generate_image(nombre, categoria)
                        if img:
                            st.image(img, use_container_width=True)
                        else:
                            st.error("⚠️ No se pudo generar la imagen (API temporalmente inestable)")
                            st.info("🔄 Intenta cambiar a otra variante")

                with col_info:
                    st.markdown(f"## {nombre}")
                    st.markdown(f"<div class='data-card'><b>Categoría:</b> {categoria}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-card'>{desc}</div>", unsafe_allow_html=True)
                    
                    st.markdown("### 📖 Historia")
                    st.markdown(f"<div class='historia-box'>{historia}</div>", unsafe_allow_html=True)
                    
                    labels = get_labels(categoria)   # ← FUERZA LAS ETIQUETAS CORRECTAS
                    
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

                    try:
                        tts = gTTS(f"{nombre}. {desc}. {historia[:160]}", lang='es')
                        fp = io.BytesIO(); tts.write_to_fp(fp)
                        st.audio(fp)
                    except: pass

            except Exception as e:
                st.error(f"Error: {str(e)}")

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

                            st.session_state.current_item = nombre or "Elemento desconocido"
                            st.session_state.current_category = categoria or "ANIMAL"
                            st.session_state.historial = [st.session_state.current_item]
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al analizar: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
