import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Turidex", page_icon="📸", layout="wide")

# CSS: Máxima legibilidad con sombras y marcos retro
st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    /* Estilo de texto 'Pokédex Inmersiva' */
    .legible-text {
        color: white !important;
        text-shadow: 2px 2px 4px #000000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
        font-family: 'Courier New', monospace;
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
        background-color: rgba(220, 10, 45, 0.95);
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
    }
    /* Asegurar que h2 y h3 sean legibles */
    .stMarkdown h2, .stMarkdown h3 {
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
    """Codifica la imagen para enviarla a la API."""
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
archivo = st.file_uploader("📸 Escaneando objetivo...", type=["jpg", "png", "jpeg"])

if archivo:
    st.markdown("<div class='img-container'>", unsafe_allow_html=True)
    st.image(PIL.Image.open(archivo), width=240)
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🔍 INICIAR ESCÁNER"):
        with st.spinner("⏳ Analizando con Llama 4 Scout (Prompt Sincero)..."):
            try:
                base64_image = encode_image(archivo)
                
                # --- PROMPT REFORZADO: El ajuste de tuercas ---
                prompt = """Actúa como una Pokédex. Analiza la imagen.
                STATS CRÍTICOS: Sé realista e inflexible con la lógica nutricional.
                - Si detectas fritura masiva, grasa excesiva o comida chatarra (como salchipapas, pizzas, burgers), el Stat de SALUD debe ser obligatoriamente MENOR a 15.
                - Si es ensalada o fruta, Salud > 90.
                - Si es un lugar, Sabor=0 y Salud=0, evalúa Rareza y Antigüedad.
                
                Responde en ESPAÑOL con este formato:
                NOMBRE: [Nombre]
                TIPO: [Categoría]
                DESC: [Descripción breve de una línea]
                HISTORIA: [Dos párrafos detallados sobre origen y cultura]
                STATS: [Sabor, Picante, Salud, Rareza - Dame 4 números de 0 a 100 separados por comas]
                EVOS: [3 versiones alternativas separated by commas]"""

                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    # MODELO FIJO (llama-4-scout-17b-16e-instruct)
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.7 # Temperatura media para balancear creatividad y lógica
                )
                
                res = chat.choices[0].message.content

                # --- EXTRACCIÓN ROBUSTA DE DATOS ---
                def extraer(clave, texto):
                    try:
                        parte = texto.split(clave + ":")[1]
                        # Buscar la siguiente clave para cortar
                        for k in ["NOMBRE", "TIPO", "DESC", "HISTORIA", "STATS", "EVOS"]:
                            if k + ":" in parte:
                                parte = parte.split(k + ":")[0]
                        return parte.strip()
                    except:
                        return "---"

                nombre = extraer("NOMBRE", res)
                tipo = extraer("TIPO", res)
                desc = extraer("DESC", res)
                historia = extraer("HISTORIA", res)
                stats_raw = extraer("STATS", res)
                evos_raw = extraer("EVOS", res)

                # Procesamiento de Stats
                try:
                    # Buscamos cualquier número en la línea de STATS
                    numeros_encontrados = re.findall(r'\d+', stats_raw)
                    # Tomamos los primeros 4 y rellenamos si faltan
                    nums = [int(n) for n in numeros_encontrados][:4]
                    while len(nums) < 4:
                        nums.append(0)
                except:
                    # Stats de fallback si el parseo falla (raro con Llama 4)
                    nums = [50, 0, 5, 10]

                # Procesamiento de Presentaciones
                evos = evos_raw.split(",") if "," in evos_raw else ["Normal", "Especial", "Premium"]

                # --- DISPLAY DE RESULTADOS ---
                st.markdown(f"<h2 class='legible-text'>📋 {nombre}</h2>", unsafe_allow_html=True)
                
                st.markdown(f"<div class='data-card'>TIPO: {tipo}<br><i>{desc}</i></div>", unsafe_allow_html=True)
                
                st.markdown(f"<p class='legible-text'>{historia}</p>", unsafe_allow_html=True)

                st.markdown("<h3 class='legible-text'>📊 Puntos Base (Análisis Sincero)</h3>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                
                # Etiquetas dinámicas según el tipo
                if "comida" in tipo.lower() or "plato" in tipo.lower() or "salchi" in nombre.lower():
                    labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]
                else:
                    labels = ["🏛️ Edad", "🧗 Altura", "🌤️ Clima", "💎 Rareza"]

                with c1:
                    # El color de la barra cambiará dinámicamente según el valor
                    st.write(f"**{labels[0]}: {nums[0]}%**")
                    st.progress(nums[0]/100)
                    st.write(f"**{labels[1]}: {nums[1]}%**")
                    st.progress(nums[1]/100)
                with c2:
                    st.write(f"**{labels[2]}: {nums[2]}%**")
                    # La barra de salud ahora debe ser baja para salchipapas
                    st.progress(nums[2]/100)
                    st.write(f"**{labels[3]}: {nums[3]}%**")
                    st.progress(nums[3]/100)

                st.markdown("<h3 class='legible-text'>🔄 Otras Presentaciones</h3>", unsafe_allow_html=True)
                ec = st.columns(3)
                for i, col in enumerate(ec):
                    if i < len(evos):
                        with col:
                            st.markdown(f"<div class='evo-card'>{evos[i].strip()}</div>", unsafe_allow_html=True)

                # Generar audio automático con la historia
                audio_text = f"{nombre}. {tipo}. {desc}. {historia}"
                tts = gTTS(text=re.sub(r'[*#_]', '', audio_text), lang='es')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)

            except Exception as e:
                st.error(f"Error técnico en el escáner: {e}")
                st.info("💡 Asegúrate de que tu GROQ_API_KEY sea correcta en los Secrets.")

st.markdown("</div>", unsafe_allow_html=True)
