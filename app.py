import streamlit as st
import pandas as pd
import fitz  # Importante: es PyMuPDF para leer PDFs
from docx import Document
from groq import Groq
import io

# 1. Configuración inicial
st.set_page_config(page_title="Finatrix AI", layout="wide")

# Inicializamos el cliente de la IA (Asegúrate de tener la llave en Secrets)
if "GROQ_API_KEY" in st.secrets:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
else:
    st.error("Falta la llave GROQ_API_KEY en los Secrets de Streamlit")

# 2. Función para extraer texto de diferentes archivos
def extraer_texto(archivo_subido):
    nombre_archivo = archivo_subido.name.lower()
    
    try:
        if nombre_archivo.endswith('.xlsx') or nombre_archivo.endswith('.xls'):
            df = pd.read_excel(archivo_subido)
            return df.to_string()
            
        elif nombre_archivo.endswith('.docx'):
            doc = Document(archivo_subido)
            return "\n".join([p.text for p in doc.paragraphs])
            
        elif nombre_archivo.endswith('.pdf'):
            # Leemos PDF digital
            doc_pdf = fitz.open(stream=archivo_subido.read(), filetype="pdf")
            texto = ""
            for pagina in doc_pdf:
                texto += pagina.get_text()
            return texto
            
        return None # Si es imagen o algo que no procesamos aquí
    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
        return None

# 3. Interfaz de Usuario
st.title("📊 Finatrix: Multi-Analista")

archivo = st.file_uploader("Sube tu estado financiero (PDF, Excel, Word o Imagen)", 
                          type=["pdf", "xlsx", "xls", "docx", "png", "jpg", "jpeg"])

if archivo:
    # Intentamos extraer texto directamente (más rápido y gratis)
    texto_extraido = extraer_texto(archivo)
    
    if texto_extraido and len(texto_extraido.strip()) > 10:
        st.success("✅ Texto detectado digitalmente.")
        
        if st.button("Analizar con Llama-3.3 (Texto)"):
            with st.spinner("Analizando datos..."):
                # Aquí usamos el modelo de texto puro (Más barato y rápido)
                chat = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": f"Analiza estos datos contables y dame un diagnóstico: {texto_extraido}"}]
                )
                st.markdown("### 📋 Diagnóstico")
                st.write(chat.choices[0].message.content)
    else:
        # Si no hay texto, es una imagen o PDF escaneado
        st.warning("📸 No se detectó texto digital. Se requiere usar Llama-4-Scout (Visión).")
        
        if st.button("Escanear Imagen con Scout"):
            st.info("Aquí iría la llamada a tu modelo Scout para procesar la imagen...")
            # Aquí pondrías tu código de Scout que ya tenías funcionando
