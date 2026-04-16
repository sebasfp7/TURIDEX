import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- 1. CONFIGURACIÓN Y ESTILO CSS (Inmersión Total) ---
st.set_page_config(page_title="Turidex", page_icon="📸", layout="wide")

# CSS para cambiar el fondo, estilar tarjetas y textos tipo Pokedex
st.markdown("""
<style>
    /* Fondo de pantalla: Mapa de aventura retro */
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    /* Título principal pixelado */
    .pokedex-title {
        font-family: 'Courier New', Courier, monospace;
        color: #FFCC00;
        text-align: center;
        text-shadow: 3px 3px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 1px 1px 0 #000;
        font-size: 3em;
        font-weight: bold;
        padding: 20px;
    }

    /* Contenedor principal de la ficha (Redondeado y rojo) */
    .pokedex-frame {
        background-color: #DC0A2D; /* Rojo Pokedex */
        border: 10px solid #8B0000;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 10px 10px 0px rgba(0,0,0,0.5);
        margin-bottom: 30px;
    }

    /* Caja de la Imagen (Marco blanco) */
    .pokedex-img-back {
        background-color: white;
        border: 5px solid #585858;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        width: 300px; /* Tamaño pequeño */
        margin: 0 auto;
    }

    /* Ficha de Datos (Caja azul como image_c058bd.png) */
    .pokedex-data-box {
        background-color: #30A7D7; /* Azul Datos */
        color: white;
        border-radius: 10px;
        padding: 15px;
        font-family: Arial, sans-serif;
        margin-top: 15px;
    }

    /* Sección Evoluciones/Presentaciones */
    .pokedex-evo-box {
        background-color: #585858;
        border-radius: 10px;
        padding: 15px;
        margin-top: 20px;
        color: white;
        text-align: center;
    }

    /* Botones estilo retro */
    .stButton>button {
        background-color: #FFCC00;
        color: black;
        border: 3px solid #000;
        font-family: 'Courier New', monospace;
        font-weight: bold;
        text-transform: uppercase;
        box-shadow: 4px 4px 0px #000;
    }
    .stButton>button:hover {
        background-color: #FFDD55;
        border: 3px solid #000;
    }
</style>
""", unsafe_allow_html=True)

# Título definitivo
st.markdown("<h1 class='pokedex-title'>TURIDEX</h1>", unsafe_allow_html=True)

# Cliente de Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Error: Configura tu GROQ_API_KEY en los Secrets.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

# --- 2. INTERFAZ DE SUBIDA ---
st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True) # Inicio Marco Rojo
archivo = st.file_uploader("📸 Enfoca tu objetivo...", type=["jpg", "png", "jpeg"])

