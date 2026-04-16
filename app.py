import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 Bienvenido a TURIDEX")
st.write("Identifica lugares y comida con IA")

# --- CONFIGURACIÓN DE IA ---
# Aquí usaremos un truco de seguridad después, por ahora pon tu llave:
genai.configure(api_key="TU_API_KEY_AQUI")
model = genai.GenerativeModel('gemini-1.5-flash')

# --- INTERFAZ DE USUARIO ---
archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido)
    st.image(imagen, caption="Tu foto subida", use_column_width=True)
    
    if st.button("🔍 ANALIZAR CON TURIDEX"):
        with st.spinner("Escaneando..."):
            # 1. IA de Visión
            instruccion = "Eres Turidex. Identifica esto y dame Nombre, Historia y Dato Curioso en 4 líneas."
            response = model.generate_content([instruccion, imagen])
            texto_resultado = response.text
            
            st.success("¡Identificado!")
            st.write(texto_resultado)
            
            # 2. Voz del Robot
            tts = gTTS(text=texto_resultado, lang='es')
            tts.save("voz.mp3")
            st.audio("voz.mp3")
            
            # 3. Botón de Mapas
            nombre_objeto = texto_resultado.split('\n')[0].replace("Nombre:", "").strip()
            link_maps = f"https://www.google.com/maps/search/{nombre_objeto}+cerca+de+mi"
            st.link_button("📍 VER EN GOOGLE MAPS", link_maps)

st.info("Nota: Esta es una versión prototipo de Turidex.")
