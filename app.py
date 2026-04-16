import streamlit as st
import google.generativeai as genai
import PIL.Image
from gtts import gTTS
import os
import re
import io

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex", page_icon="📸")
st.title("📸 TURIDEX: Pokedex Edición Especial")

# --- 📚 LA TURIDEX-PEDIA (Nuestra Base de Datos Local) ---
# Aquí guardamos la información para que no dependa de la IA siempre
TURIDEX_PEDIA = {
    "cerdo asado": {
        "historia": "El cerdo asado es un plato tradicional en muchas culturas, especialmente en festividades rurales. Su preparación lenta a fuego de leña le otorga un sabor ahumado único.",
        "dato": "En algunas regiones, se cree que el secreto de un buen asado está en el adobo de 24 horas con hierbas silvestres.",
        "mapa": "restaurantes+de+cerdo+asado+y+parrilladas"
    },
    "hamburguesa": {
        "historia": "Aunque se popularizó en Estados Unidos, sus orígenes se remontan a Hamburgo, Alemania. Es el icono mundial de la comida rápida.",
        "dato": "La hamburguesa más cara del mundo cuesta más de 5,000 dólares y lleva láminas de oro.",
        "mapa": "hamburgueserias+artesanales"
    },
    "pizza": {
        "historia": "Nacida en Nápoles, Italia, como un plato para gente humilde, hoy es la comida más famosa del planeta.",
        "dato": "La pizza Margarita fue creada en honor a la reina Margarita de Saboya con los colores de la bandera italiana.",
        "mapa": "pizzerias+italianas"
    },
    "ensalada": {
        "historia": "Consumida desde la antigua Grecia, las ensaladas representan la frescura y la salud en la mesa.",
        "dato": "La palabra ensalada viene del latín 'salata', que significa salada.",
        "mapa": "restaurantes+saludables"
    }
}

# --- CONFIGURACIÓN DE IA (Solo como último recurso) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except:
    pass

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

archivo_subido = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo_subido is not None:
    imagen = PIL.Image.open(archivo_subido).convert("RGB")
    st.image(imagen, use_container_width=True)
    
    # 1. Selector manual (como en una Pokedex real para evitar errores)
    opciones = ["Seleccionar automáticamente (IA)", "Cerdo Asado", "Hamburguesa", "Pizza", "Ensalada"]
    seleccion = st.selectbox("¿Qué estamos viendo?", opciones)

    if st.button("🔍 IDENTIFICAR"):
        texto_full = ""
        nombre_solo = ""
        
        # CASO A: El usuario selecciona del "Libro"
        if seleccion != "Seleccionar automáticamente (IA)":
            clave = seleccion.lower()
            info = TURIDEX_PEDIA[clave]
            nombre_solo = seleccion
            texto_full = f"NOMBRE: {seleccion}\nHISTORIA: {info['historia']}\nDATO: {info['dato']}"
            st.success(f"📖 Información recuperada de la Turidex-Pedia")
        
        # CASO B: Usar la IA si no está en el libro
        else:
            with st.spinner("Buscando en la nube..."):
                try:
                    prompt = "Identifica el objeto. NOMBRE: [Nombre], HISTORIA: [Breve], DATO: [Curiosidad]"
                    response = model.generate_content([prompt, imagen])
                    texto_full = response.text
                    nombre_solo = "comida"
                except:
                    st.error("IA saturada. Por favor selecciona el plato manualmente de la lista.")

        if texto_full:
            st.subheader(f"📍 {nombre_solo}")
            st.write(texto_full)
            
            # Mapa inteligente
            termino = seleccion.lower() if seleccion != "Seleccionar automáticamente (IA)" else "comida"
            mapa_query = TURIDEX_PEDIA.get(termino, {"mapa": termino})["mapa"]
            
            link = f"https://www.google.com/maps/search/{mapa_query.replace(' ', '+')}+cerca+de+mi"
            st.link_button(f"🍴 BUSCAR {nombre_solo.upper()} CERCA", link)
            
            # Audio
            audio_limpio = limpiar_texto(texto_full)
            tts = gTTS(text=audio_limpio, lang='es')
            tts.save("voz.mp3")
            st.audio("voz.mp3")
