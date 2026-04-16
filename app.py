import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import json
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX: Inteligencia Automática")

# --- CARGAR BASE DE DATOS ---
def cargar_datos():
    try:
        with open('datos_comida.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

TURIDEX_PEDIA = cargar_datos()

# --- CONFIGURACIÓN IA ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# Usamos el modelo Flash para que sea instantáneo
model = genai.GenerativeModel('gemini-1.5-flash')

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido).convert("RGB")
    st.image(imagen, use_container_width=True)
    
    if st.button("🔍 IDENTIFICAR AUTOMÁTICAMENTE"):
        with st.status("🚀 Turidex analizando...", expanded=True) as status:
            
            # PASO 1: Identificación rápida del nombre
            try:
                status.write("🕵️ Identificando plato...")
                prompt_nombre = "Responde SOLO el nombre del plato de la imagen en 2 o 3 palabras máximo."
                res_nombre = model.generate_content([prompt_nombre, imagen])
                nombre_identificado = res_nombre.text.lower().strip().replace(".", "")
                
                # PASO 2: Buscar en la base de datos (Búsqueda inteligente)
                info_encontrada = None
                for clave in TURIDEX_PEDIA:
                    if clave in nombre_identificado or nombre_identificado in clave:
                        info_encontrada = TURIDEX_PEDIA[clave]
                        nombre_final = clave.title()
                        break
                
                # PASO 3: Mostrar resultados
                if info_encontrada:
                    status.update(label="✅ ¡Encontrado en la enciclopedia!", state="complete")
                    texto_completo = f"NOMBRE: {nombre_final}\n\nHISTORIA: {info_encontrada['history']}\n\nDATO CURIOSO: {info_encontrada['dato']}"
                    query_mapa = info_encontrada['mapa']
                else:
                    status.write("📡 No estaba en el libro, generando respuesta con IA...")
                    prompt_completo = "Identifica y dame una historia larga y un dato curioso. Formato: NOMBRE: [nombre], HISTORIA: [historia larga], DATO: [dato]"
                    res_completa = model.generate_content([prompt_completo, imagen])
                    texto_completo = res_completa.text
                    nombre_final = nombre_identificado.title()
                    query_mapa = nombre_identificado

                st.subheader(f"📍 {nombre_final}")
                st.write(texto_completo)
                
                # Mapa y Audio
                link = f"https://www.google.com/maps/search/{query_mapa.replace(' ', '+')}+cerca+de+mi"
                st.link_button(f"🍴 BUSCAR {nombre_final.upper()} CERCA", link)
                
                audio_limpio = limpiar_texto(texto_completo)
                tts = gTTS(text=audio_limpio, lang='es')
                tts.save("voz.mp3")
                st.audio("voz.mp3")

            except Exception as e:
                status.update(label="❌ Error de conexión", state="error")
                st.error("Google está saturado. Intenta de nuevo en un momento.")
