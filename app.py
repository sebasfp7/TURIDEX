import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re

# Intentamos importar Groq, si falla avisamos al usuario
try:
    from groq import Groq
except ImportError:
    st.error("Falta la librería 'groq' en requirements.txt")

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Turidex Pro", page_icon="📸")
st.title("📸 TURIDEX: El Escáner Inteligente")
st.markdown("---")

# --- CONEXIÓN A LAS LLAVES (SECRETS) ---
try:
    # Google (Para ver la imagen)
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model_google = genai.GenerativeModel('gemini-1.5-flash')
    
    # Groq (Para la historia larga y rápida)
    client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Error en las llaves de acceso. Revisa los Secrets de Streamlit.")

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

# --- INTERFAZ DE USUARIO ---
archivo = st.file_uploader("Sube una foto de comida o lugar...", type=["jpg", "png", "jpeg"])

if archivo:
    img = PIL.Image.open(archivo).convert("RGB")
    st.image(img, use_container_width=True)
    
    if st.button("🔍 ANALIZAR CON TURIDEX"):
        with st.status("🚀 Procesando con Multi-IA...", expanded=True) as status:
            nombre_identificado = ""
            res_final = ""

            # PASO 1: Identificar el nombre (Usando Google)
            try:
                status.write("🕵️ Google está mirando la foto...")
                prompt_nombre = "Responde solo el nombre de lo que ves (2-3 palabras)."
                res_google = model_google.generate_content([prompt_nombre, img])
                nombre_identificado = res_google.text.strip()
            except Exception:
                status.write("⚠️ Google saturado. Usando identificación genérica...")
                nombre_identificado = "Plato Tradicional"

            # PASO 2: Generar historia larga (Usando Groq)
            if nombre_identificado:
                try:
                    status.write(f"📖 Groq está redactando la historia de: {nombre_identificado}...")
                    prompt_historia = f"""Actúa como un guía turístico experto. 
                    Escribe una historia LARGA (2 párrafos) y un DATO CURIOSO sobre: {nombre_identificado}.
                    Usa este formato:
                    NOMBRE: {nombre_identificado}
                    HISTORIA: [Texto detallado]
                    DATO: [Curiosidad sorprendente]"""
                    
                    completion = client_groq.chat.completions.create(
                        messages=[{"role": "user", "content": prompt_historia}],
                        model="llama-3.3-70b-versatile",
                    )
                    res_final = completion.choices[0].message.content
                except Exception:
                    status.write("📡 Groq falló, usando respuesta de emergencia...")
                    res_final = f"NOMBRE: {nombre_identificado}\nHISTORIA: No se pudo conectar con el servidor de historias, pero este es un plato icónico que debes probar.\nDATO: ¡Busca un restaurante local para más detalles!"

            # --- MOSTRAR RESULTADOS ---
            if res_final:
                status.update(label="✅ ¡Análisis completo!", state="complete", expanded=False)
                st.markdown(res_final)
                
                # Mapa
                query_mapa = nombre_identificado.replace(" ", "+")
                link_mapa = f"https://www.google.com/maps/search/{query_mapa}+cerca+de+mi"
                st.link_button(f"📍 BUSCAR {nombre_identificado.upper()} CERCA", link_mapa)
                
                # Audio
                with st.spinner("Generando audio..."):
                    audio_texto = limpiar_texto(res_final)
                    tts = gTTS(text=audio_texto, lang='es')
                    tts.save("voz.mp3")
                    st.audio("voz.mp3")
            else:
                st.error("No se pudo procesar la solicitud. Intenta en unos segundos.")

st.info("💡 Consejo: Si sale error de conexión, es que los servidores gratuitos están al límite. Espera 10 segundos.")
