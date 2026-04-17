import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go
import io
from fpdf import FPDF
from docx import Document
from pptx import Presentation
import pdfplumber

# ==================== 1. CONFIGURACIÓN Y ESTILO ====================
st.set_page_config(page_title="Finatrix Ultra v7.0", layout="wide")

st.markdown("""
    <style>
    .reportview-container .main .block-container{ padding-top: 2rem; }
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d1d5db; }
    .evidence-card { padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #2563eb; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# ==================== 2. LECTORES MULTIFORMATO ====================
def leer_archivo(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    content = ""
    try:
        if ext == 'xlsx':
            xls = pd.ExcelFile(uploaded_file)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet).head(50)
                content += f"\nHoja: {sheet}\n{df.to_csv(index=False, sep='|')}\n"
        elif ext == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                content = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        elif ext == 'docx':
            doc = Document(uploaded_file)
            content = "\n".join([p.text for p in doc.paragraphs])
        elif ext == 'pptx':
            prs = Presentation(uploaded_file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"): content += shape.text + " "
        return content[:30000] # Cap para Groq
    except Exception as e:
        st.error(f"Error leyendo {ext.upper()}: {e}")
        return None

# ==================== 3. LÓGICA DE NEGOCIO ====================
def safe_div(n, d): return n / d if d and d != 0 else 0

def procesar_ia(contexto, client):
    prompt = f"""Eres un Auditor Senior de Wall Street. Analiza este contenido financiero:
    {contexto}
    
    Genera un JSON con esta estructura exacta:
    {{
      "diagnostico": "Resumen ejecutivo...",
      "score": 0-100,
      "metricas": {{"ventas_a1": 0, "ventas_a5": 0, "ebitda": 0, "eva": 0, "wacc": 0}},
      "evidencias": [
          {{"punto": "Nombre de la métrica", "valor": "X.XX", "estado": "Riesgo/Oportunidad", "porque": "Explicación"}},
          ...
      ]
    }}"""
    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user", "content":prompt}], response_format={"type":"json_object"})
    return json.loads(res.choices[0].message.content)

# ==================== 4. INTERFAZ PRINCIPAL ====================
st.sidebar.header("🛡️ Finatrix Ultra v7.0")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Balance/Informe (Excel, PDF, Word, PPT)", type=["xlsx", "pdf", "docx", "pptx"])

if api_key and archivo:
    client = Groq(api_key=api_key)
    if st.button("🚀 Iniciar Auditoría Profunda"):
        raw_text = leer_archivo(archivo)
        if raw_text:
            data = procesar_ia(raw_text, client)
            
            # --- DISEÑO DE INFORMACIÓN ---
            st.title("📊 Informe de Situación Financiera")
            st.markdown(f"### {data['diagnostico']}")
            
            c1, c2, c3 = st.columns(3)
            m = data['metricas']
            c1.metric("Salud Global", f"{data['score']}/100")
            c2.metric("EVA Detectado", f"${m['eva']:,.0f}")
            c3.metric("WACC", f"{m['wacc']:.2%}")

            # --- TABLA DE EVIDENCIAS (NUEVO DISEÑO) ---
            st.write("---")
            st.subheader("🔍 Memoria de Cálculo y Justificación de Riesgos")
            
            df_ev = pd.DataFrame(data['evidencias'])
            def color_estado(val):
                color = '#fee2e2' if val == 'Riesgo' else '#dcfce7'
                return f'background-color: {color}'
            
            st.table(df_ev.style.applymap(color_estado, subset=['estado']))

            # --- EXPORTACIONES CORREGIDAS ---
            st.write("---")
            st.subheader("📥 Exportar Resultados")
            ce1, ce2, ce3 = st.columns(3)
            
            # PDF
            with ce1:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "Informe Auditoría Finatrix", 0, 1)
                pdf.set_font("Arial", size=10); pdf.multi_cell(0, 5, data['diagnostico'].encode('latin-1', 'replace').decode('latin-1'))
                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("PDF", pdf_bytes, "Informe.pdf", "application/pdf")

            # WORD
            with ce2:
                doc = Document()
                doc.add_heading("Informe Finatrix", 0)
                doc.add_paragraph(data['diagnostico'])
                doc_io = io.BytesIO()
                doc.save(doc_io); doc_io.seek(0)
                st.download_button("Word", doc_io.getvalue(), "Informe.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

            # EXCEL (NUEVO)
            with ce3:
                excel_io = io.BytesIO()
                with pd.ExcelWriter(excel_io, engine='openpyxl') as writer:
                    df_ev.to_excel(writer, index=False, sheet_name='Evidencias')
                    pd.DataFrame([m]).to_excel(writer, index=False, sheet_name='Metricas')
                excel_io.seek(0)
                st.download_button("Excel de Auditoría", excel_io.getvalue(), "Auditoria.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
