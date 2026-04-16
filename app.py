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
        text-align: center;
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

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Error: Configura tu GROQ_API_KEY en los Secrets.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
archivo = st.file_uploader("📸 Escaneando entorno...", type=["jpg", "png", "jpeg"])

if archivo:
    st.markdown("<div class='img-container'>", unsafe_allow_html=True)
    st.image(PIL.Image.open(archivo), width=240)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🔍 INICIAR ESCÁNER"):
        with st.spinner("⏳ Accediendo a la red de Turidex..."):
            try:
                base64_image = encode_image(archivo)
                prompt = """Actúa como una Pokédex experta. Analiza la imagen y responde en ESPAÑOL.
                Sé LÓGICO con los stats (Ej: Margarita picante 0). 
                Formato estricto:
                NOMBRE: [Nombre]
                TIPO: [Categoría]
                DESC: [Descripción breve]
                HISTORIA: [Dos párrafos]
                STATS: [Sabor, Picante, Salud, Rareza - 4 números 0-100]
                EVOS: [3 versiones alternativas]"""

                # LISTA DE MODELOS POR SI UNO FALLA
                modelos_a_probar = ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]
                res = None
                
                for mod in modelos_a_probar:
                    try:
                        chat = client.chat.completions.create(
                            messages=[{"role": "user", "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                            ]}],
                            model=mod,
                            temperature=0.1
                        )
                        res = chat.choices[0].message.content
                        break # Si funciona, salimos del bucle
                    except Exception:
                        continue # Si falla, probamos el siguiente

                if not res:
                    st.error("Ningún modelo de visión está respondiendo. Groq está en mantenimiento.")
                    st.stop()

                # --- EXTRACCIÓN ROBUSTA ---
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

                # Stats y Evos
                try: nums = [int(n.strip()) for n in stats_raw.replace('[','').replace(']','').split(",")]
                except: nums = [50, 0, 50, 10]
                evos = evos_raw.split(",") if "," in evos_raw else ["Ver. A", "Ver. B", "Ver. C"]

                # --- DISPLAY ---
                st.markdown(f"## 📋 {nombre}")
                st.markdown(f"<div class='data-card'><b>Tipo:</b> {tipo}<br><i>{desc}</i></div>", unsafe_allow_html=True)
                st.write(historia)

                st.subheader("📊 Puntos Base")
                c1, c2 = st.columns(2)
                labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
                with c1:
                    st.write(f"{labels[0]}: {nums[0]}%"); st.progress(min(nums[0]/100, 1.0))
                    st.write(f"{labels[1]}: {nums[1]}%"); st.progress(min(nums[1]/100, 1.0))
                with c2:
                    st.write(f"{labels[2]}: {nums[2]}%"); st.progress(min(nums[2]/100, 1.0))
                    st.write(f"{labels[3]}: {nums[3]}%"); st.progress(min(nums[3]/100, 1.0))

                st.markdown("### 🔄 Otras Presentaciones")
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
                st.error(f"Error crítico: {e}")

st.markdown("</div>", unsafe_allow_html=True)
