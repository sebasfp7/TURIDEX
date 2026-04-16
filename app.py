import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import requests
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX: Multi-IA Resiliente")

# --- CONFIGURACIÓN DE LLAVES ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Cambiamos a 1.5-flash: es el que tiene menos errores 404 y es muy rápido
    model_gemini = genai.GenerativeModel('gemini-1.5-flash')
    
    HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
    # Usamos un modelo de comida más robusto de Hugging Face
    API_URL_HF = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"
    headers_hf = {"Authorization": f"Bearer {HF_TOKEN}"}
except Exception as e:
    st.error(f"Error en Secrets: {e}")

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

def consulta_huggingface(img_pil):
    import io
    img_bytes = io.BytesIO()
    img_pil.save(img_bytes, format='JPEG')
    data = img_bytes.getvalue()
    
    # Intentos por si el modelo está dormido
    for _ in range(3):
        response = requests.post(API_URL_HF, headers=headers_hf, data=data)
        resultado = response.json()
        if isinstance(resultado, dict) and "estimated_time" in resultado:
            time.sleep(2) # Esperar si el modelo está cargando
            continue
        return resultado
    return None

archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido)
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 ANALIZAR AHORA"):
        with st.status("🚀 Procesando...", expanded=True) as status:
            texto_full = ""
            nombre_solo = ""

            # 1. INTENTO CON GOOGLE
            try:
                status.write("📡 Intentando con IA Principal...")
                prompt = "Identifica el objeto. NOMBRE: [Nombre], HISTORIA: [Breve], DATO: [Curiosidad]"
                response = model_gemini.generate_content([prompt, imagen])
                texto_full = response.text
                status.write("✅ Google respondió con éxito.")
            except Exception:
                # 2. INTENTO CON RESPALDO (Hugging Face)
                status.write("⚠️ Google saturado. Cambiando a IA de Respaldo...")
                res_hf = consulta_huggingface(imagen)
                if res_hf and isinstance(res_hf, list):
                    nombre_solo = res_hf[0]['label'].split(',')[0]
                    texto_full = f"NOMBRE: {nombre_solo}\nHISTORIA: Identificado por sistema de respaldo.\nDATO: ¡Parece delicioso!"
                    status.write("✅ Respaldo activado con éxito.")
                else:
                    status.write("❌ Ambos sistemas fallaron.")

            if texto_full:
                status.update(label="¡Proceso finalizado!", state="complete", expanded=False)
                st.write(texto_full)
                
                # Extraer nombre para el mapa
                match = re.search(r"NOMBRE:\s*(.*)", texto_full)
                nombre_mapa = match.group(1) if match else "Comida"
                
                link = f"https://www.google.com/maps/search/restaurantes+de+{nombre_mapa.replace(' ', '+')}"
                st.link_button(f"📍 BUSCAR {nombre_mapa.upper()} CERCA", link)
                
                audio_limpio = limpiar_texto(texto_full)
                tts = gTTS(text=audio_limpio, lang='es')
                tts.save("voz.mp3")
                st.audio("voz.mp3")
            else:
                st.error("Lo siento, los servidores gratuitos están llenos. Intenta en 10 segundos.")
