import streamlit as st
import pandas as pd
from groq import Groq
import json
import io
import pdfplumber
from docx import Document
from pptx import Presentation

# ==================== 1. CONFIGURACIÓN ====================
st.set_page_config(page_title="Finatrix Elite v7.4", layout="wide")

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
        return text[:20000] # Reducido para evitar Rate Limit
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

# ==================== 3. INTERFAZ Y LÓGICA ====================
st.title("🛡️ Finatrix Elite | CFO Strategy")
st.sidebar.markdown("### ⚙️ Configuración")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Documentos Financieros", type=["xlsx", "pdf", "docx", "pptx"])

if api_key and archivo:
    client = Groq(api_key=api_key)
    
    if st.button("🚀 Ejecutar Auditoría Estratégica"):
        with st.spinner("Procesando en una sola ráfaga para evitar límites..."):
            raw_text = leer_contenido(archivo)
            
            if raw_text:
                # LLAMADA ÚNICA A LA IA
                prompt = f"""Eres un CFO Senior de una Big4. Analiza los datos y devuelve UN SOLO JSON.
                DATOS A EXTRAER Y ANALIZAR: {raw_text}

                JSON STRUCTURE:
                {{
                  "m": {{
                    "cagr": num, "ebitda_m": num, "liquidez": num, "eva": num, "wacc": num, "activos": num
                  }},
                  "score": 0-100,
                  "resumen": "Análisis de salud en 2 párrafos.",
                  "pilares": {{
                    "rentabilidad": "...", "liquidez": "...", "solvencia": "...", "creacion_valor": "..."
                  }},
                  "semaforo": {{ "verde": [], "amarillo": [], "rojo": [] }},
                  "plan": {{ "t30": "...", "t60": "...", "t90": "..." }}
                }}"""

                try:
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"user", "content":prompt}],
                        response_format={"type":"json_object"}
                    )
                    data = json.loads(res.choices[0].message.content)
                    m = data['m']

                    # --- VISUALIZACIÓN ---
                    col_s1, col_s2, col_s3 = st.columns(3)
                    col_s1.metric("Salud Estratégica", f"{data['score']}/100")
                    col_s2.metric("EVA", safe_format(m.get('eva')))
                    col_s3.metric("WACC", safe_format(m.get('wacc'), 'pct'))

                    st.info(data.get('resumen', ''))

                    st.subheader("🔬 Diagnóstico por Pilares")
                    diag = data.get('pilares', {})
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**📈 Rentabilidad:** {diag.get('rentabilidad')}")
                        st.markdown(f"**💧 Liquidez:** {diag.get('liquidez')}")
                    with c2:
                        st.markdown(f"**🏗️ Solvencia:** {diag.get('solvencia')}")
                        st.markdown(f"**💎 Creación de Valor:** {diag.get('creacion_valor')}")

                    st.write("---")
                    st.subheader("🚦 Semáforo Directivo")
                    sem = data.get('semaforo', {})
                    cs1, cs2, cs3 = st.columns(3)
                    cs1.success("**FORTALEZAS**\n\n" + "\n".join([f"• {x}" for x in sem.get('verde',[])]))
                    cs2.warning("**ALERTAS**\n\n" + "\n".join([f"• {x}" for x in sem.get('amarillo',[])]))
                    cs3.error("**CRÍTICO**\n\n" + "\n".join([f"• {x}" for x in sem.get('rojo',[])]))

                    st.write("---")
                    st.subheader("🎯 Plan de Acción 90 Días")
                    plan = data.get('plan', {})
                    t30, t60, t90 = st.tabs(["30 Días", "60 Días", "90 Días"])
                    t30.markdown(plan.get('t30',''))
                    t60.markdown(plan.get('t60',''))
                    t90.markdown(plan.get('t90',''))

                except Exception as e:
                    st.error(f"Error en la respuesta de IA o Límite excedido: {e}")
