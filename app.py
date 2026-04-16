import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import requests
import time

# Intentar importar Groq
try:
    from groq import Groq
except ImportError:
    st.error("Error: 'groq' no encontrado en el sistema.")

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex Pro", page_icon="📸")
st.title("📸 TURIDEX: Inteligencia Resiliente")

# --- CONEXIÓN A LAS LLAVES ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model_google = genai.GenerativeModel('gemini-1.5-flash')
    client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])
    
    HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
    API_URL_HF = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"
    headers_hf = {"Authorization": f"Bearer {HF_TOKEN}"}
except Exception as e:
    st.error(f"Revisa tus Secrets: {e}")

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

def consulta_huggingface(img_pil):
    import io
    img_rgb = img_pil.convert("RGB")
    img_bytes = io.BytesIO()
    img_rgb.save(img_bytes, format='JPEG')
    data = img_bytes.getvalue()
    
    # Intentar 3 veces por si el modelo está cargando
    for _ in range(3):
        response = requests.post(API_URL_HF, headers=headers_hf, data=data)
        resultado = response.json()
        if isinstance(resultado, dict) and "estimated_time" in resultado:
            time.sleep(2)
            continue
        return resultado
    return None

archivo = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo:
    img = PIL.Image.open(archivo)
    st.image(img, use_container_width=True)
    
    if st.button("🔍 ANALIZAR AHORA"):
        with st.status("🚀 Procesando...", expanded=True) as status:
            nombre = ""
            res_final = ""

            # 1. INTENTO CON GOOGLE
            try:
                status.write("📡 Intentando con Google...")
                res_g = model_google.generate_content(["Dime solo el nombre de este plato (2 palabras).", img])
                nombre = res_g.text.strip()
            except:
                # 2. RESPALDO CON HUGGING FACE
                status.write("⚠️ Google saturado. Activando respaldo...")
                res_hf = consulta_huggingface(img)
                if res_hf and isinstance(res_hf, list):
                    nombre = res_hf[0]['label'].split(',')[0]
                else:
                    nombre = "Plato Típico"

            # 3. GENERAR HISTORIA CON GROQ
            if nombre:
                try:
                    status.write(f"📖 Redactando historia de: {nombre}...")
                    prompt = f"Actúa como guía. Dame HISTORIA (larga) y DATO de: {nombre}. Formato: NOMBRE: {nombre}, HISTORIA: [texto], DATO: [dato]"
                    comp = client_groq.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.3-70b-versatile",
                    )
                    res_final = comp.choices[0].message.content
                except:
                    res_final = f"NOMBRE: {nombre}\nHISTORIA: Delicioso plato identificado.\nDATO: ¡Disfrútalo!"

            if res_final:
                status.update(label="✅ ¡Listo!", state="complete")
                st.markdown(res_final)
                
                # Mapa
                link = f"https://www.google.com/maps/search/{nombre.replace(' ', '+')}+cerca+de+mi"
                st.link_button(f"📍 BUSCAR {nombre.upper()} CERCA", link)
                
                # Audio
                tts = gTTS(text=limpiar_texto(res_final), lang='es')
                tts.save("v.mp3")
                st.audio("v.mp3")
