import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Turidex Elite v4", page_icon="📸", layout="wide")

# --- CSS DE ALTO CONTRASTE Y DISEÑO LIMPIO ---
st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    /* El contenedor principal con efecto cristal oscuro */
    .pokedex-frame {
        background-color: rgba(0, 0, 0, 0.75);
        backdrop-filter: blur(10px);
        border: 4px solid #DC0A2D;
        border-radius: 20px;
        padding: 30px;
        color: white;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);
    }
    .pokedex-title {
        font-family: 'Courier New', monospace;
        color: #FFCC00;
        text-align: center;
        text-shadow: 2px 2px #000;
        font-size: 3.5em;
        margin-bottom: 20px;
    }
    .data-card {
        background-color: rgba(48, 167, 215, 0.2);
        border-left: 5px solid #30A7D7;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
    }
    .stats-box {
        background-color: rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    .evo-tag {
        background-color: #FFCC00;
        color: black;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
    }
    /* Estilo para que el texto de Streamlit no se pierda */
    .stMarkdown, p, h1, h2, h3 {
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='pokedex-title'>TURIDEX ELITE</h1>", unsafe_allow_html=True)

# Lógica de Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Error: Configura tu GROQ_API_KEY.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- CUERPO DE LA APP ---
with st.container():
    st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
    
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        archivo = st.file_uploader("📸 Escáner de Élite", type=["jpg", "png", "jpeg"])
        if archivo:
            st.image(PIL.Image.open(archivo), use_container_width=True)
            analizar = st.button("🔍 INICIAR ANÁLISIS")
    
    if archivo and analizar:
        with st.spinner("⏳ Analizando con Llama 4 Scout..."):
            try:
                base_4_img = encode_image(archivo)
                prompt = """Actúa como un Crítico Gastronómico y Analista Científico. 
                Analiza la imagen. Si es comida chatarra (salchipapa, etc), Salud < 15.
                
                Responde EXACTAMENTE así:
                NOMBRE: [Nombre]
                TIPO: [Categoría]
                DESC: [Breve descripción]
                HISTORIA: [Historia larga y detallada de 2 párrafos]
                STATS: [Valor1, Valor2, Valor3, Valor4] (4 números)
                EVOS: [Var1, Var2, Var3]"""

                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base_4_img}"}}
                    ]}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.4
                )
                
                res = chat.choices[0].message.content

                # --- EXTRACCIÓN LIMPIA ---
                def extraer(tag, texto):
                    try:
                        regex = rf"{tag}:\s*(.*?)(?=\n[A-Z]+:|$)"
                        return re.search(regex, texto, re.S).group(1).strip()
                    except: return "No disponible"

                nombre = extraer("NOMBRE", res)
                tipo = extraer("TIPO", res)
                desc = extraer("DESC", res)
                historia = extraer("HISTORIA", res)
                stats_raw = extraer("STATS", res)
                evos_raw = extraer("EVOS", res)
                
                nums = [int(n) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: nums.append(0)

                # --- RENDERIZADO EN COL_INFO ---
                with col_info:
                    st.markdown(f"## 📋 {nombre}")
                    st.markdown(f"<div class='data-card'><b>{tipo.upper()}</b><br>{desc}</div>", unsafe_allow_html=True)
                    
                    st.subheader("📖 Origen y Detalles")
                    st.write(historia)
                    
                    st.subheader("📊 Análisis de Puntos Base")
                    labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
                    if "animal" in tipo.lower(): labels = ["🐾 Fuerza", "⚡ Agilidad", "❤️ Ternura", "💎 Rareza"]
                    
                    st.markdown("<div class='stats-box'>", unsafe_allow_html=True)
                    c_a, c_b = st.columns(2)
                    with c_a:
                        st.write(f"{labels[0]}: {nums[0]}%"); st.progress(nums[0]/100)
                        st.write(f"{labels[1]}: {nums[1]}%"); st.progress(nums[1]/100)
                    with c_b:
                        st.write(f"{labels[2]}: {nums[2]}%"); st.progress(nums[2]/100)
                        st.write(f"{labels[3]}: {nums[3]}%"); st.progress(nums[3]/100)
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.subheader("🔄 Variantes")
                    for e in evos_raw.split(","):
                        st.markdown(f"<span class='evo-tag'>{e.strip()}</span>", unsafe_allow_html=True)

                # Audio
                tts = gTTS(text=f"{nombre}. {desc}. {historia}", lang='es')
                fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)

            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
