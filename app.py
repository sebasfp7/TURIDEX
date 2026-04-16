import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import re
from database import TURIDEX_PEDIA # Importamos tu base de datos gigante

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX: Sistema Automático")

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# Modelo Flash (más rápido y menos propenso a errores de saturación)
model = genai.GenerativeModel('gemini-1.5-flash')

archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido).convert("RGB")
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 ANALIZAR AUTOMÁTICAMENTE"):
        with st.status("🕵️ Identificando...", expanded=True) as status:
            try:
                # 1. IDENTIFICACIÓN RÁPIDA (Solo nombre)
                # Al pedir solo el nombre, Google gasta menos recursos y no te bloquea tanto
                res = model.generate_content(["Dime solo el nombre de este plato (2 palabras máximo)", imagen])
                nombre_ia = res.text.lower().strip()
                
                # 2. BÚSQUEDA EN BASE DE DATOS
                encontrado = None
                for clave in TURIDEX_PEDIA:
                    if clave in nombre_ia or nombre_ia in clave:
                        encontrado = TURIDEX_PEDIA[clave]
                        break
                
                if encontrado:
                    status.update(label="✅ Información recuperada!", state="complete")
                    
                    st.header(f"📍 {encontrado['nombre']}")
                    
                    # Mostramos la información LARGA que escribiste en el archivo
                    st.markdown("### 📖 Historia")
                    st.write(encontrado['history'])
                    
                    st.markdown("### 💡 Dato Curioso")
                    st.info(encontrado['dato'])
                    
                    # Botón de Mapa
                    link = f"https://www.google.com/maps/search/{encontrado['mapa']}+cerca+de+mi"
                    st.link_button(f"🍴 BUSCAR {encontrado['nombre'].upper()} CERCA", link)
                    
                    # Audio
                    texto_audio = f"{encontrado['nombre']}. {encontrado['history']}. {encontrado['dato']}"
                    tts = gTTS(text=re.sub(r'[*#_]', '', texto_audio), lang='es')
                    tts.save("voz.mp3")
                    st.audio("voz.mp3")
                
                else:
                    status.update(label="❓ No está en la base de datos", state="error")
                    st.warning(f"La IA cree que es '{nombre_ia}', pero no tengo información detallada en mi base de datos.")

            except Exception as e:
                st.error("Google está saturado en este momento. Intenta en 10 segundos.")
