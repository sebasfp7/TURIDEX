import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TURIDEX", layout="wide")

# --- CSS DE IDENTIDAD Y CONTRASTE ---
st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .pokedex-frame {
        background-color: rgba(255, 255, 255, 0.9);
        border: 4px solid #DC0A2D;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }
    .pokedex-title-box {
        background-color: #000000;
        border: 4px solid #DC0A2D;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .pokedex-title {
        color: #FFFFFF !important;
        font-family: 'Courier New', monospace;
        font-size: 3em;
        margin: 0;
    }
    /* TODO EL TEXTO EN NEGRO */
    .black-text, p, h1, h2, h3, span, label {
        color: #000000 !important;
        font-weight: 500;
    }
    .data-card {
        background-color: rgba(0, 0, 0, 0.05);
        border-left: 5px solid #DC0A2D;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .evo-tag {
        background-color: #FFCC00;
        color: black !important;
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: bold;
        display: inline-block;
        margin: 4px;
        border: 1px solid #000;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='pokedex-title-box'><h1 class='pokedex-title'>TURIDEX</h1></div>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Configura la API KEY en Secrets.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

with st.container():
    st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        archivo = st.file_uploader("", type=["jpg", "png", "jpeg"])
        if archivo:
            st.image(PIL.Image.open(archivo), use_container_width=True)
            analizar = st.button("🔍 ESCANEAR OBJETIVO")

    if archivo and analizar:
        with st.spinner("Analizando..."):
            try:
                img_b64 = encode_image(archivo)
                # PROMPT INTELIGENTE: Clasificación por categorías
                prompt = """Actúa como el sistema de inteligencia TURIDEX. Analiza la imagen y clasifícala en una de estas 3 categorías: COMIDA, ANIMAL, o LUGAR.
                
                REGLAS DE IDENTIFICACIÓN:
                1. Si es ANIMAL: Los STATS deben ser [Fuerza, Agilidad, Peligro, Rareza]. Las EVOS deben ser otros animales similares (ej: si es León -> Tigre, Jaguar).
                2. Si es LUGAR: Los STATS deben ser [Historia, Belleza, Cultura, Rareza]. Las EVOS deben ser otros lugares similares.
                3. Si es COMIDA: Los STATS deben ser [Sabor, Picante, Salud, Rareza]. Las EVOS deben ser variantes del plato.
                
                Responde EXACTAMENTE así:
                NOMBRE: [Nombre]
                CATEGORIA: [ANIMAL, LUGAR o COMIDA]
                DESC: [Descripción breve]
                HISTORIA: [Contexto detallado de 2 párrafos]
                STATS: [Valor1, Valor2, Valor3, Valor4] (Números 0-100)
                EVOS: [Variante1, Variante2, Variante3]"""

                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.2
                )
                res = chat.choices[0].message.content

                def extraer(tag, texto):
                    try: return re.search(rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)", texto, re.S).group(1).strip()
                    except: return "---"

                nombre = extraer("NOMBRE", res)
                cat = extraer("CATEGORIA", res).upper()
                desc = extraer("DESC", res)
                historia = extraer("HISTORIA", res)
                stats_raw = extraer("STATS", res)
                evos_raw = extraer("EVOS", res)
                
                nums = [int(n) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: nums.append(0)

                with col_info:
                    st.markdown(f"## 📋 {nombre}")
                    st.markdown(f"<div class='data-card'><p><b>CATEGORÍA:</b> {cat}<br>{desc}</p></div>", unsafe_allow_html=True)
                    
                    st.markdown("### 📖 Historia y Datos")
                    st.markdown(f"<p>{historia}</p>", unsafe_allow_html=True)
                    
                    # Lógica de etiquetas dinámicas
                    if "ANIMAL" in cat: labels = ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
                    elif "LUGAR" in cat: labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
                    else: labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

                    st.markdown(f"### 📊 Puntos Base ({cat})")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"<p>{labels[0]}: {nums[0]}%</p>", unsafe_allow_html=True)
                        st.progress(nums[0]/100)
                        st.markdown(f"<p>{labels[1]}: {nums[1]}%</p>", unsafe_allow_html=True)
                        st.progress(nums[1]/100)
                    with c2:
                        st.markdown(f"<p>{labels[2]}: {nums[2]}%</p>", unsafe_allow_html=True)
                        st.progress(nums[2]/100)
                        st.markdown(f"<p>{labels[3]}: {nums[3]}%</p>", unsafe_allow_html=True)
                        st.progress(nums[3]/100)

                    st.markdown("### 🔄 Variantes Relacionadas")
                    for e in evos_raw.split(","):
                        st.markdown(f"<span class='evo-tag'>{e.strip()}</span>", unsafe_allow_html=True)

                tts = gTTS(text=f"{nombre}. {historia}", lang='es')
                fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)

            except Exception as e:
                st.error(f"Error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)
