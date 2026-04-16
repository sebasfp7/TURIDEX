import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import requests
import time
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX: Multi-IA Ultra")

# --- CONFIGURACIÓN DE LLAVES ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Intentamos con 1.5-flash-latest que suele tener cuotas separadas
    model_gemini = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
    # Cambiamos a un modelo de Microsoft que es más rápido y estable en HF
    API_URL_HF = "https://api-inference.huggingface.co/models/microsoft/resnet-50"
    headers_hf = {"Authorization": f"Bearer {HF_TOKEN}"}
except Exception as e:
    st.error(f"Error en configuración: {e}")

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

def consulta_huggingface(img_pil):
    img_rgb = img_pil.convert("RGB")
    img_bytes = io.BytesIO()
    img_rgb.save(img_bytes, format='JPEG')
    data = img_bytes.getvalue()
    
    try:
        response = requests.post(API_URL_HF, headers=headers_hf, data=data, timeout=10)
        resultado = response.json()
        # Si el modelo está cargando, HF devuelve un diccionario con 'estimated_time'
        if isinstance(resultado, dict) and "error" in resultado:
            return None
        return resultado
    except:
        return None

archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen_original = PIL.Image.open(archivo_subido)
    imagen = imagen_original.convert("RGB")
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 ANALIZAR AHORA"):
        with st.status("🚀 Buscando en la nube...", expanded=True) as status:
            texto_full = ""
            nombre_solo = ""

            # 1. INTENTO CON GOOGLE (Puerta Lateral)
            try:
                status.write("📡 Conectando con Google AI...")
                # Prompt más corto para que gaste menos recursos
                prompt = "Identifica qué es. Responde: NOMBRE: [nombre], HISTORIA: [historia], DATO: [dato]"
                response = model_gemini.generate_content([prompt, imagen])
                if response:
                    texto_full = response.text
                    status.write("✅ ¡Google respondió!")
            except Exception as e:
                status.write(f"⚠️ Google ocupado.")
                
                # 2. INTENTO CON RESPALDO (Microsoft via HF)
                status.write("🔄 Activando respaldo de emergencia...")
                res_hf = consulta_huggingface(imagen)
                
                if res_hf and isinstance(res_hf, list) and len(res_hf) > 0:
                    nombre_solo = res_hf[0]['label'].split(',')[0]
                    texto_full = f"NOMBRE: {nombre_solo}\nHISTORIA: Identificado por el motor de respaldo de Turidex.\nDATO: La IA principal volverá pronto."
                    status.write("✅ Respaldo activado.")
                else:
                    status.write("❌ Error de red en ambos motores.")

            if texto_full:
                status.update(label="Análisis finalizado", state="complete", expanded=False)
                st.subheader("Resultado Turidex")
                st.write(texto_full)
                
                # Extraer nombre
                match = re.search(r"NOMBRE:\s*(.*)", texto_full)
                nombre_mapa = match.group(1) if match else "Comida"
                
                # Link de mapas
                link = f"https://www.google.com/maps/search/{nombre_mapa.replace(' ', '+')}+cerca+de+mi"
                st.link_button(f"🍴 BUSCAR {nombre_mapa.upper()} CERCA", link)
                
                # Audio
                try:
                    audio_limpio = limpiar_texto(texto_full)
                    tts = gTTS(text=audio_limpio, lang='es')
                    tts.save("voz.mp3")
                    st.audio("voz.mp3")
                except:
                    st.warning("No se pudo generar el audio esta vez.")
            else:
                st.error("Límite gratuito excedido. Espera un minuto y refresca la página.")
