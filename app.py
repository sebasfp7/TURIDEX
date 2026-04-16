import streamlit as st
from groq import Groq
from PIL import Image
import base64
import io
import re
import json

st.set_page_config(page_title="TURIDEX", layout="wide")

if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_category' not in st.session_state: st.session_state.current_category = None
if 'log' not in st.session_state: st.session_state.log = []

def add_log(msg):
    st.session_state.log.append(msg)
    st.rerun()

st.markdown("""
<style>
    .stApp {background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
            background-size: cover; background-attachment: fixed;}
    .frame {background: rgba(255,255,255,0.92); backdrop-filter: blur(12px);
            border: 4px solid #DC0A2D; border-radius: 20px; padding: 25px;}
    .title {color: #FFDE00 !important; font-size: 3.8em; text-align:center;}
    .header {background:#000; color:#0F0; padding:12px; border-radius:8px; text-align:center; font-size:1.4em;}
    .log-box {background:#111; color:#0F0; padding:10px; border-radius:5px; font-family:monospace; margin:10px 0;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title'>⚡ TURIDEX ⚡</h1>", unsafe_allow_html=True)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

def add_log(msg):
    st.session_state.log.append(msg)

def resize_image(image_file):
    img = Image.open(image_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    if img.width > 800 or img.height > 800:
        img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85, optimize=True)
    return buffer.getvalue()

def get_prompt(is_image=True):
    if is_image:
        return """Analiza la imagen y responde SOLO con un JSON válido:
{
  "nombre": "nombre claro",
  "categoria": "ANIMAL",
  "desc": "descripción corta",
  "historia": "dos párrafos cortos",
  "stats": [80,75,70,65],
  "evos": ["Tigre", "Leopardo", "Jaguar"]
}"""
    return "Responde solo con JSON válido."

def parse_json(text):
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
    return {"nombre": "Error", "categoria": "ANIMAL", "desc": "Error de parsing", 
            "historia": "No se pudo procesar la respuesta.", "stats": [50,50,50,50], "evos": ["Error1","Error2","Error3"]}

# ====================== INTERFAZ ======================
with st.container():
    st.markdown("<div class='frame'>", unsafe_allow_html=True)

    if st.button("🔄 Reiniciar"):
        st.session_state.clear()
        st.rerun()

    st.markdown(f"<div class='header'>📍 {st.session_state.current_item or 'Esperando imagen...'}</div>", unsafe_allow_html=True)

    # Mostrar logs
    if st.session_state.log:
        st.markdown("### Logs:")
        for entry in st.session_state.log[-6:]:
            st.markdown(f"<div class='log-box'>{entry}</div>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 2])

    with col1:
        archivo = st.file_uploader("Carga una imagen (JPG, PNG)", type=["jpg","png","jpeg"])
        if archivo:
            st.image(archivo, use_container_width=True)
            if st.button("🔍 ESCANEAR OBJETIVO", type="primary", use_container_width=True):
                st.session_state.log = []
                add_log("1. Imagen recibida")
                
                try:
                    add_log("2. Redimensionando imagen...")
                    bytes_opt = resize_image(archivo)
                    add_log("3. Codificando a base64...")
                    b64 = base64.b64encode(bytes_opt).decode()
                    add_log("4. Preparando prompt...")
                    prompt = get_prompt(is_image=True)
                    
                    add_log("5. Llamando a Groq API...")
                    response = client.chat.completions.create(
                        messages=[{"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]}],
                        model="llama-4-scout-17b-16e-instruct",
                        temperature=0.1,
                        max_tokens=800
                    )
                    add_log("6. Respuesta recibida. Procesando JSON...")
                    
                    data = parse_json(response.choices[0].message.content)
                    
                    st.session_state.current_item = data.get("nombre", "Animal Desconocido")
                    st.session_state.current_category = data.get("categoria", "ANIMAL")
                    add_log(f"7. Análisis completado: {st.session_state.current_item}")
                    st.rerun()
                    
                except Exception as e:
                    add_log(f"❌ ERROR: {str(e)}")
                    st.error(f"Error detallado: {str(e)}")

    with col2:
        if st.session_state.current_item and st.session_state.current_item != "Procesando imagen...":
            st.success(f"✅ Análisis completado: **{st.session_state.current_item}**")
            st.info("Ahora puedes probar pulsando variantes (cuando estén disponibles).")

    st.markdown("</div>", unsafe_allow_html=True)
