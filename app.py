import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import requests
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX: Identificador Inteligente")
st.write("Visión Multi-IA para viajeros")

# --- CONEXIÓN A LAS IAS (Usando Secrets) ---
# Intentamos conectar con los modelos más recientes de 2026
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Usamos el alias estable que Google mantiene actualizado automáticamente
    model_gemini = genai.GenerativeModel('models/gemini-2.5-flash')
    
    API_URL_HF = "https://api-inference.huggingface.co/models/calendari/food-image-classification"
    headers_hf = {"Authorization": f"Bearer {st.secrets['HUGGINGFACE_API_KEY']}"}
except Exception as e:
    st.error(f"Error de configuración: {e}")

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

def consulta_huggingface(img_pil):
    import io
    img_bytes = io.BytesIO()
    img_pil.save(img_bytes, format='JPEG')
    img_bytes = img_bytes.getvalue()
    response = requests.post(API_URL_HF, headers=headers_hf, data=img_bytes)
    return response.json()

# --- INTERFAZ DE USUARIO ---
archivo_subido = st.file_uploader("Sube una foto de comida o lugar...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido)
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 ANALIZAR CON TURIDEX"):
        with st.status("🚀 Analizando con Multi-Visión...", expanded=True) as status:
            texto_full = ""
            nombre_solo = "comida"
            metodo_ia = ""

            # INTENTO 1: Google Gemini (Modelo 2.5 Flash)
            try:
                status.write("📡 Consultando IA Principal (Google 2.5)...")
                prompt = """Identifica el objeto. Responde estrictamente:
                NOMBRE: [Nombre]
                HISTORIA: [Historia breve y curiosa]
                DATO: [Dato curioso]"""
                response = model_gemini.generate_content([prompt, imagen])
                texto_full = response.text
                metodo_ia = "Google Gemini 2.5"
                
                lineas = texto_full.split('\n')
                for l in lineas:
                    if "NOMBRE:" in l:
                        nombre_solo = l.replace("NOMBRE:", "").strip()

            # INTENTO 2: Respaldo por saturación o error de modelo
            except Exception as e:
                status.write("⚠️ Google no disponible. Activando IA de Respaldo...")
                try:
                    resultado_hf = consulta_huggingface(imagen)
                    if resultado_hf and isinstance(resultado_hf, list) and 'label' in resultado_hf[0]:
                        nombre_solo = resultado_hf[0]['label']
                        texto_full = f"NOMBRE: {nombre_solo.title()}\nHISTORIA: Identificado por sistema de respaldo.\nDATO: ¡Disfruta tu descubrimiento!"
                        metodo_ia = "Hugging Face"
                    else:
                        texto_full = "No se pudo identificar con ninguna IA."
                except:
                    texto_full = "Error en todos los sistemas."

            # --- RESULTADOS ---
            if texto_full and "Error" not in texto_full:
                status.update(label=f"✅ ¡Identificado por {metodo_ia}!", state="complete", expanded=False)
                st.subheader(f"📍 {nombre_solo.title()}")
                st.write(texto_full)
                
                busqueda = f"donde+comer+{nombre_solo.replace(' ', '+')}+restaurantes"
                link = f"https://www.google.com/maps/search/{busqueda}"
                st.link_button(f"🍴 BUSCAR {nombre_solo.upper()} CERCA", link)
                
                texto_voz = limpiar_texto(texto_full)
                tts = gTTS(text=texto_voz, lang='es')
                tts.save("voz.mp3")
                st.audio("voz.mp3")
            else:
                status.update(label="❌ Fallo total", state="error")
                st.error("No se pudo procesar la imagen. Intenta de nuevo en unos segundos.")
