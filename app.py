import streamlit as st
import google.generativeai as genai
from groq import Groq # Necesitas poner 'groq' en requirements.txt
import PIL.Image
from gtts import gTTS
import json
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex Pro", page_icon="📸")
st.title("📸 TURIDEX: Inteligencia Total")

# Configurar Google
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model_google = genai.GenerativeModel('gemini-1.5-flash-8b')

# Configurar Groq (El respaldo que no falla)
client_groq = Groq(api_key=st.secrets["GROQ_API_KEY"])

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

archivo = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo:
    img = PIL.Image.open(archivo).convert("RGB")
    st.image(img, use_container_width=True)
    
    if st.button("🔍 ANALIZAR AHORA"):
        with st.status("🚀 Buscando en múltiples cerebros...") as status:
            res_final = ""
            
            # INTENTO 1: Google Gemini Mini (Rápido y ligero)
            try:
                status.write("📡 Consultando Google (Flash-8b)...")
                prompt = "Identifica el plato/lugar. Dame: NOMBRE, HISTORIA (larga y detallada) y DATO CURIOSO."
                response = model_google.generate_content([prompt, img])
                res_final = response.text
            except:
                # INTENTO 2: Groq (Si Google falla)
                status.write("⚠️ Google saturado. Saltando a motor de alta velocidad (Groq)...")
                try:
                    # Nota: Groq es mejor con texto, así que le pediremos a Google solo el nombre 
                    # y a Groq que nos cuente la historia larga.
                    prompt_nombre = "Dime solo el nombre de este plato/lugar (2 palabras)."
                    nombre_breve = model_google.generate_content([prompt_nombre, img]).text
                    
                    chat_completion = client_groq.chat.completions.create(
                        messages=[{"role": "user", "content": f"Háblame extensamente sobre {nombre_breve}. Dame historia y un dato curioso."}],
                        model="llama-3.3-70b-versatile",
                    )
                    res_final = f"NOMBRE: {nombre_breve}\n\n{chat_completion.choices[0].message.content}"
                except Exception as e:
                    st.error("Incluso el respaldo falló. Revisa tu conexión.")

            if res_final:
                status.update(label="✅ ¡Logrado!", state="complete")
                st.markdown(res_final)
                
                # Mapa
                nombre_busqueda = res_final.split('\n')[0].replace("NOMBRE:", "").strip()
                link = f"https://www.google.com/maps/search/{nombre_busqueda.replace(' ', '+')}+restaurantes"
                st.link_button(f"📍 BUSCAR {nombre_busqueda.upper()} CERCA", link)
                
                # Audio
                tts = gTTS(limpiar_texto(res_final), lang='es')
                tts.save("voz.mp3")
                st.audio("voz.mp3")
