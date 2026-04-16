import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import json # Nueva herramienta para leer el libro gigante

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX: Gran Enciclopedia")

# --- 📚 CARGAR LA TURIDEX-PEDIA DESDE ARCHIVO ---
def cargar_datos():
    try:
        with open('datos_comida.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        # Si el archivo no existe o falla, cargamos una base mínima
        return {"error": "No se encontró la base de datos"}

TURIDEX_PEDIA = cargar_datos()

# --- CONFIGURACIÓN IA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except:
    pass

archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido).convert("RGB")
    st.image(imagen, use_container_width=True)
    
    # El buscador ahora se alimenta de todos los nombres en tu archivo JSON
    nombres_comidas = sorted(list(TURIDEX_PEDIA.keys()))
    opciones = ["Identificar con IA (Nube)"] + [n.title() for n in nombres_comidas]
    
    seleccion = st.selectbox("¿Qué plato es este?", opciones)

    if st.button("🔍 OBTENER INFORMACIÓN"):
        texto_full = ""
        nombre_final = ""
        
        if seleccion != "Identificar con IA (Nube)":
            clave = seleccion.lower()
            info = TURIDEX_PEDIA[clave]
            nombre_final = seleccion
            texto_full = f"NOMBRE: {seleccion}\nHISTORIA: {info['historia']}\nDATO: {info['dato']}"
        else:
            # Solo usa IA si el usuario lo pide y el plato no está en el libro
            with st.spinner("Consultando satélite..."):
                try:
                    prompt = "Identifica el objeto. NOMBRE: [Nombre], HISTORIA: [Breve], DATO: [Curiosidad]"
                    response = model.generate_content([prompt, imagen])
                    texto_full = response.text
                    nombre_final = "Comida"
                except:
                    st.error("Servidores ocupados. Por favor, selecciona el nombre del menú.")

        if texto_full:
            st.success("¡Información lista!")
            st.write(texto_full)
            
            # Mapa
            clave_mapa = seleccion.lower() if seleccion != "Identificar con IA (Nube)" else "restaurante"
            query_mapa = TURIDEX_PEDIA.get(clave_mapa, {"mapa": "restaurante"})["mapa"]
            link = f"https://www.google.com/maps/search/{query_mapa}+cerca+de+mi"
            st.link_button(f"📍 BUSCAR {nombre_final.upper()} CERCA", link)
            
            # Audio
            tts = gTTS(text=re.sub(r'[*#_]', '', texto_full), lang='es')
            tts.save("voz.mp3")
            st.audio("voz.mp3")
