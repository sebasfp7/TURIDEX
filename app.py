import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import json
import pdfplumber
from docx import Document
import re
import requests
from io import BytesIO

# Configuración inicial
st.set_page_config(page_title="Finatrix Elite Pro", layout="wide", page_icon="🛡️")

# Lectura de archivos multiformato
def leer_archivo(file):
    try:
        ext = file.name.split('.')[-1].lower()
        content = file.read()
        if ext == 'pdf':
            with pdfplumber.open(BytesIO(content)) as pdf:
                return "\n".join([p.extract_text() or "" for p in pdf.pages[:20]])[:30000]
        elif ext == 'xlsx':
            return pd.read_excel(BytesIO(content)).head(100).to_csv(index=False)[:30000]
        elif ext == 'docx':
            doc = Document(BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs[:200]])[:30000]
        return ""
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return ""

# Motores de IA con limpieza de JSON
def analizar_ia(nombre, api_key, prompt, raw_text):
    try:
        if nombre == "Groq":
            client = Groq(api_key=api_key)
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        elif nombre == "Gemini":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content(prompt)
            match = re.search(r'\{.*\}', res.text, re.DOTALL)
            return json.loads(match.group(0))
        # Agrega aquí los otros motores si tienes sus Keys
        return None
    except:
        return None

# INTERFAZ
st.title("🛡️ Finatrix Elite | 5 IAs en Cascada")

with st.sidebar:
    st.header("🔑 API Keys")
    api_groq = st.text_input("Groq Key", value=st.secrets.get("GROQ_KEY", ""), type="password")
    api_gemini = st.text_input("Gemini Key", value=st.secrets.get("GEMINI_KEY", ""), type="password")

archivo = st.file_uploader("📁 Subir Estados Financieros", type=["pdf", "xlsx", "docx"])

if archivo and st.button("🚀 Analizar", type="primary"):
    with st.spinner("📖 Procesando..."):
        raw_text = leer_archivo(archivo)
        if not raw_text: st.stop()
        
        prompt = f"Actúa como CFO. Analiza y responde SOLO JSON: {raw_text[:10000]}"
        
        data = None
        # Cascada de seguridad
        for nombre, key in [("Groq", api_groq), ("Gemini", api_gemini)]:
            if key and not data:
                with st.spinner(f"Intentando con {nombre}..."):
                    data = analizar_ia(nombre, key, prompt, raw_text)
                    if data: st.success(f"✅ Éxito con {nombre}")

        if data:
            # Visualización de métricas
            m = data.get('m', {})
            c1, c2, c3 = st.columns(3)
            c1.metric("Score", f"{data.get('score', 0)}/100")
            c2.metric("EVA", f"${m.get('eva', 0):,.0f}")
            c3.metric("WACC", f"{m.get('wacc', 0):.2%}")
            
            st.subheader("📋 Resumen")
            st.write(data.get('resumen_ejecutivo'))
            
            # Hallazgos y Riesgos
            st.subheader("🔍 Diagnóstico")
            st.write(data.get('diagnostico_pilares'))
        else:
            st.error("Ninguna IA respondió. Revisa tus llaves.")
