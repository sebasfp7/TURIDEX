import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Turidex Scout 2026", page_icon="📸")
st.title("📸 TURIDEX: Motor Llama 4 Scout")
st.markdown("---")

# Cliente de Groq
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception:
    st.error("Error: Configura tu GROQ_API_KEY en los Secrets.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def limpiar_texto(t):
    return re.sub(r'[*#_]', '', t)

archivo = st.file_uploader("Sube una foto de tu plato...", type=["jpg", "png", "jpeg"])

if archivo:
    img_display = PIL.Image.open(archivo)
    st.image(img_display, use_container_width=True, caption="Imagen cargada")
    
    if st.button("🔍 ESCANEAR CON LLAMA 4"):
        with st.status("🚀 Analizando con Llama 4 Scout (Visión)...") as status:
            try:
                base64_image = encode_image(archivo)
                
                # Prompt optimizado para Llama 4
                prompt = """Identifica este plato o lugar turístico. 
                Responde estrictamente en ESPAÑOL con este formato:
                NOMBRE: [Nombre exacto]
                HISTORIA: [Escribe dos párrafos extensos sobre su origen, tradición y evolución cultural]
                DATO: [Un dato curioso poco conocido]"""

                # Llamada al modelo Llama 4 Scout
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
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                )
                
                res_final = chat_completion.choices[0].message.content
                
                # --- MOSTRAR RESULTADOS ---
                status.update(label="✅ Análisis de nueva generación completado", state="complete")
                st.markdown(res_final)
                
                # Extraer nombre para el buscador
                try:
                    nombre_plato = res_final.split("NOMBRE:")[1].split("\n")[0].strip()
                except:
                    nombre_plato = "comida"
                
                col1, col2 = st.columns(2)
                with col1:
                    st.link_button(f"📍 BUSCAR {nombre_plato.upper()}", f"https://www.google.com/maps/search/{nombre_plato.replace(' ', '+')}")
                
                with col2:
                    # Generar Audio
                    audio_texto = limpiar_texto(res_final)
                    tts = gTTS(text=audio_texto, lang='es')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, format="audio/mp3")

            except Exception as e:
                st.error(f"Error técnico: {e}")
                st.info("Si el modelo Scout aún no está activo en tu región de Groq, prueba con 'llama-3.2-90b-vision-preview'.")
