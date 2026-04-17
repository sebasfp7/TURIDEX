import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go
import pdfplumber
from docx import Document
from pptx import Presentation

# ==================== 1. CONFIGURACIÓN ====================
st.set_page_config(page_title="Finatrix Focus v7.2", layout="wide")

# Estilos CSS para mejorar la UI sin librerías externas
st.markdown("""
    <style>
    .metric-container { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e1e4e8; text-align: center; }
    .risk-card { padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 6px solid #ef4444; background-color: #fef2f2; }
    .opportunity-card { padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 6px solid #22c55e; background-color: #f0fdf4; }
    </style>
    """, unsafe_allow_html=True)

# ==================== 2. LECTORES MULTIFORMATO ====================
def leer_contenido(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    text = ""
    try:
        if ext == 'xlsx':
            df = pd.read_excel(uploaded_file).head(100)
            text = df.to_csv(index=False)
        elif ext == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif ext == 'docx':
            doc = Document(uploaded_file)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif ext == 'pptx':
            prs = Presentation(uploaded_file)
            text = "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
        return text[:25000] # Límite de tokens
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

# ==================== 3. PROCESAMIENTO CON IA ====================
def analizar_con_ia(prompt_text, client):
    sys_prompt = """Eres un Director Financiero (CFO) experto. Analiza el contenido y devuelve un JSON:
    {
      "resumen": "Breve análisis de 2 párrafos",
      "score": 0-100,
      "eva": 0,
      "wacc": 0,
      "hallazgos": [
        {"tipo": "Riesgo", "titulo": "Título", "desc": "Explicación", "impacto": "Alto/Medio"},
        {"tipo": "Oportunidad", "titulo": "Título", "desc": "Explicación", "impacto": "Alto/Medio"}
      ]
    }"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt_text}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# ==================== 4. INTERFAZ DE USUARIO ====================
st.title("🛡️ Finatrix Focus | Auditoría Inteligente")
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Cargar documento (Excel, PDF, Word, PPT)", type=["xlsx", "pdf", "docx", "pptx"])

if api_key and archivo:
    client = Groq(api_key=api_key)
    
    if st.button("🚀 Ejecutar Análisis Estratégico"):
        with st.spinner("Procesando evidencias..."):
            contenido = leer_contenido(archivo)
            if contenido:
                try:
                    data = analizar_con_ia(contenido, client)
                    
                    # --- FILA 1: DASHBOARD DE MÉTRICAS ---
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f'<div class="metric-container"><h3>Salud Financiera</h3><h2>{data["score"]}/100</h2></div>', unsafe_allow_html=True)
                    with col2:
                        st.markdown(f'<div class="metric-container"><h3>EVA</h3><h2>${data["eva"]:,.0f}</h2></div>', unsafe_allow_html=True)
                    with col3:
                        st.markdown(f'<div class="metric-container"><h3>WACC</h3><h2>{data["wacc"]:.2%}</h2></div>', unsafe_allow_html=True)
                    
                    # --- FILA 2: RESUMEN EJECUTIVO ---
                    st.write("---")
                    st.subheader("📋 Resumen del Auditor")
                    st.write(data["resumen"])
                    
                    # --- FILA 3: RIESGOS Y OPORTUNIDADES ---
                    st.write("---")
                    st.subheader("🔍 Hallazgos Críticos")
                    
                    riesgos = [h for h in data["hallazgos"] if h["tipo"] == "Riesgo"]
                    oportunidades = [h for h in data["hallazgos"] if h["tipo"] == "Oportunidad"]
                    
                    c_riesgo, c_op = st.columns(2)
                    
                    with c_riesgo:
                        st.markdown("#### 🚩 Riesgos Detectados")
                        for r in riesgos:
                            st.markdown(f"""
                                <div class="risk-card">
                                    <strong>{r['titulo']}</strong> (Impacto: {r['impacto']})<br>
                                    <small>{r['desc']}</small>
                                </div>
                            """, unsafe_allow_html=True)
                            
                    with c_op:
                        st.markdown("#### 💡 Oportunidades")
                        for o in oportunidades:
                            st.markdown(f"""
                                <div class="opportunity-card">
                                    <strong>{o['titulo']}</strong> (Impacto: {o['impacto']})<br>
                                    <small>{o['desc']}</small>
                                </div>
                            """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error al interpretar el análisis: {e}")
