import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Turidex", page_icon="📸", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    /* Sombra de texto para máxima legibilidad en CUALQUIER fondo */
    .legible-text {
        color: white !important;
        text-shadow: 2px 2px 4px #000000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
    }
    .pokedex-title {
        font-family: 'Courier New', monospace;
        color: #FFCC00;
        text-align: center;
        text-shadow: 3px 3px 0 #000;
        font-size: 3.5em;
        padding: 10px;
    }
    .pokedex-frame {
        background-color: rgba(220, 10, 45, 0.95); /* Rojo un poco más sólido */
        border: 8px solid #8B0000;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 10px 10px 0px rgba(0,0,0,0.4);
    }
    .img-container {
        background-color: #f0f0f0;
        border: 4px solid #585858;
        border-radius: 10px;
        padding: 10px;
        margin: 0 auto;
        width: 260px;
        text-align: center;
    }
    .data-card {
        background-color: rgba(48, 167, 215, 0.9);
        color: white;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        border: 2px solid #1b7ba1;
        font-weight: bold;
        text-shadow: 1px 1px 2px #000;
    }
    .evo-card {
        background-color: #333;
        border: 2px solid #FFCC00;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        color: white;
        font-weight: bold;
        text-shadow: 1px 1px 2px #000;
    }
    /* Forzar que todos los textos dentro de la pokedex sean legibles */
    .stMarkdown p, .stMarkdown h2, .stMarkdown h3 {
        color: white !important;
        text-shadow: 1px 1px 3px #000;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='pokedex-title'>TURIDEX</h1>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Error: Configura la API KEY en Secrets.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
archivo = st.file_uploader("📸 Escaneando objetivo...", type=["jpg", "png", "jpeg"])

if archivo:
    st.markdown("<div class='img-container'>", unsafe_allow_html=True)
    st.image(PIL.Image.open(archivo), width=240)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🔍 INICIAR ESCÁNER"):
        with st.spinner("⏳ Analizando con Llama 4 Scout..."):
            try:
                base64_image = encode_image(archivo)
                # Prompt con instrucciones nutricionales estrictas
                prompt = """Actúa como una Pokédex. Analiza la imagen.
                CRÍTICO: Sé realista y estricto con la salud (si es pizza/comida rápida, salud debe ser MENOR a 30).
                Responde en ESPAÑOL:
                NOMBRE: [Nombre]
                TIPO: [Categoría]
                DESC: [Descripción breve]
                HISTORIA: [Dos párrafos]
                STATS: [Sabor, Picante, Salud, Rareza - 4 números 0-100]
                EVOS: [3 versiones alternativas]"""

                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.1
                )
                
                res = chat.choices[0].message.content

                def extraer(clave, texto):
                    try:
                        parte = texto.split(clave + ":")[1]
                        for k in ["NOMBRE", "TIPO", "DESC", "HISTORIA", "STATS", "EVOS"]:
                            if k + ":" in parte: parte = parte.split(k + ":")[0]
                        return parte.strip()
                    except: return "---"

                nombre = extraer("NOMBRE", res)
                tipo = extraer("TIPO", res)
                desc = extraer("DESC", res)
                historia = extraer("HISTORIA", res)
                stats_raw = extraer("STATS", res)
                evos_raw = extraer("EVOS", res)

                try: nums = [int(n.strip()) for n in stats_raw.replace('[','').replace(']','').split(",")]
                except: nums = [50, 0, 20, 10]
                evos = evos_raw.split(",") if "," in evos_raw else ["Normal", "Especial", "Premium"]

                # --- DISPLAY MEJORADO ---
                st.markdown(f"<h2 class='legible-text'>📋 {nombre}</h2>", unsafe_allow_html=True)
                st.markdown(f"<div class='data-card'>TIPO: {tipo}<br><i>{desc}</i></div>", unsafe_allow_html=True)
                
                st.markdown(f"<p class='legible-text'>{historia}</p>", unsafe_allow_html=True)

                st.markdown("<h3 class='legible-text'>📊 Puntos Base</h3>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
                with c1:
                    st.write(f"**{labels[0]}: {nums[0]}%**")
                    st.progress(min(nums[0]/100, 1.0))
                    st.write(f"**{labels[1]}: {nums[1]}%**")
                    st.progress(min(nums[1]/100, 1.0))
                with c2:
                    st.write(f"**{labels[2]}: {nums[2]}%**")
                    st.progress(min(nums[2]/100, 1.0))
                    st.write(f"**{labels[3]}: {nums[3]}%**")
                    st.progress(min(nums[3]/100, 1.0))

                st.markdown("<h3 class='legible-text'>🔄 Otras Presentaciones</h3>", unsafe_allow_html=True)
                ec = st.columns(3)
                for i, col in enumerate(ec):
                    if i < len(evos):
                        with col: st.markdown(f"<div class='evo-card'>{evos[i].strip()}</div>", unsafe_allow_html=True)

                audio_text = f"{nombre}. {tipo}. {desc}. {historia}"
                tts = gTTS(text=re.sub(r'[*#_]', '', audio_text), lang='es')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)

            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("</div>", unsafe_allow_html=True)
