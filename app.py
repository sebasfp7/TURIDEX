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
        padding: 15px; margin: 10px 0; border: 2px solid #1b7ba1; text-shadow: 1px 1px 2px #000;
        font-size: 1.1em;
    }
    .stats-container {
        background-color: rgba(0, 0, 0, 0.7); border-radius: 10px; padding: 15px; margin-top: 10px;
    }
    .evo-card {
        background-color: #333; border: 2px solid #FFCC00; border-radius: 10px;
        padding: 10px; text-align: center; color: white; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='pokedex-title'>TURIDEX ELITE</h1>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Error: Configura tu GROQ_API_KEY en Secrets.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
archivo = st.file_uploader("📸 Escáner Multimodal Activo...", type=["jpg", "png", "jpeg"])

if archivo:
    st.image(PIL.Image.open(archivo), width=240)
    
    if st.button("🔍 ANALIZAR OBJETIVO"):
        with st.spinner("⏳ Analizando con rigor Gastronómico y Científico..."):
            try:
                base64_image = encode_image(archivo)
                
                prompt = """Actúa como un Crítico Gastronómico de Élite y un Explorador Científico.
                Analiza la imagen con precisión quirúrgica.
                
                REGLAS DE IDENTIFICACIÓN:
                1. COMIDA: Diferencia papas fritas de totopos. Si ves salchicha y papa frita, es SALCHIPAPA.
                2. ANIMALES/LUGARES: Identificación rigurosa.
                
                REGLAS DE STATS (Inflexibles):
                - COMIDA CHATARRA: Salud < 15. Sabor > 90.
                - ANIMALES: Sabor/Picante no aplican (pon 0). Usa Fuerza y Agilidad.
                
                Responde estrictamente en este formato:
                NOMBRE: [Nombre]
                TIPO: [Categoría]
                DESC: [Descripción de 1 línea]
                HISTORIA: [Dos párrafos detallados]
                STATS: [Valor1, Valor2, Valor3, Valor4] (4 números 0-100)
                EVOS: [Variante1, Variante2, Variante3]"""

                chat = client.chat.completions.create(
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.4
                )
                
                res = chat.choices[0].message.content

                # --- EXTRACCIÓN MEJORADA ---
                def get_field(field_name, text):
                    pattern = rf"{field_name}:\s*(.*?)(?=\n[A-Z]+:|$)"
                    match = re.search(pattern, text, re.DOTALL)
                    return match.group(1).strip() if match else "---"

                nombre = get_field("NOMBRE", res)
                tipo = get_field("TIPO", res)
                desc = get_field("DESC", res)
                historia = get_field("HISTORIA", res)
                stats_raw = get_field("STATS", res)
                evos_raw = get_field("EVOS", res)
                
                # Números de stats
                nums = [int(n) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: nums.append(0)

                # --- VISUALIZACIÓN DE DATOS (AQUÍ ESTABA EL FALLO) ---
                st.markdown(f"<h2 class='legible-text'>📋 {nombre}</h2>", unsafe_allow_html=True)
                
                st.markdown(f"<div class='data-card'><b>TIPO:</b> {tipo.upper()}<br><i>{desc}</i></div>", unsafe_allow_html=True)
                
                # Mostrar Historia explícitamente
                st.markdown("<h3 class='legible-text'>📖 Descripción y Origen</h3>", unsafe_allow_html=True)
                st.markdown(f"<div class='data-card' style='background-color: rgba(0,0,0,0.5);'>{historia}</div>", unsafe_allow_html=True)

                # Stats Dinámicos
                st.markdown("<h3 class='legible-text'>📊 Estadísticas de Análisis</h3>", unsafe_allow_html=True)
                if "animal" in tipo.lower():
                    labels = ["🐾 Fuerza", "⚡ Agilidad", "❤️ Ternura", "💎 Rareza"]
                elif "lugar" in tipo.lower():
                    labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
                else:
                    labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

                st.markdown("<div class='stats-container'>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**{labels[0]}: {nums[0]}%**"); st.progress(nums[0]/100)
                    st.write(f"**{labels[1]}: {nums[1]}%**"); st.progress(nums[1]/100)
                with c2:
                    st.write(f"**{labels[2]}: {nums[2]}%**"); st.progress(nums[2]/100)
                    st.write(f"**{labels[3]}: {nums[3]}%**"); st.progress(nums[3]/100)
                st.markdown("</div>", unsafe_allow_html=True)

                # Evoluciones
                st.markdown("<h3 class='legible-text'>🔄 Variantes Registradas</h3>", unsafe_allow_html=True)
                evos = evos_raw.split(",")
                ec = st.columns(3)
                for i, col in enumerate(ec):
                    if i < len(evos):
                        with col: st.markdown(f"<div class='evo-card'>{evos[i].strip()}</div>", unsafe_allow_html=True)

                # Audio
                audio_text = f"{nombre}. {tipo}. {desc}. {historia}"
                tts = gTTS(text=re.sub(r'[*#_]', '', audio_text), lang='es')
                fp = io.BytesIO(); tts.write_to_fp(fp); st.audio(fp)

            except Exception as e:
                st.error(f"Error en el escáner: {e}")

st.markdown("</div>", unsafe_allow_html=True)
