import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Turidex Meta 2026", page_icon="📸")
st.title("📸 TURIDEX: Motor Llama 3.2 90B")
st.markdown("---")

# Cliente de Groq con el nuevo modelo estable
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Falta la GROQ_API_KEY en los Secrets de Streamlit.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

archivo = st.file_uploader("Sube una foto de tu plato...", type=["jpg", "png", "jpeg"])

if archivo:
    img_display = PIL.Image.open(archivo)
    st.image(img_display, use_container_width=True, caption="Imagen cargada para análisis")
    
    if st.button("🔍 ESCANEAR CON IA DE META"):
        with st.status("🚀 Analizando con Llama 3.2 90B (Visión)...") as status:
            try:
                # 1. Preparar la imagen
                base64_image = encode_image(archivo)
                
                # 2. El Prompt Maestro para evitar respuestas cortas
                prompt = """Identifica este plato o lugar. 
                Responde en ESPAÑOL con este formato:
                NOMBRE: [Nombre exacto]
                HISTORIA: [Escribe aquí al menos dos párrafos largos y detallados sobre el origen, la evolución y la importancia cultural]
                DATO: [Un dato curioso que casi nadie sepa]"""

                # 3. Llamada al NUEVO modelo de visión 90B
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
                    model="llama-3.2-11b-vision-preview", # Si este falla, usa llama-3.2-90b-vision-preview
                )
                
                # NOTA: Si el de 11b sigue dando error de decommissioned, 
                # cambia la línea de arriba a: model="llama-3.2-90b-vision-preview"
                
                res_final = chat_completion.choices[0].message.content
                
                # --- MOSTRAR RESULTADOS ---
                status.update(label="✅ ¡Identificación exitosa!", state="complete")
                st.markdown(res_final)
                
                # Extraer nombre para el mapa
                try:
                    nombre_plato = res_final.split("NOMBRE:")[1].split("\n")[0].strip()
                except:
                    nombre_plato = "comida"
                
                # Botones de acción
                col1, col2 = st.columns(2)
                with col1:
                    st.link_button(f"📍 BUSCAR {nombre_plato.upper()}", f"https://www.google.com/maps/search/{nombre_plato.replace(' ', '+')}")
                
                with col2:
                    # Audio
                    audio_texto = limpiar_texto(res_final)
                    tts = gTTS(text=audio_texto, lang='es')
                    tts.save("v.mp3")
                    st.audio("v.mp3")

            except Exception as e:
                st.error(f"Error técnico: {e}")
                st.info("Nota: Si el error persiste, es posible que Groq esté actualizando sus modelos. Intenta cambiar el nombre del modelo a 'llama-3.2-90b-vision-preview' en el código.")
