import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Turidex Pokédex Edition", page_icon="📸")
st.title("📸 TURIDEX: ¡Atrápalos a todos!")
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

archivo = st.file_uploader("📸 Enfoca tu objetivo...", type=["jpg", "png", "jpeg"])

if archivo:
    img_display = PIL.Image.open(archivo)
    st.image(img_display, use_container_width=True)
    
    if st.button("🔍 ESCANEAR OBJETIVO"):
        with st.status("🚀 Procesando datos de la Pokedex...") as status:
            try:
                base64_image = encode_image(archivo)
                
                # PROMPT MAESTRO: Pedimos el nombre, la historia y los valores para las barras
                prompt = """Identifica este plato, lugar o animal. 
                Responde en ESPAÑOL con este formato exacto:
                NOMBRE: [Nombre]
                HISTORIA: [Dos párrafos detallados]
                DATO: [Curiosidad]
                STATS: [Dame 4 números del 1 al 100 para sus atributos principales, separados por comas]"""

                chat_completion = client.chat.completions.create(
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }],
                    model="meta-llama/llama-4-scout-17b-16e-instruct", # O llama-3.2-90b-vision-preview
                )
                
                res_full = chat_completion.choices[0].message.content
                
                # --- PROCESAMIENTO DE DATOS ---
                # Separamos el texto de los números (Stats)
                try:
                    texto_principal = res_full.split("STATS:")[0]
                    stats_raw = res_full.split("STATS:")[1].strip()
                    numeros = [int(n.strip()) for n in stats_raw.split(",")]
                except:
                    numeros = [50, 50, 50, 50] # Valores por defecto si falla
                
                status.update(label="✅ Datos recuperados", state="complete")
                
                # 1. MOSTRAR TEXTO (Historia y Dato)
                st.markdown(texto_principal)

                # 2. INTERFAZ POKÉDEX (Donde pegamos tu código)
                st.markdown("---")
                st.subheader("📊 Puntos de Base (Stats)")
                
                # Identificamos etiquetas según el contexto (si es comida o lugar)
                if "caloria" in texto_principal.lower() or "plato" in texto_principal.lower():
                    labels = ["🔥 Calorías", "🌶️ Picante", "💪 Proteína", "⭐ Popularidad"]
                else:
                    labels = ["🏛️ Antigüedad", "🧗 Altura", "🌤️ Clima", "💎 Rareza"]

                col1, col2 = st.columns(2)
                with col1:
                    st.write(labels[0])
                    st.progress(numeros[0] / 100)
                    st.write(labels[1])
                    st.progress(numeros[1] / 100)
                with col2:
                    st.write(labels[2])
                    st.progress(numeros[2] / 100)
                    st.write(labels[3])
                    st.progress(numeros[3] / 100)
                
                st.markdown("---")

                # 3. ACCIONES FINALIZADAS
                nombre_plato = texto_principal.split("NOMBRE:")[1].split("\n")[0].strip()
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    st.link_button(f"📍 MAPA DE {nombre_plato}", f"https://www.google.com/maps/search/{nombre_plato.replace(' ', '+')}")
                with col_btn2:
                    tts = gTTS(text=limpiar_texto(texto_principal), lang='es')
                    audio_fp = io.BytesIO()
                    tts.write_to_fp(audio_fp)
                    st.audio(audio_fp, format="audio/mp3")

            except Exception as e:
                st.error(f"Error en los circuitos de la Pokédex: {e}")
