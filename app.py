import streamlit as st
import pandas as pd
from groq import Groq
import json
import pdfplumber
from docx import Document
from pptx import Presentation
import time

# ==================== 1. CONFIGURACIÓN ====================
st.set_page_config(page_title="Finatrix Resilient v7.6", layout="wide")

# (Funciones de lectura de archivos se mantienen igual que v7.5)
def leer_contenido(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    text = ""
    try:
        if ext == 'xlsx':
            xls = pd.ExcelFile(uploaded_file)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet).head(30) # Reducido para ahorrar tokens
                text += f"\nHoja: {sheet}\n{df.to_csv(index=False)}\n"
        elif ext == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif ext == 'docx':
            doc = Document(uploaded_file)
            text = "\n".join([p.text for p in doc.paragraphs])
        return text[:15000] # Más corto = menos riesgo de error 429
    except: return None

# ==================== 2. MOTOR MULTI-IA (EL SECRETO) ====================
def ejecutar_analisis_robusto(client, prompt):
    # Lista de modelos de mejor a peor, pero con más límite
    modelos = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    
    for modelo in modelos:
        try:
            res = client.chat.completions.create(
                model=modelo,
                messages=[{"role":"user", "content":prompt}],
                response_format={"type":"json_object"}
            )
            return json.loads(res.choices[0].message.content), modelo
        except Exception as e:
            if "rate_limit" in str(e).lower():
                st.warning(f"⚠️ Límite alcanzado en {modelo}. Saltando al siguiente cerebro...")
                time.sleep(1) # Pausa técnica
                continue
            else:
                raise e
    return None, None

# ==================== 3. INTERFAZ ====================
st.title("🛡️ Finatrix Elite | Multi-Engine")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Documento Financiero", type=["xlsx", "pdf", "docx"])

if api_key and archivo:
    client = Groq(api_key=api_key)
    
    if st.button("🚀 Iniciar Auditoría Resiliente"):
        with st.spinner("Buscando IA disponible para el análisis..."):
            raw_text = leer_contenido(archivo)
            
            if raw_text:
                # TU PROMPT PERFECTO
                prompt = f"""Eres un CFO Senior de Big4. Analiza: {raw_text}
                Devuelve JSON: {{
                  "m": {{ "eva": num, "wacc": num, "score": num }},
                  "resumen_ejecutivo": "...",
                  "diagnostico_pilares": {{ "rentabilidad": "...", "liquidez": "...", "solvencia": "...", "creacion_valor": "..." }},
                  "semaforo": {{ "verde": [], "amarillo": [], "rojo": [] }},
                  "plan_90_dias": {{ "t30": "...", "t60": "...", "t90": "..." }}
                }}"""

                data, modelo_usado = ejecutar_analisis_robusto(client, prompt)
                
                if data:
                    st.success(f"✅ Análisis completado con éxito usando: {modelo_usado}")
                    # --- AQUÍ VA TODO EL RENDERIZADO DE TABLAS Y MÉTRICAS QUE YA TENÍAMOS ---
                    # (Copia el código de visualización de la v7.5 aquí)
                    m = data.get('m', {})
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Salud", f"{m.get('score', 0)}/100")
                    c2.metric("EVA", f"${m.get('eva', 0):,.0f}")
                    c3.metric("WACC", f"{m.get('wacc', 0):.2%}")
                    
                    st.info(data.get('resumen_ejecutivo'))
                    # ... rest of the UI ...
                else:
                    st.error("❌ Todos los motores de IA están saturados. Espera 60 segundos.")
