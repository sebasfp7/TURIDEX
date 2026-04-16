import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX OFICIAL")

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# Función para limpiar el texto para el audio
def limpiar_texto(t):
    # Quita asteriscos y símbolos raros
    return re.sub(r'[*#_]', '', t)

archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido)
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 ANALIZAR"):
        with st.spinner("Turidex pensando..."):
            # Pedimos el nombre separado para el mapa
            prompt = """Identifica el objeto. 
            Responde estrictamente en este formato:
            NOMBRE: [Nombre corto del plato]
            HISTORIA: [Breve historia]
            DATO: [Dato curioso]"""
            
            response = model.generate_content([prompt, imagen])
            texto_full = response.text
            
            # 1. Extraer solo el nombre para el mapa
            lineas = texto_full.split('\n')
            nombre_solo = "comida" # por defecto
            for l in lineas:
                if "NOMBRE:" in l:
                    nombre_solo = l.replace("NOMBRE:", "").strip()
            
            # 2. Mostrar texto y Botón de Mapa limpio
            st.success("¡Logrado!")
            st.write(texto_full)
            
            link_maps = f"https://www.google.com/maps/search/{nombre_solo.replace(' ', '+')}+cerca+de+mi"
            st.link_button(f"📍 BUSCAR {nombre_solo.upper()} CERCA", link_maps)
            
            # 3. Audio limpio (sin asteriscos)
            texto_limpio = limpiar_texto(texto_full)
            tts = gTTS(text=texto_limpio, lang='es')
            tts.save("voz.mp3")
            st.audio("voz.mp3")
