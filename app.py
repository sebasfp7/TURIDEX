import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX OFICIAL")
st.write("Identifica lugares y comida con IA")

# --- CONFIGURACIÓN DE IA ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('models/gemini-2.5-flash')

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido)
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 ANALIZAR CON TURIDEX"):
        progreso = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Conectando con el satélite de Turidex...")
        progreso.progress(25)
        
        exito = False
        intentos = 0
        while intentos < 2 and not exito:
            try:
                prompt = """Identifica el objeto. Responde estrictamente:
                NOMBRE: [Nombre]
                HISTORIA: [Historia]
                DATO: [Dato curioso]"""
                
                response = model.generate_content([prompt, imagen])
                texto_full = response.text
                exito = True # Si llega aquí, funcionó
                
            except Exception as e:
                intentos += 1
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    status_text.text("Línea ocupada... reintentando en 3 segundos...")
                    time.sleep(3) # Espera un poco para engañar al límite
                else:
                    st.error(f"Error inesperado: {e}")
                    break

        if exito:
            progreso.progress(100)
            status_text.text("¡Identificación exitosa!")
            
            lineas = texto_full.split('\n')
            nombre_solo = "comida" 
            for l in lineas:
                if "NOMBRE:" in l:
                    nombre_solo = l.replace("NOMBRE:", "").strip()
            
            st.success(f"Análisis de {nombre_solo} listo")
            st.write(texto_full)
            
            termino_busqueda = f"donde+comer+{nombre_solo.replace(' ', '+')}+o+restaurantes+de+{nombre_solo.replace(' ', '+')}"
            link_maps = f"https://www.google.com/maps/search/{termino_busqueda}+cerca+de+mi"
            st.link_button(f"📍 BUSCAR {nombre_solo.upper()} CERCA", link_maps)
            
            texto_para_audio = limpiar_texto(texto_full)
            tts = gTTS(text=texto_para_audio, lang='es')
            tts.save("voz.mp3")
            st.audio("voz.mp3")
        else:
            st.warning("Agotamos los intentos gratuitos por ahora. Por favor, intenta de nuevo en un minuto.")
