import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TURIDEX", page_icon="📸", layout="wide")

# --- CSS DE IDENTIDAD Y CONTRASTE CRÍTICO ---
st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    /* El contenedor principal con efecto cristal */
    .pokedex-frame {
        background-color: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(5px);
        border: 4px solid #DC0A2D;
        border-radius: 20px;
        padding: 30px;
        color: black;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }
    /* Cuadro de título negro superior con borde rojo */
    .pokedex-title-box {
        background-color: #000000;
        border: 4px solid #DC0A2D;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.5);
    }
    .pokedex-title {
        font-family: 'Courier New', monospace;
        color: #FFFFFF !important;
        text-shadow: 2px 2px #DC0A2D;
        font-size: 3.5em;
        margin: 0;
        font-weight: bold;
    }
    /* Forzar QUE TODO EL TEXTO SEA NEGRO */
    .stMarkdown, p, h1, h2, h3, .evo-tag, span, .stWrite {
        color: black !important;
        text-shadow: none !important;
    }
    .data-card {
        background-color: rgba(48, 167, 215, 0.15);
        border-left: 5px solid #30A7D7;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
    }
    .stats-box {
        background-color: rgba(0, 0, 0, 0.05);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid rgba(0, 0, 0, 0.1);
    }
    .evo-tag {
        background-color: #FFCC00;
        color: black !important;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Título TURIDEX en el cuadro superior negro
st.markdown("""
<div class='pokedex-title-box'>
    <h1 class='pokedex-title'>TURIDEX</h1>
</div>
""", unsafe_allow_html=True)

# Cliente de Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Error: Configura tu GROQ_API_KEY en los Secrets.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

# --- CUERPO DE LA APP ---
with st.container():
    st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
    
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        st.markdown("<h3 class='stMarkdown'>📸 Escáner</h3>", unsafe_allow_html=True)
        archivo = st.file_uploader("", type=["jpg", "png", "jpeg"])
        if archivo:
            st.image(PIL.Image.open(archivo), use_container_width=True)
            analizar = st.button("🔍 INICIAR ANÁLISIS")
    
    if archivo and analizar:
        with st.spinner("⏳ Turidex analizando datos..."):
            try:
                base_4_img = encode_image(archivo)
                prompt = """Actúa como un Crítico de Élite y Analista Científico para TURIDEX. 
                Identifica el objeto, plato o lugar.
                CRÍTICO: Si es comida rápida/chatarra, Salud < 15.
                
                Responde EXACTAMENTE en este formato:
                NOMBRE: [Nombre]
                TIPO: [Categoría]
                DESC: [Breve descripción]
                HISTORIA: [Historia detallada de 2 párrafos]
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

                # --- RENDERIZADO EN COL_INFO (TODO EN NEGRO) ---
                with col_info:
                    st.markdown(f"<h2>📋 {nombre}</h2>", unsafe_allow_html=True)
                    st.markdown(f"<div class='data-card'><p><b>{tipo.upper()}</b><br>{desc}</p></div>", unsafe_allow_html=True)
                    
                    st.markdown("<h3>📖 Origen y Detalles</h3>", unsafe_allow_html=True)
                    st.markdown(f"<p>{historia}</p>", unsafe_allow_html=True)
                    
                    st.markdown("<h3>📊 Análisis de Puntos Base</h3>", unsafe_allow_html=True)
                    labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
                    if "animal" in tipo.lower(): labels = ["🐾 Fuerza", "⚡ Agilidad", "❤️ Ternura", "💎 Rareza"]
                    if "lugar" in tipo.lower() or "obra" in tipo.lower(): labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
                    
                    st.markdown("<div class='stats-box'>", unsafe_allow_html=True)
                    c_a, c_b = st.columns(2)
                    with c_a:
                        st.markdown(f"<p><b>{labels[0]}: {nums[0]}%</b></p>", unsafe_allow_html=True)
                        st.progress(nums[0]/100)
                        st.markdown(f"<p><b>{labels[1]}: {nums[1]}%**</p>", unsafe_allow_html=True)
                        st.progress(nums[1]/100)
                    with c_b:
                        st.markdown(f"<p><b>{labels[2]}: {nums[2]}%**</p>", unsafe_allow_html=True)
                        st.progress(nums[2]/100)
                        st.markdown(f"<p><b>{labels[3]}: {nums[3]}%**</p>", unsafe_allow_html=True)
                        st.progress(nums[3]/100)
                    st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("<h3>🔄 Variantes</h3>", unsafe_allow_html=True)
                    if evos_raw and evos_raw != "No disponible":
                        for e in evos_raw.split(","):
                            st.markdown(f"<span class='evo-tag'>{e.strip()}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<p>No se registran variantes.</p>", unsafe_allow_html=True)

                # Audio
                tts = gTTS(text=f"{nombre}. {desc}. {historia}", lang='es')
                fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)

            except Exception as e:
                st.error(f"Error técnico en Turidex: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
