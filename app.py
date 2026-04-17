import streamlit as st
import pandas as pd
from groq import Groq
import json
import pdfplumber
from docx import Document
from pptx import Presentation

# ==================== 1. CONFIGURACIÓN Y ESTILO ====================
st.set_page_config(page_title="Finatrix Elite v7.5", layout="wide")

st.markdown("""
    <style>
    .report-box { padding: 20px; border-radius: 10px; border: 1px solid #e1e4e8; background-color: #ffffff; margin-bottom: 20px; }
    .pilar-card { padding: 15px; border-radius: 8px; border-top: 4px solid #2563eb; background-color: #f8fafc; height: 100%; }
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

def safe_format(valor, tipo='num'):
    if not isinstance(valor, (int, float)): return "N/D"
    if tipo == 'pct': return f"{valor:.2%}"
    if tipo == 'x': return f"{valor:.2f}x"
    return f"${valor:,.0f}"

# ==================== 2. LECTOR DE ARCHIVOS ====================
def leer_contenido(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    text = ""
    try:
        if ext == 'xlsx':
            xls = pd.ExcelFile(uploaded_file)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet).head(40)
                text += f"\nHoja: {sheet}\n{df.to_csv(index=False)}\n"
        elif ext == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
        elif ext == 'docx':
            doc = Document(uploaded_file)
            text = "\n".join([p.text for p in doc.paragraphs])
        elif ext == 'pptx':
            prs = Presentation(uploaded_file)
            text = "\n".join([shape.text for slide in prs.slides for shape in slide.shapes if hasattr(shape, "text")])
        return text[:18000] # Límite prudente de tokens para evitar Rate Limit
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

# ==================== 3. LÓGICA DE NEGOCIO (ONE-SHOT) ====================
st.title("🛡️ Finatrix Elite | Consultoría Estratégica")
st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Estados Financieros", type=["xlsx", "pdf", "docx", "pptx"])

if api_key and archivo:
    client = Groq(api_key=api_key)
    
    if st.button("🚀 Iniciar Auditoría de Alto Nivel"):
        with st.spinner("Generando diagnóstico financiero..."):
            raw_text = leer_contenido(archivo)
            
            if raw_text:
                # UN SOLO PROMPT PARA TODO: MÉTRICAS + ANÁLISIS PROFUNDO
                prompt = f"""Eres un CFO Senior y Socio de Consultora Big4. Tu cliente es el dueño de la empresa.
                Analiza este contenido y extrae los números reales para el análisis: {raw_text}

                TAREA: Devuelve ÚNICAMENTE un JSON con esta estructura:
                {{
                  "m": {{ "cagr": num, "ebitda_m": num, "liquidez": num, "eva": num, "wacc": num, "act_tot": num }},
                  "score": 0-100,
                  "resumen_ejecutivo": "2 párrafos: Veredicto de salud y por qué gana o pierde plata.",
                  "diagnostico_pilares": {{
                    "rentabilidad": "Análisis profundo con números.",
                    "liquidez": "Análisis de capacidad de pago.",
                    "solvencia": "Análisis de deuda y estrés del dueño.",
                    "creacion_valor": "Análisis de EVA brutalmente honesto."
                  }},
                  "semaforo": {{ "verde": ["3 fortalezas"], "amarillo": ["2 alertas"], "rojo": ["2 críticos"] }},
                  "plan_90_dias": {{ "t30": "Urgente", "t60": "Táctico", "t90": "Estratégico" }}
                }}"""

                try:
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"user", "content":prompt}],
                        response_format={"type":"json_object"}
                    )
                    data = json.loads(res.choices[0].message.content)
                    m = data.get('m', {})

                    # --- INTERFAZ DE RESULTADOS ---
                    # 1. Indicadores Clave
                    c_met1, c_met2, c_met3 = st.columns(3)
                    c_met1.metric("Score Estratégico", f"{data.get('score')}/100")
                    c_met2.metric("EVA (Creación Valor)", safe_format(m.get('eva')))
                    c_met3.metric("WACC", safe_format(m.get('wacc'), 'pct'))

                    # 2. Resumen
                    st.write("---")
                    st.subheader("📋 Resumen Ejecutivo")
                    st.info(data.get('resumen_ejecutivo', ''))

                    # 3. Diagnóstico por Pilares
                    st.write("---")
                    st.subheader("🔬 Diagnóstico por Pilares")
                    diag = data.get('diagnostico_pilares', {})
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        st.markdown(f'<div class="pilar-card"><strong>📈 Rentabilidad</strong><br>{diag.get("rentabilidad")}</div>', unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown(f'<div class="pilar-card"><strong>💧 Liquidez</strong><br>{diag.get("liquidez")}</div>', unsafe_allow_html=True)
                    with col_p2:
                        st.markdown(f'<div class="pilar-card"><strong>🏗️ Solvencia</strong><br>{diag.get("solvencia")}</div>', unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        st.markdown(f'<div class="pilar-card"><strong>💎 Creación de Valor</strong><br>{diag.get("creacion_valor")}</div>', unsafe_allow_html=True)

                    # 4. Semáforo
                    st.write("---")
                    st.subheader("🚦 Semáforo de Gestión Directiva")
                    sem = data.get('semaforo', {})
                    cs1, cs2, cs3 = st.columns(3)
                    cs1.success("**FORTALEZAS**\n\n" + "\n".join([f"• {x}" for x in sem.get('verde', [])]))
                    cs2.warning("**ALERTAS**\n\n" + "\n".join([f"• {x}" for x in sem.get('amarillo', [])]))
                    cs3.error("**PELIGROS**\n\n" + "\n".join([f"• {x}" for x in sem.get('rojo', [])]))

                    # 5. Plan de Acción
                    st.write("---")
                    st.subheader("🎯 Hoja de Ruta (Próximos 90 Días)")
                    plan = data.get('plan_90_dias', {})
                    t1, t2, t3 = st.tabs(["Fase 1: Inmediata", "Fase 2: Táctica", "Fase 3: Estructural"])
                    t1.markdown(plan.get('t30', ''))
                    t2.markdown(plan.get('t60', ''))
                    t3.markdown(plan.get('t90', ''))

                except Exception as e:
                    st.error("Límite de API alcanzado o error de procesamiento. Por favor, espera 30 segundos e intenta de nuevo.")
                    st.code(e)
