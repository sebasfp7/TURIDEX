import streamlit as st
from PIL import Image
import imagehash
from gtts import gTTS
import os

# --- BASE DE DATOS DE HUELLAS DIGITALES ---
# En un proyecto real, esto cargaría desde una carpeta. 
# Aquí te doy la estructura para que funcione ya mismo.
TURIDEX_DB = {
    "cerdo_asado": {
        "nombre": "Cerdo Asado Colombiano",
        "hash": "8c8cceecec8c8c8c", # Esta es la "huella" de la foto
        "historia": "Una tradición milenaria de los campos... (aquí tu texto largo)",
        "dato": "El secreto es el adobo de 24 horas.",
        "mapa": "restaurantes+de+asados"
    }
}

st.title("📸 TURIDEX: Escáner Local")
st.write("Sube una foto y la compararemos con nuestra base de datos biométrica.")

archivo = st.file_uploader("Sube la imagen", type=["jpg", "png", "jpeg"])

if archivo:
    img_usuario = Image.open(archivo)
    st.image(img_usuario, width=300)
    
    # Generamos la huella digital de la foto que subió el usuario
    hash_usuario = str(imagehash.average_hash(img_usuario))
    
    if st.button("🔍 ESCANEAR"):
        encontrado = None
        # Comparamos la huella con nuestra base de datos
        for clave, info in TURIDEX_DB.items():
            # Si las huellas son similares (distancia pequeña)
            distancia = imagehash.hex_to_hash(hash_usuario) - imagehash.hex_to_hash(info["hash"])
            
            if distancia < 10: # Ajuste de sensibilidad (más bajo es más exacto)
                encontrado = info
                break
        
        if encontrado:
            st.success(f"✅ ¡Coincidencia encontrada: {encontrado['nombre']}!")
            st.subheader("📖 Historia Completa")
            st.write(encontrado["historia"])
            
            # Mapa y Audio (igual que antes)
            st.link_button("📍 VER MAPA", f"https://www.google.com/maps/search/{encontrado['mapa']}")
            
            tts = gTTS(encontrado["historia"], lang='es')
            tts.save("audio.mp3")
            st.audio("audio.mp3")
        else:
            st.error("❌ No reconozco esta imagen. No está en mi base de datos de ADN.")
