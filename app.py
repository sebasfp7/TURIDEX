import streamlit as st
import google.generativeai as genai
try:
    from groq import Groq
except ImportError:
    st.error("Falta 'groq' en requirements.txt")

import PIL.Image
from gtts import gTTS
import os
import re
import requests # Necesario para la IA de respaldo

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Turidex Pro", page_icon="📸")
st.title("📸 TURIDEX: El Escáner Inteligente")
st.markdown("---")

# --- CONEXIÓN A LAS LLAVES (SECRETS) ---
try:
    # Google (IA Principal)
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model_google = genai.GenerativeModel('gemini-1.5-flash')
    
    # Groq (Cerebro rápido)
    client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    # Hugging Face (Ojos de Emergencia - Modelo Open Source de visión)
    # Usaremos el modelo de Google VIT que es excelente y gratuito en HF
    API_URL_HF = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"
    headers_hf = {"Authorization": f"Bearer {st.secrets['HUGGINGFACE_API_KEY']}"}
except Exception as e:
    st.error(f"Error en Secrets: {e}")

# Funciones de utilidad
def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

def consulta_huggingface(img_pil):
    import io
    img_bytes = io.BytesIO()
    img_pil.save(img_bytes, format='JPEG')
    data = img_bytes.getvalue()
    response = requests.post(API_URL_HF, headers=headers_hf, data=data)
    return response.json()

# --- INTERFAZ DE USUARIO ---
archivo = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo:
    # Abrimos la imagen y la convertimos a RGB para evitar errores de formato
    img = PIL.Image.open(archivo).convert("RGB")
    st.image(img, use_container_width=True)
    
    if st.button("🔍 ANALIZAR CON TURIDEX"):
        with st.status("🚀 Procesando con Multi-IA...", expanded=True) as status:
            nombre_identificado = ""
            res_final = ""
            metodo_vision = ""

            # PASO 1: Identificar el nombre (Usando Google)
            try:
                status.write("🕵️ Google está mirando la foto...")
                prompt_nombre = "Responde solo el nombre de lo que ves (2-3 palabras)."
                res_google = model_google.generate_content([prompt_nombre, img])
                nombre_identificado = res_google.text.strip()
                metodo_vision = "Google Gemini"
            except Exception:
                status.write("⚠️ Google saturado. Activando ojos de emergencia (Hugging Face Open Source)...")
                try:
                    # Usamos la IA de respaldo para identificar el nombre
                    resultado_hf = consulta_huggingface(img)
                    # Tomamos el primer resultado (más probable)
                    if resultado_hf and isinstance(resultado_hf, list) and 'label' in resultado_hf[0]:
                        nombre_identificado = resultado_hf[0]['label']
                        metodo_vision = "Hugging Face"
                    else:
                        nombre_identificado = "Plato Tradicional"
                except:
                    nombre_identificado = "Plato Tradicional"

            # PASO 2: Generar historia larga (Usando Groq)
            if nombre_identificado and "Plato" not in nombre_identificado:
                try:
                    status.write(f"📖 Groq está redactando la historia de: {nombre_identificado.title()}...")
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
                    res_final = f"NOMBRE: {nombre_identificado}\nHISTORIA: No se pudo conectar con el cerebro de historias.\nDATO: ¡Parece delicioso!"

            # --- MOSTRAR RESULTADOS ---
            if res_final:
                status.update(label=f"✅ ¡Análisis completo (Visto por {metodo_vision})!", state="complete", expanded=False)
                st.markdown(res_final)
                
                # Mapa
                query_mapa = nombre_identificado.replace(" ", "+")
                link_mapa = f"https://www.google.com/maps/search/{query_mapa}+restaurantes"
                st.link_button(f"📍 BUSCAR {nombre_identificado.upper()} CERCA", link_mapa)
                
                # Audio
                audio_texto = limpiar_texto(res_final)
                tts = gTTS(text=audio_texto, lang='es')
                tts.save("voz.mp3")
                st.audio("voz.mp3")
            else:
                st.error("Todos los cerebros están ocupados. Intenta en 10 segundos.")
