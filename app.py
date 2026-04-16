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
    .pokedex-title {
        font-family: 'Courier New', monospace;
        color: #FFCC00;
        text-align: center;
        text-shadow: 3px 3px 0 #000;
        font-size: 3em;
        padding: 10px;
    }
    .pokedex-frame {
        background-color: #DC0A2D;
        border: 8px solid #8B0000;
        border-radius: 15px;
        padding: 25px;
        box-shadow: 10px 10px 0px rgba(0,0,0,0.4);
    }
    .img-container {
        background-color: #dedede;
        border: 4px solid #585858;
        border-radius: 10px;
        padding: 10px;
        margin: 0 auto;
        width: 260px;
    }
    .data-card {
        background-color: #30A7D7;
        color: white;
        border-radius: 10px;
        padding: 15px;
        margin: 15px 0;
        border: 2px solid #1b7ba1;
    }
    .evo-card {
        background-color: #444;
        border: 2px solid #FFCC00;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='pokedex-title'>TURIDEX</h1>", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
archivo = st.file_uploader("📸 Escaneando entorno...", type=["jpg", "png", "jpeg"])

if archivo:
    st.markdown("<div class='img-container'>", unsafe_allow_html=True)
    st.image(PIL.Image.open(archivo), width=240)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🔍 INICIAR ESCÁNER"):
        # Mensaje de carga sencillo, la info aparecerá abajo automáticamente
        with st.spinner("⏳ La IA está analizando cada detalle..."):
            try:
                base64_image = encode_image(archivo)
                
                prompt = """Actúa como una Pokédex experta. Identifica el objeto/plato. 
                Sé extremadamente LÓGICO con los stats (Ej: Una Margarita NO es picante).
                Responde en ESPAÑOL:
                NOMBRE: [Nombre]
                TIPO: [Categoría]
                DESC: [Descripción de una línea]
                HISTORIA: [Dos párrafos culturales]
                STATS: [4 números del 0 al 100 para: Sabor, Picante, Salud, Rareza]
                EVOS: [3 versiones alternativas separadas por comas]"""

                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    model="llama-3.2-90b-vision-preview",
                    temperature=0.2 # Menor temperatura = más precisión y coherencia
                )
                
                res = chat.choices[0].message.content

                # --- EXTRACCIÓN DIRECTA (SIN CLICS EXTRA) ---
                nombre = res.split("NOMBRE:")[1].split("\n")[0].strip()
                tipo = res.split("TIPO:")[1].split("\n")[0].strip()
                desc = res.split("DESC:")[1].split("\n")[0].strip()
                historia = res.split("HISTORIA:")[1].split("STATS:")[0].strip()
                stats_raw = res.split("STATS:")[1].split("EVOS:")[0].strip()
                evos = res.split("EVOS:")[1].strip().split(",")

                nums = [int(n.strip()) for n in stats_raw.split(",")]

                # --- MOSTRAR TODO INMEDIATAMENTE ---
                st.markdown(f"## 📋 {nombre}")
                
                st.markdown(f"<div class='data-card'><b>Tipo:</b> {tipo}<br><i>{desc}</i></div>", unsafe_allow_html=True)
                
                st.write(historia)

                st.subheader("📊 Puntos Base")
                c1, c2 = st.columns(2)
                labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
                with c1:
                    st.write(f"{labels[0]}: {nums[0]}%")
                    st.progress(nums[0]/100)
                    st.write(f"{labels[1]}: {nums[1]}%")
                    st.progress(nums[1]/100)
                with c2:
                    st.write(f"{labels[2]}: {nums[2]}%")
                    st.progress(nums[2]/100)
                    st.write(f"{labels[3]}: {nums[3]}%")
                    st.progress(nums[3]/100)

                st.markdown("### 🔄 Otras Presentaciones")
                ec1, ec2, ec3 = st.columns(3)
                with ec1: st.markdown(f"<div class='evo-card'>{evos[0]}</div>", unsafe_allow_html=True)
                with ec2: st.markdown(f"<div class='evo-card'>{evos[1]}</div>", unsafe_allow_html=True)
                with ec3: st.markdown(f"<div class='evo-card'>{evos[2]}</div>", unsafe_allow_html=True)

                # Audio automático al final
                audio_text = f"{nombre}. {tipo}. {desc}. {historia}"
                tts = gTTS(text=re.sub(r'[*#_]', '', audio_text), lang='es')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)

            except Exception as e:
                st.error("Error en la conexión. Intenta de nuevo.")

st.markdown("</div>", unsafe_allow_html=True)
