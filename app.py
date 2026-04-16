import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="TURIDEX", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .pokedex-frame {
        background-color: rgba(255, 255, 255, 0.92);
        border: 4px solid #DC0A2D;
        border-radius: 20px;
        padding: 25px;
    }
    .pokedex-title-box {
        background-color: #000000;
        border: 4px solid #DC0A2D;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .pokedex-title { color: #FFFFFF !important; font-family: 'Courier New', monospace; font-size: 3em; margin: 0; }
    /* TEXTO NEGRO INTEGRAL */
    .black-text, p, h1, h2, h3, span, label, div { color: #000000 !important; font-weight: 600; }
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
        padding: 6px 14px;
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
    st.error("Error: Configura la API KEY.")

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
        with st.spinner("Analizando con Inteligencia TURIDEX..."):
            try:
                img_b64 = encode_image(archivo)
                # PROMPT MAESTRO BLINDADO
                prompt = """Eres el sistema de reconocimiento TURIDEX. Tu análisis debe ser infalible.
                
                CONOCIMIENTO BASE:
                - SALCHIPAPA: Contiene papas fritas alargadas y trozos de salchicha. NO son nachos.
                - NACHOS: Son triángulos de tortilla de maíz con queso. NO son salchipapas.
                
                INSTRUCCIONES DE CATEGORÍA:
                1. Clasifica en: [COMIDA, ANIMAL, LUGAR].
                2. Si es COMIDA: Stats = [Sabor, Picante, Salud, Rareza]. Salud < 15 si es frito/chatarra.
                3. Si es ANIMAL: Stats = [Fuerza, Agilidad, Peligro, Rareza]. Variantes = otros animales de la misma familia.
                4. Si es LUGAR: Stats = [Historia, Belleza, Cultura, Rareza].
                
                RESPONDE ESTRICTAMENTE:
                NOMBRE: [Nombre]
                CATEGORIA: [COMIDA, ANIMAL o LUGAR]
                DESC: [Breve descripción]
                HISTORIA: [2 párrafos de contexto real]
                STATS: [Valor1, Valor2, Valor3, Valor4] (0-100)
                EVOS: [Variante1, Variante2, Variante3]"""

                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.1 # Bajamos la temperatura para que no invente
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
                    st.markdown(f"<div class='data-card'><p><b>CATEGORÍA:</b> {cat}</p><p>{desc}</p></div>", unsafe_allow_html=True)
                    
                    st.markdown("### 📖 Historia")
                    st.markdown(f"<p>{historia}</p>", unsafe_allow_html=True)
                    
                    # ASIGNACIÓN DE ETIQUETAS SIN ERRORES
                    if "ANIMAL" in cat:
                        labels = ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
                    elif "LUGAR" in cat:
                        labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
                    else: # COMIDA
                        labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

                    st.markdown(f"### 📊 Puntos Base")
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

                    st.markdown("### 🔄 Variantes Registradas")
                    for e in evos_raw.split(","):
                        if e.strip() and e.strip() != "---":
                            st.markdown(f"<span class='evo-tag'>{e.strip()}</span>", unsafe_allow_html=True)

                tts = gTTS(text=f"{nombre}. {historia}", lang='es')
                fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)

            except Exception as e:
                st.error(f"Error técnico: {e}")
    st.markdown("</div>", unsafe_allow_html=True)
