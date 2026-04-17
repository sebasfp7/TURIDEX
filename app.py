import streamlit as st
import pandas as pd
from groq import Groq
import json
import pdfplumber
from docx import Document
from pptx import Presentation
import time
import google.generativeai as genai # Necesitas instalar google-generativeai

# ==================== 1. CONFIGURACIÓN Y ESTILOS ====================
st.set_page_config(page_title="Finatrix Tank v8.0", layout="wide")

st.markdown("""
    <style>
    .pilar-card { padding: 15px; border-radius: 8px; border-top: 4px solid #2563eb; background-color: #f8fafc; height: 100%; margin-bottom: 10px; border: 1px solid #e2e8f0; }
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

def safe_format(valor, tipo='num'):
    if not isinstance(valor, (int, float)): return "N/D"
    if tipo == 'pct': return f"{valor:.2%}"
    if tipo == 'x': return f"{valor:.2f}x"
    return f"${valor:,.0f}"

# ==================== 2. LECTORES DE DOCUMENTOS ====================
def leer_contenido(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    text = ""
    try:
        if ext == 'xlsx':
            xls = pd.ExcelFile(uploaded_file)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet).head(35)
                text += f"\nHoja: {sheet}\n{df.to_csv(index=False)}\n"
        elif ext == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif ext == 'docx':
            doc = Document(uploaded_file)
            text = "\n".join([p.text for p in doc.paragraphs])
        return text[:18000]
    except: return None

# ==================== 3. MOTORES DE IA (EL CASCADAZO) ====================

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
    model = genai.GenerativeModel('gemini-1.5-flash', 
                                 generation_config={"response_mime_type": "application/json"})
    res = model.generate_content(prompt)
    return json.loads(res.text)

# ==================== 4. INTERFAZ Y EJECUCIÓN ====================
st.title("🛡️ Finatrix Elite | Multi-Engine Tank")

with st.sidebar:
    st.header("🔑 Llaves de Poder")
    key_groq = st.text_input("Groq API Key", type="password")
    key_gemini = st.text_input("Gemini API Key", type="password")
    st.info("💡 Si una falla, usaremos la siguiente automáticamente.")

archivo = st.file_uploader("Subir Estados Financieros", type=["xlsx", "pdf", "docx"])

if archivo:
    if st.button("🚀 Iniciar Auditoría de Alto Nivel"):
        raw_text = leer_contenido(archivo)
        
        # EL PROMPT MAESTRO (Tu configuración perfecta)
        prompt = f"""Eres un CFO Senior y Socio de Consultora Big4. Analiza este contenido: {raw_text}
        Devuelve ÚNICAMENTE un JSON con esta estructura:
        {{
          "m": {{ "cagr": 0, "ebitda_m": 0, "liquidez": 0, "eva": 0, "wacc": 0, "score": 0 }},
          "resumen_ejecutivo": "...",
          "diagnostico_pilares": {{ "rentabilidad": "...", "liquidez": "...", "solvencia": "...", "creacion_valor": "..." }},
          "semaforo": {{ "verde": [], "amarillo": [], "rojo": [] }},
          "plan_90_dias": {{ "t30": "...", "t60": "...", "t90": "..." }}
        }}"""

        analisis_exitoso = False
        data = None

        # INTENTO 1: GROQ
        if key_groq and not analisis_exitoso:
            try:
                with st.spinner("Intentando con Motor Groq (Llama 3.3)..."):
                    data = motor_groq(key_groq, prompt)
                    analisis_exitoso = True
                    st.toast("✅ Groq respondió con éxito")
            except Exception as e:
                st.warning(f"⚠️ Groq fuera de servicio o límite alcanzado.")

        # INTENTO 2: GEMINI (Fallback)
        if key_gemini and not analisis_exitoso:
            try:
                with st.spinner("Intentando con Motor Gemini 1.5 Flash..."):
                    data = motor_gemini(key_gemini, prompt)
                    analisis_exitoso = True
                    st.toast("✅ Gemini al rescate")
            except Exception as e:
                st.error(f"❌ Gemini también falló.")

        # --- MOSTRAR RESULTADOS SI ALGUNA IA RESPONDIÓ ---
        if analisis_exitoso and data:
            m = data.get('m', {})
            # Dashboard
            c_met1, c_met2, c_met3 = st.columns(3)
            c_met1.metric("Score Estratégico", f"{m.get('score', 0)}/100")
            c_met2.metric("EVA", safe_format(m.get('eva')))
            c_met3.metric("WACC", safe_format(m.get('wacc'), 'pct'))

            st.write("---")
            st.subheader("📋 Resumen Ejecutivo")
            st.info(data.get('resumen_ejecutivo', ''))

            st.write("---")
            st.subheader("🔬 Diagnóstico por Pilares")
            diag = data.get('diagnostico_pilares', {})
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown(f'<div class="pilar-card"><strong>📈 Rentabilidad</strong><br>{diag.get("rentabilidad")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="pilar-card"><strong>💧 Liquidez</strong><br>{diag.get("liquidez")}</div>', unsafe_allow_html=True)
            with col_p2:
                st.markdown(f'<div class="pilar-card"><strong>🏗️ Solvencia</strong><br>{diag.get("solvencia")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="pilar-card"><strong>💎 Creación de Valor</strong><br>{diag.get("creacion_valor")}</div>', unsafe_allow_html=True)

            st.write("---")
            st.subheader("🚦 Semáforo de Gestión Directiva")
            sem = data.get('semaforo', {})
            cs1, cs2, cs3 = st.columns(3)
            cs1.success("**FORTALEZAS**\n\n" + "\n".join([f"• {x}" for x in sem.get('verde', [])]))
            cs2.warning("**ALERTAS**\n\n" + "\n".join([f"• {x}" for x in sem.get('amarillo', [])]))
            cs3.error("**PELIGROS**\n\n" + "\n".join([f"• {x}" for x in sem.get('rojo', [])]))

            st.write("---")
            st.subheader("🎯 Hoja de Ruta (90 Días)")
            plan = data.get('plan_90_dias', {})
            t1, t2, t3 = st.tabs(["Fase 1", "Fase 2", "Fase 3"])
            t1.markdown(plan.get('t30', ''))
            t2.markdown(plan.get('t60', ''))
            t3.markdown(plan.get('t90', ''))
        else:
            st.error("No se pudo obtener el análisis. Revisa tus API Keys o espera un minuto.")
