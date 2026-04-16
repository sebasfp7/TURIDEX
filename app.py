import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="Turidex Elite", page_icon="📸", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .legible-text {
        color: white !important;
        text-shadow: 2px 2px 4px #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
    }
    .pokedex-title {
        font-family: 'Courier New', monospace; color: #FFCC00; text-align: center;
        text-shadow: 3px 3px 0 #000; font-size: 3.5em; padding: 10px;
    }
    .pokedex-frame {
        background-color: rgba(220, 10, 45, 0.95); border: 8px solid #8B0000;
        border-radius: 15px; padding: 25px; box-shadow: 10px 10px 0px rgba(0,0,0,0.4);
    }
    .data-card {
        background-color: rgba(48, 167, 215, 0.9); color: white; border-radius: 10px;
        padding: 15px; margin: 15px 0; border: 2px solid #1b7ba1; text-shadow: 1px 1px 2px #000;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='pokedex-title'>TURIDEX ELITE</h1>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Configura la API KEY.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
archivo = st.file_uploader("📸 Escáner Multimodal Activo...", type=["jpg", "png", "jpeg"])

if archivo:
    st.image(PIL.Image.open(archivo), width=240)
    
    if st.button("🔍 ANALIZAR OBJETIVO"):
        with st.spinner("⏳ Analizando texturas y procedencia..."):
            try:
                base64_image = encode_image(archivo)
                
                # --- IDENTIDAD DE IA MEJORADA (SUPER CHEF / CRÍTICO / EXPLORADOR) ---
                prompt = """Actúa como un Crítico Gastronómico de Élite y un Explorador Científico.
                Analiza la imagen con precisión quirúrgica.
                
                REGLAS DE IDENTIFICACIÓN:
                1. COMIDA: Diferencia papas fritas de totopos. Si ves salchicha y papa frita, es SALCHIPAPA.
                2. ANIMALES/LUGARES: Si es un perro, gato o paisaje, identifícalo con rigor biológico o geográfico.
                
                REGLAS DE STATS (Inflexibles):
                - COMIDA CHATARRA (Salchipapa, Pizza, Burger): Salud SIEMPRE < 20. Sabor SIEMPRE > 85.
                - LUGARES: Picante y Sabor son 0. Usa Cultura y Belleza.
                - ANIMALES: Sabor es 0. Usa Agilidad, Fuerza y Ternura.
                
                Responde en ESPAÑOL:
                NOMBRE: [Nombre]
                TIPO: [Categoría: Comida, Animal, Lugar, Objeto]
                DESC: [Resumen experto de 1 línea]
                HISTORIA: [Dos párrafos de contexto profundo]
                STATS: [Sabor/Fuerza, Picante/Agilidad, Salud/Cultura, Rareza] (4 números 0-100)
                EVOS: [3 Variantes o Evoluciones]"""

                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.4 # Balance entre rigor y variedad
                )
                
                res = chat.choices[0].message.content

                def extraer(clave, texto):
                    try:
                        return texto.split(clave + ":")[1].split("\n")[0].strip()
                    except: return "---"

                nombre = extraer("NOMBRE", res)
                tipo = extraer("TIPO", res).lower()
                desc = extraer("DESC", res)
                stats_raw = extraer("STATS", res)
                
                # Extraer números de forma limpia
                nums = [int(n) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: nums.append(0)

                # --- LÓGICA DINÁMICA DE ETIQUETAS ---
                if "animal" in tipo:
                    labels = ["🐾 Fuerza", "⚡ Agilidad", "❤️ Ternura", "💎 Rareza"]
                elif "lugar" in tipo or "paisaje" in tipo:
                    labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
                else: # Por defecto Comida
                    labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

                # --- INTERFAZ ---
                st.markdown(f"<h2 class='legible-text'>📋 {nombre}</h2>", unsafe_allow_html=True)
                st.markdown(f"<div class='data-card'>TIPO: {tipo.upper()}<br>{desc}</div>", unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**{labels[0]}: {nums[0]}%**"); st.progress(nums[0]/100)
                    st.write(f"**{labels[1]}: {nums[1]}%**"); st.progress(nums[1]/100)
                with col2:
                    st.write(f"**{labels[2]}: {nums[2]}%**"); st.progress(nums[2]/100)
                    st.write(f"**{labels[3]}: {nums[3]}%**"); st.progress(nums[3]/100)

                audio_text = f"{nombre}. {desc}. {res.split('HISTORIA:')[1].split('STATS:')[0]}"
                tts = gTTS(text=re.sub(r'[*#_]', '', audio_text), lang='es')
                fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)

            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("</div>", unsafe_allow_html=True)
