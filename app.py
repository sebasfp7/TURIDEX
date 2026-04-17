import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import requests
import json
import pdfplumber
from docx import Document
import re

# ==================== 1. MOTOR DE INTELIGENCIA Y LIMPIEZA ====================
def limpiar_json(texto):
    try:
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match: return json.loads(match.group(0))
        return json.loads(texto)
    except: return None

def motor_groq(key, prompt):
    client = Groq(api_key=key)
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user", "content":prompt}],
        response_format={"type":"json_object"}
    )
    return json.loads(res.choices[0].message.content)

def motor_gemini(key, prompt):
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    res = model.generate_content(prompt)
    return limpiar_json(res.text)

# ==================== 2. LECTURA MULTIFORMATO ====================
def leer_archivo(file):
    ext = file.name.split('.')[-1].lower()
    text = ""
    if ext == 'pdf':
        with pdfplumber.open(file) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
    elif ext == 'xlsx':
        df = pd.read_excel(file).head(50)
        text = df.to_csv(index=False)
    elif ext == 'docx':
        doc = Document(file)
        text = "\n".join([p.text for p in doc.paragraphs])
    return text[:15000]

# ==================== 3. INTERFAZ (EL REGRESO DE LAS KEYS) ====================
st.set_page_config(page_title="Finatrix Elite v9.7", layout="wide")
st.title("🛡️ Finatrix Elite | CFO Virtual")

with st.sidebar:
    st.header("🔑 Configuración de Keys")
    st.write("Si no configuraste 'Secrets', pon tus llaves aquí:")
    # Prioriza Secrets, pero permite entrada manual
    key_groq = st.text_input("Groq Key", value=st.secrets.get("GROQ_KEY", ""), type="password")
    key_gemini = st.text_input("Gemini Key", value=st.secrets.get("GEMINI_KEY", ""), type="password")
    
archivo = st.file_uploader("Subir Estados Financieros", type=["pdf", "xlsx", "docx"])

if archivo and st.button("🚀 Iniciar Gran Auditoría"):
    with st.spinner("Procesando datos financieros..."):
        raw_text = leer_archivo(archivo)
        
        prompt_maestro = f"""Eres un CFO Senior. Analiza: {raw_text}.
        Responde SOLO en JSON:
        {{
          "m": {{ "score": 0, "eva": 0, "wacc": 0 }},
          "resumen_ejecutivo": "...",
          "diagnostico_pilares": {{ "rentabilidad": "...", "liquidez": "...", "solvencia": "...", "creacion_valor": "..." }},
          "semaforo": {{ "verde": [], "amarillo": [], "rojo": [] }},
          "plan_90_dias": {{ "t30": "...", "t60": "...", "t90": "..." }}
        }}"""

        data = None
        # Intento con Groq
        if key_groq and not data:
            try:
                data = motor_groq(key_groq, prompt_maestro)
                st.success("✅ Análisis generado con Groq")
            except: st.warning("⚠️ Groq falló o no tiene Key válida.")

        # Intento con Gemini (Respaldo)
        if key_gemini and not data:
            try:
                data = motor_gemini(key_gemini, prompt_maestro)
                st.success("✅ Análisis generado con Gemini")
            except: st.error("❌ Gemini también falló.")

        if data:
            # --- VISUALIZACIÓN COMPLETA ---
            m = data.get('m', {})
            c1, c2, c3 = st.columns(3)
            c1.metric("Salud Estratégica", f"{m.get('score', 0)}/100")
            c2.metric("EVA", f"${m.get('eva', 0):,.0f}")
            c3.metric("WACC", f"{m.get('wacc', 0):.2%}")

            st.write("---")
            st.subheader("📋 Resumen Ejecutivo")
            st.info(data.get('resumen_ejecutivo', ''))

            # Pilares y resto de la información...
            diag = data.get('diagnostico_pilares', {})
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Rentabilidad:** {diag.get('rentabilidad')}")
                st.write(f"**Liquidez:** {diag.get('liquidez')}")
            with col2:
                st.write(f"**Solvencia:** {diag.get('solvencia')}")
                st.write(f"**Creación de Valor:** {diag.get('creacion_valor')}")
            
            # Semáforo y Plan...
            st.write("---")
            sem = data.get('semaforo', {})
            st.subheader("🚦 Semáforo y Plan de Acción")
            st.success(f"Fortalezas: {', '.join(sem.get('verde', []))}")
            st.error(f"Riesgos: {', '.join(sem.get('rojo', []))}")
