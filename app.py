import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX OFICIAL")

# --- CONEXIÓN SEGURA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Probamos con 1.5-flash que es más rápido y tiene límites más amplios que el 2.5
    model = genai.GenerativeModel('models/gemini-1.5-flash')
except:
    st.error("Error de configuración. Revisa tus Secrets.")

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

archivo_subido = st.file_uploader("Sube una foto de comida o lugar...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido)
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 ANALIZAR CON TURIDEX"):
        with st.status("🚀 Procesando con IA...", expanded=True) as status:
            exito = False
            for intento in range(3): # Intentará 3 veces automáticamente
                try:
                    prompt = """Identifica el objeto. Responde estrictamente:
                    NOMBRE: [Nombre]
                    HISTORIA: [Historia breve]
                    DATO: [Dato curioso]"""
                    
                    response = model.generate_content([prompt, imagen])
                    texto_full = response.text
                    exito = True
                    break 
                except Exception as e:
                    if "429" in str(e):
                        st.write(f"⚠️ Servidor ocupado (Intento {intento+1}/3)... esperando...")
                        time.sleep(5) # Espera 5 segundos entre intentos
                    else:
                        st.error(f"Error: {e}")
                        break

            if exito:
                status.update(label="✅ ¡Identificado!", state="complete", expanded=False)
                
                # Extraer nombre
                lineas = texto_full.split('\n')
                nombre_solo = "comida"
                for l in lineas:
                    if "NOMBRE:" in l:
                        nombre_solo = l.replace("NOMBRE:", "").strip()
                
                st.subheader(f"📍 {nombre_solo}")
                st.write(texto_full)
                
                # Mapa
                busqueda = f"donde+comer+{nombre_solo.replace(' ', '+')}+restaurantes"
                link = f"https://www.google.com/maps/search/{busqueda}"
                st.link_button(f"🍴 BUSCAR {nombre_solo.upper()} CERCA", link)
                
                # Audio
                texto_voz = limpiar_texto(texto_full)
                tts = gTTS(text=texto_voz, lang='es')
                tts.save("voz.mp3")
                st.audio("voz.mp3")
            else:
                status.update(label="❌ Error de conexión", state="error")
                st.warning("Google está saturado. Por favor, intenta subir la foto nuevamente en 1 minuto.")

st.info("💡 Consejo: Si sale error, espera unos segundos. La versión gratuita tiene límites de velocidad.")
