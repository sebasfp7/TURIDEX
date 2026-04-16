import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex Elite", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-attachment: fixed;
    }
    .pokedex-frame {
        background-color: rgba(20, 20, 20, 0.95); /* Fondo casi negro para máximo contraste */
        border: 5px solid #DC0A2D;
        border-radius: 15px;
        padding: 25px;
        color: white;
    }
    .text-box {
        background-color: #303030; /* Fondo gris oscuro para el texto */
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #555;
        color: #FFFFFF !important;
        margin-bottom: 10px;
    }
    .evo-tag {
        background-color: #FFCC00;
        color: #000000 !important;
        padding: 8px 12px;
        border-radius: 5px;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
    }
    h1, h2, h3, p, span { color: white !important; }
</style>
""", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Error en la API Key.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
st.markdown("<h1 style='text-align:center; color:#FFCC00 !important;'>TURIDEX ELITE</h1>", unsafe_allow_html=True)

col_img, col_info = st.columns([1, 2])

with col_img:
    archivo = st.file_uploader("📸 Escanear", type=["jpg", "png", "jpeg"])
    if archivo:
        st.image(PIL.Image.open(archivo), use_container_width=True)
        btn = st.button("🔍 ANALIZAR")

if archivo and btn:
    with st.spinner("Analizando..."):
        try:
            img_b64 = encode_image(archivo)
            prompt = """Actúa como un experto evaluador de comida y objetos. 
            Analiza la imagen y responde estrictamente en este formato:
            NOMBRE: [Nombre]
            TIPO: [Categoría]
            HISTORIA: [Descripción y origen detallado]
            STATS: [Sabor, Picante, Salud, Rareza] (4 números del 0 al 100)
            EVOS: [Solo 3 nombres de variantes o evoluciones separados por comas]
            
            CRÍTICO: Si es comida chatarra, SALUD debe ser menor a 15."""

            chat = client.chat.completions.create(
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                ]}],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                temperature=0.2
            )
            res = chat.choices[0].message.content

            def extraer(tag, texto):
                try:
                    return re.search(rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)", texto, re.S).group(1).strip()
                except: return "---"

            nombre = extraer("NOMBRE", res)
            tipo = extraer("TIPO", res)
            historia = extraer("HISTORIA", res)
            stats_raw = extraer("STATS", res)
            evos_raw = extraer("EVOS", res)

            # Lógica de Stats
            nums = [int(n) for n in re.findall(r'\d+', stats_raw)][0:4]
            while len(nums) < 4: nums.append(0)

            with col_info:
                st.markdown(f"## {nombre}")
                st.markdown(f"<div class='text-box'><b>TIPO:</b> {tipo}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='text-box'>{historia}</div>", unsafe_allow_html=True)
                
                st.subheader("📊 Puntos Base")
                labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"{labels[0]}: {nums[0]}%"); st.progress(nums[0]/100)
                    st.write(f"{labels[1]}: {nums[1]}%"); st.progress(nums[1]/100)
                with c2:
                    st.write(f"{labels[2]}: {nums[2]}%"); st.progress(nums[2]/100)
                    st.write(f"{labels[3]}: {nums[3]}%"); st.progress(nums[3]/100)

                st.subheader("🔄 Variantes")
                for e in evos_raw.split(","):
                    if e.strip():
                        st.markdown(f"<span class='evo-tag'>{e.strip()}</span>", unsafe_allow_html=True)

            tts = gTTS(text=f"{nombre}. {historia}", lang='es')
            fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)

        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("</div>", unsafe_allow_html=True)
