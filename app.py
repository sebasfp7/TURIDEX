import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX OFICIAL")
st.write("Identifica lugares y comida con IA")

# --- CONFIGURACIÓN DE IA (Usando el modelo exacto que te funciona) ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Usamos el nombre exacto que me confirmaste
model = genai.GenerativeModel('models/gemini-2.5-flash')

# Función para limpiar el texto para el audio (quita asteriscos)
def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

# --- INTERFAZ DE USUARIO ---
archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido)
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 ANALIZAR CON TURIDEX"):
        with st.spinner("Turidex pensando..."):
            try:
                # Prompt optimizado
                prompt = """Identifica el objeto de la imagen. 
                Responde estrictamente en este formato:
                NOMBRE: [Nombre corto y simple del plato o lugar]
                HISTORIA: [Breve historia]
                DATO: [Dato curioso]"""
                
                response = model.generate_content([prompt, imagen])
                texto_full = response.text
                
                # 1. Extraer solo el nombre para la búsqueda de Google Maps
                lineas = texto_full.split('\n')
                nombre_solo = "comida" 
                for l in lineas:
                    if "NOMBRE:" in l:
                        nombre_solo = l.replace("NOMBRE:", "").strip()
                
                # 2. Mostrar resultados en la App
                st.success("¡Análisis completado!")
                st.write(texto_full)
                
                # 3. Lógica de Mapa Optimizada
                termino_busqueda = f"donde+comer+{nombre_solo.replace(' ', '+')}+o+restaurantes+de+{nombre_solo.replace(' ', '+')}"
                link_maps = f"https://www.google.com/maps/search/{termino_busqueda}+cerca+de+mi"
                
                st.link_button(f"📍 BUSCAR {nombre_solo.upper()} CERCA", link_maps)
                
                # 4. Generación de Audio limpia
                texto_para_audio = limpiar_texto(texto_full)
                tts = gTTS(text=texto_para_audio, lang='es')
                tts.save("voz.mp3")
                st.audio("voz.mp3")

            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    st.error("⚠️ Google está un poco saturado. Espera 30 segundos y vuelve a intentarlo.")
                else:
                    st.error(f"Hubo un error: {e}")

st.info("Nota: Esta es una versión prototipo de Turidex.")
