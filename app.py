import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import requests # Necesario para la IA de respaldo

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX: Identificador Inteligente")
st.write("Visión Multi-IA para viajeros")

# --- CONEXIÓN A LAS IAS (Usando Secrets) ---
try:
    # IA Principal (Gemini)
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model_gemini = genai.GenerativeModel('models/gemini-1.5-flash')
    
    # IA de Respaldo (Hugging Face)
    API_URL_HF = "https://api-inference.huggingface.co/models/calendari/food-image-classification"
    headers_hf = {"Authorization": f"Bearer {st.secrets['HUGGINGFACE_API_KEY']}"}
except:
    st.error("Error crítico de configuración. Revisa tus Secrets de Streamlit.")

# Funciones de utilidad
def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

def consulta_huggingface(img_pil):
    # Convierte la imagen PIL a bytes para enviarla por red
    import io
    img_bytes = io.BytesIO()
    img_pil.save(img_bytes, format='JPEG')
    img_bytes = img_bytes.getvalue()
    
    # Hace la consulta a Hugging Face
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

            # INTENTO 1: Usar Gemini (La mejor opción)
            try:
                status.write("📡 Consultando IA Principal (Google)...")
                prompt = """Identifica el objeto. Responde estrictamente:
                NOMBRE: [Nombre]
                HISTORIA: [Historia breve y curiosa]
                DATO: [Dato curioso]"""
                response = model_gemini.generate_content([prompt, imagen])
                texto_full = response.text
                metodo_ia = "Google Gemini"
                
                # Extraer nombre
                lineas = texto_full.split('\n')
                for l in lineas:
                    if "NOMBRE:" in l:
                        nombre_solo = l.replace("NOMBRE:", "").strip()

            # INTENTO 2: Si Gemini falla por saturación (Error 429), usar Hugging Face
            except Exception as e:
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    status.write("⚠️ Google saturado. Activando IA de Respaldo (Open Source)...")
                    try:
                        resultado_hf = consulta_huggingface(imagen)
                        # Hugging Face suele devolver una lista ordenada por probabilidad
                        # Tomamos el primer resultado
                        if resultado_hf and 'label' in resultado_hf[0]:
                            nombre_solo = resultado_hf[0]['label']
                            # Como HF solo da el nombre, inventamos un texto genérico profesional
                            texto_full = f"""
                            NOMBRE: {nombre_solo.title()}
                            HISTORIA: He identificado este plato usando mi IA de respaldo. Es una delicia muy popular.
                            DATO: ¡Busca lugares cercanos para probarlo!
                            """
                            metodo_ia = "Hugging Face (Open Source)"
                        else:
                            texto_full = "No pude identificarlo con ninguna IA."
                    except:
                        texto_full = "Error total en ambas IAs."
                else:
                    st.error(f"Error inesperado: {e}")
                    status.update(label="❌ Error", state="error")
                    st.stop()

            # --- MOSTRAR RESULTADOS ---
            if texto_full and texto_full != "No pude identificarlo con ninguna IA.":
                status.update(label=f"✅ ¡Identificado por {metodo_ia}!", state="complete", expanded=False)
                
                st.subheader(f"📍 {nombre_solo.title()}")
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
                status.update(label="❌ Fallo en la identificación", state="error")
                st.warning("No pude identificar la imagen por saturación en todos los servidores gratuitos.")

st.info("💡 Consejo: Esta versión usa Multi-IA para evitar los límites de velocidad gratuitos.")
