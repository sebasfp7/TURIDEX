import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Turidex Meta Edition", page_icon="📸")
st.title("📸 TURIDEX: Motor Meta Llama 3")

# Cliente de Groq (Usaremos su modelo de Visión de Meta)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

archivo = st.file_uploader("Sube una foto...", type=["jpg", "png", "jpeg"])

if archivo:
    st.image(archivo, use_container_width=True)
    
    if st.button("🔍 ESCANEAR CON META AI"):
        with st.status("🚀 Usando Llama 3 Vision (Meta)...") as status:
            try:
                # Convertir imagen a base64 para la IA
                base64_image = encode_image(archivo)
                
                # Pedimos todo de un solo golpe para ahorrar tiempo y evitar bloqueos
                prompt = """Identifica el plato de la imagen. 
                Responde con este formato exacto:
                NOMBRE: [Nombre del plato]
                HISTORIA: [Escribe 2 párrafos largos sobre su origen y tradición]
                DATO: [Un dato curioso sorprendente]"""

                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                    },
                                },
                            ],
                        }
                    ],
                    model="llama-3.2-11b-vision-preview", # El modelo de Visión de Meta
                )
                
                res_final = chat_completion.choices[0].message.content
                
                # --- RESULTADOS ---
                status.update(label="✅ Identificado por Meta AI", state="complete")
                st.markdown(res_final)
                
                # Extraer nombre para el mapa
                nombre_match = re.search(r"NOMBRE:\s*(.*)", res_final)
                nombre_plato = nombre_match.group(1) if nombre_match else "comida"
                
                st.link_button(f"📍 BUSCAR {nombre_plato.upper()} CERCA", f"https://www.google.com/maps/search/{nombre_plato.replace(' ', '+')}")
                
                # Audio
                tts = gTTS(text=re.sub(r'[*#_]', '', res_final), lang='es')
                tts.save("v.mp3")
                st.audio("v.mp3")

            except Exception as e:
                st.error(f"Error de conexión: {e}")