if archivo:
    # Mostramos la imagen pequeña centrada con CSS
    st.markdown("<div class='pokedex-img-back'>", unsafe_allow_html=True)
    img_display = PIL.Image.open(archivo)
    st.image(img_display, width=280) # Imagen pequeña
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("🔍 ESCANEAR OBJETIVO"):
        with st.status("🚀 Procesando datos de la Pokedex...") as status:
            try:
                base64_image = encode_image(archivo)
                
                # PROMPT MAESTRO V3: Pedimos nombre, datos técnicos, stats y presentaciones
                prompt = """Identifica este plato o lugar. 
                Responde en ESPAÑOL con este formato exacto y sin introducciones:
                NOMBRE: [Nombre]
                DESCRIPCION_CORTA: [Una frase]
                CATEGORIA: [Ej: Comida > Italiana]
                HABILIDAD: [Ej: Sabor Intenso]
                HISTORIA: [Un párrafo largo]
                DATO: [Curiosidad]
                STATS: [4 números 1-100 para stats principales]
                PRESENTACIONES: [Nombres de 3 variantes, separadas por coma]"""

                chat_completion = client.chat.completions.create(
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }],
                    model="meta-llama/llama-4-scout-17b-16e-instruct", # O llama-3.2-90b-vision-preview
                )
                
                res_full = chat_completion.choices[0].message.content
                
                # --- PROCESAMIENTO DE DATOS ---
                try:
                    # Parseo avanzado para extraer cada campo
                    nombre = res_full.split("NOMBRE:")[1].split("\n")[0].strip()
                    desc_corta = res_full.split("DESCRIPCION_CORTA:")[1].split("\n")[0].strip()
                    categoria = res_full.split("CATEGORIA:")[1].split("\n")[0].strip()
                    habilidad = res_full.split("HABILIDAD:")[1].split("\n")[0].strip()
                    historia = res_full.split("HISTORIA:")[1].split("DATO:")[0].strip()
                    dato = res_full.split("DATO:")[1].split("STATS:")[0].strip()
                    stats_raw = res_full.split("STATS:")[1].split("PRESENTACIONES:")[0].strip()
                    presentaciones_raw = res_full.split("PRESENTACIONES:")[1].strip()

                    numeros_stats = [int(n.strip()) for n in stats_raw.split(",")]
                    variantes = [v.strip() for v in presentaciones_raw.split(",")]
                except:
                    # Fallback si el parseo falla
                    nombre, desc_corta, categoria, habilidad = "Desconocido", "Error de lectura", "???", "???"
                    historia, dato = "No se pudo recuperar la historia.", "---"
                    numeros_stats = [50, 50, 50, 50]
                    variantes = ["Margarita", "Pepperoni", "Hawaiana"]

                status.update(label="✅ Datos recuperados", state="complete")
                
                # --- 3. DISEÑO DE LA FICHA TÉCNICA (Como image_c058bd.png) ---
                st.markdown(f"<h2>{nombre}</h2>", unsafe_allow_html=True)
                
                st.markdown("<div class='pokedex-data-box'>", unsafe_allow_html=True)
                st.markdown(f"<p>{desc_corta}</p>", unsafe_allow_html=True)
                
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"🏷️ **Categoría:** {categoria}")
                with col_info2:
                    st.write(f"✨ **Habilidad:** {habilidad}")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("---")
                st.write(historia)
                st.info(f"💡 **Dato Curioso:** {dato}")

                # --- 4. PUNTOS BASE (Estadísticas dinámicas) ---
                st.markdown("---")
                st.subheader("📊 Puntos de Base (Stats)")
                
                if "plato" in categoria.lower() or "comida" in categoria.lower():
                    labels = ["🔥 Calorías", "🌶️ Picante", "💪 Proteína", "⭐ Popularidad"]
                else:
                    labels = ["🏛️ Antigüedad", "🧗 Altura", "🌤️ Clima", "💎 Rareza"]

                col_stat1, col_stat2 = st.columns(2)
                with col_stat1:
                    st.write(labels[0])
                    st.progress(numeros_stats[0] / 100)
                    st.write(labels[1])
                    st.progress(numeros_stats[1] / 100)
                with col_stat2:
                    st.write(labels[2])
                    st.progress(numeros_stats[2] / 100)
                    st.write(labels[3])
                    st.progress(numeros_stats[3] / 100)
                
                # --- 5. OTRAS PRESENTACIONES (Estilo image_c058de.png) ---
                st.markdown("---")
                st.markdown("<div class='pokedex-evo-box'>", unsafe_allow_html=True)
                st.subheader("🔄 Otras Presentaciones")
                
                col_evo1, col_arrow1, col_evo2, col_arrow2, col_evo3 = st.columns([2, 1, 2, 1, 2])
                
                with col_evo1:
                    st.markdown(f"<div style='background:white;color:black;border-radius:50%;padding:20px;border:3px solid black;'>{variantes[0]}</div>", unsafe_allow_html=True)
                with col_arrow1:
                    st.markdown("<h1 style='color:white;text-align:center;'>➡️</h1>", unsafe_allow_html=True)
                with col_evo2:
                    st.markdown(f"<div style='background:white;color:black;border-radius:50%;padding:20px;border:3px solid black;'>{variantes[1]}</div>", unsafe_allow_html=True)
                with col_arrow2:
                    st.markdown("<h1 style='color:white;text-align:center;'>➡️</h1>", unsafe_allow_html=True)
                with col_evo3:
                    st.markdown(f"<div style='background:white;color:black;border-radius:50%;padding:20px;border:3px solid black;'>{variantes[2]}</div>", unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True) # Fin Evo Box

                # --- 6. ACCIONES FINALIZADAS ---
                st.markdown("---")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    st.link_button(f"📍 MAPA DE {nombre.upper()}", f"https://www.google.com/maps/search/{nombre.replace(' ', '+')}")
                with col_btn2:
                    texto_audio = f"{nombre}. {desc_corta}. {historia}"
                    tts = gTTS(text=limpiar_texto(texto_audio), lang='es')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, format="audio/mp3")

            except Exception as e:
                st.error(f"Error en los circuitos de la Pokédex: {e}")

st.markdown("</div>", unsafe_allow_html=True) # Fin Marco Rojo Pokedex
