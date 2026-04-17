import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import json
import pdfplumber
from docx import Document
import re
from io import BytesIO

# 1. Configuración de página (Esto DEBE ser lo primero)
st.set_page_config(page_title="Finatrix Elite Pro", layout="wide")

# 2. Barra Lateral Interactiva
with st.sidebar:
    st.header("🔑 Configuración")
    # Usamos text_input simple sin valores por defecto de secrets para probar fluidez
    api_groq = st.text_input("Groq API Key", type="password", help="Pega tu llave de Groq aquí")
    api_gemini = st.text_input("Gemini API Key", type="password", help="Pega tu llave de Gemini aquí")
    st.divider()
    st.caption("Asegúrate de que las llaves sean válidas.")

# 3. Lógica de lectura
def leer_documento(file):
    try:
        ext = file.name.split('.')[-1].lower()
        if ext == 'pdf':
            with pdfplumber.open(file) as pdf:
                return "\n".join([p.extract_text() or "" for p in pdf.pages])[:20000]
        elif ext == 'xlsx':
            return pd.read_excel(file).to_csv(index=False)[:20000]
        elif ext == 'docx':
            doc = Document(file)
            return "\n".join([p.text for p in doc.paragraphs])[:20000]
    except Exception as e:
        st.error(f"Error al leer: {e}")
        return None

# 4. Interfaz Principal
st.title("🛡️ Finatrix Elite")
st.write("Sube tu archivo para iniciar la auditoría.")

archivo = st.file_uploader("Subir Balance/Informe", type=["pdf", "xlsx", "docx"])

if archivo and st.button("🚀 Ejecutar Análisis Estratégico"):
    if not api_groq and not api_gemini:
        st.error("⚠️ Por favor, ingresa al menos una API Key en el menú de la izquierda.")
    else:
        with st.spinner("Analizando datos financieros..."):
            texto = leer_documento(archivo)
            if texto:
                # Aquí va la llamada a la IA (abreviada para asegurar que el menú funcione)
                st.success("Archivo leído correctamente. Conectando con IA...")
                # ... (Lógica de Groq/Gemini similar a la anterior)
            
