import streamlit as st
import google.generativeai as genai
try:
    from groq import Groq
except ImportError:
    st.error("Por favor, añade 'groq' a tu archivo requirements.txt en GitHub")

import PIL.Image
from gtts import gTTS
import os
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex Pro", page_icon="📸")
st.title("📸 TURIDEX: Inteligencia Total")

# Configurar Google
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model_google = genai.GenerativeModel('gemini-1.5-flash')

# Configurar Groq (El respaldo)
try:
    client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.warning("Configura tu GROQ_API_KEY en los Secrets para tener respaldo.")

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

archivo = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo:
    img = PIL.Image.open(archivo).convert("RGB")
    st.image(img, use_container_width=True)
    
    if st.button("🔍 ANALIZAR AHORA"):
        with st.status("🚀 Buscando en múltiples cerebros...") as status:
            res_final = ""
            nombre_identificado = ""
            
            # --- PASO 1: IDENTIFICAR EL NOMBRE (Google) ---
            try:
                status.write("🕵️ Identificando plato con Google...")
                res_nombre = model_google.generate_content(["Dime solo el nombre de este plato en 2 palabras.", img])
                nombre_identificado = res_nombre.text.strip()
            except Exception:
                status.write("⚠️ Google saturado. Intentando otro camino...")

            # --- PASO 2: OBTENER HISTORIA LARGA (Groq) ---
            if nombre_identificado:
                try:
                    status.write(f"📖 Buscando historia de {nombre_identificado} en Groq...")
                    prompt_historia = f"""Actúa como un experto guía turístico. 
                    Háblame extensamente sobre: {nombre_identificado}. 
                    Dame 2 párrafos de HISTORIA y 1 párrafo de un DATO CURIOSO sorprendente.
                    Usa este formato:
                    NOMBRE: {nombre_identificado}
                    HISTORIA: [Tu texto largo aquí]
                    DATO: [Tu dato curioso aquí]"""
                    
                    chat_completion = client_groq.chat.completions.create(
                        messages=[{"role": "user", "content": prompt_historia}],
                        model="llama-3.3-70b-versatile",
                    )
                    res_final = chat_completion.choices[0].message.content
                except Exception:
                    # Si Groq falla, le pedimos todo a Google aunque sea corto
                    status.write("📡 Groq no disponible, volviendo a Google...")
                    res_google = model_google.generate_content(["Identifica y dame historia larga y dato curioso.", img])
                    res_final = res_google.text

            # --- MOSTRAR RESULTADOS ---
            if res_final:
                status.update(label="✅ ¡Análisis completado!", state="complete")
                st.markdown(res_final)
                
                # Mapa
                link = f"https://www.google.com/maps/search/{nombre_identificado.replace(' ', '+')}+cerca+de+mi"
                st.link_button(f"📍 BUSCAR {nombre_identificado.upper()} CERCA", link)
                
                # Audio
                audio_texto = limpiar_texto(res_final)
                tts = gTTS(text=audio_texto, lang='es')
                tts.save("voz.mp3")
                st.audio("voz.mp3")
            else:
                st.error("Todos los cerebros están ocupados. Intenta en 10 segundos.")
