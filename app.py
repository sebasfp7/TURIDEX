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

# ==================== 1. CONFIGURACIÓN Y ESTILOS ====================
st.set_page_config(page_title="Finatrix Ultra v7.1", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e9ecef; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #2563eb; color: white; }
    </style>
    """, unsafe_allow_html=True)

# ==================== 2. LECTORES DE ARCHIVOS ====================
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
        return content[:30000]
    except Exception as e:
        st.error(f"Error procesando {ext.upper()}: {e}")
        return None

# ==================== 3. PROCESAMIENTO IA ====================
def procesar_ia(contexto, client):
    prompt = f"""Eres un Partner de Auditoría. Analiza este contenido financiero y extrae métricas clave.
    Contenido: {contexto}
    
    Responde ÚNICAMENTE en JSON con esta estructura:
    {{
      "diagnostico": "Resumen ejecutivo...",
      "score": 70,
      "metricas": {{"ventas_a1": 100, "ventas_a5": 500, "ebitda": 50, "eva": 759, "wacc": 0.1152}},
      "evidencias": [
          {{"punto": "Nombre métrica", "valor": "10%", "estado": "Riesgo", "porque": "razón..."}},
          {{"punto": "Nombre métrica", "valor": "20%", "estado": "Oportunidad", "porque": "razón..."}}
      ]
    }}"""
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile", 
        messages=[{"role":"user", "content":prompt}], 
        response_format={"type":"json_object"}
    )
    return json.loads(res.choices[0].message.content)

# ==================== 4. INTERFAZ Y RENDERIZADO ====================
st.sidebar.title("🛡️ Finatrix Ultra v7.1")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Sube Excel, PDF, Word o PPT", type=["xlsx", "pdf", "docx", "pptx"])

if api_key and archivo:
    client = Groq(api_key=api_key)
    if st.button("🚀 Iniciar Análisis"):
        try:
            with st.spinner("Analizando documentos y detectando riesgos..."):
                raw_text = leer_archivo(archivo)
                data = procesar_ia(raw_text, client)
                
                # --- CABECERA ---
                st.title("📊 Informe de Situación Financiera")
                st.info(data['diagnostico'])
                
                # --- MÉTRICAS ---
                m = data['metricas']
                col1, col2, col3 = st.columns(3)
                col1.metric("Salud Global", f"{data['score']}/100")
                col2.metric("EVA Detectado", f"${m.get('eva', 0):,.0f}")
                col3.metric("WACC", f"{m.get('wacc', 0):.2%}")

                # --- TABLA DE RIESGOS (FIXED) ---
                st.subheader("🔍 Memoria de Cálculo y Justificación de Riesgos")
                df_ev = pd.DataFrame(data['evidencias'])
                
                # Fix para el error de estilo: validamos que existan las columnas
                if not df_ev.empty:
                    def highlight_rows(row):
                        color = '#fee2e2' if row['estado'] == 'Riesgo' else '#dcfce7'
                        return [f'background-color: {color}'] * len(row)
                    
                    # Usamos 'apply' en lugar del problemático 'applymap'
                    st.dataframe(df_ev.style.apply(highlight_rows, axis=1), use_container_width=True)
                else:
                    st.warning("No se pudieron generar evidencias tabulares.")

                # --- EXPORTACIONES ---
                st.write("---")
                st.subheader("📥 Descargar Reportes")
                e1, e2, e3 = st.columns(3)

                # PDF con FPDF
                with e1:
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16); pdf.cell(0, 10, "Informe Finatrix", 0, 1)
                    pdf.set_font("Arial", size=10); pdf.multi_cell(0, 6, data['diagnostico'].encode('latin-1', 'replace').decode('latin-1'))
                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    st.download_button("Descargar PDF", pdf_bytes, "informe.pdf", "application/pdf")

                # Word con python-docx
                with e2:
                    doc = Document()
                    doc.add_heading("Informe de Auditoría", 0)
                    doc.add_paragraph(data['diagnostico'])
                    doc_buffer = io.BytesIO()
                    doc.save(doc_buffer); doc_buffer.seek(0)
                    st.download_button("Descargar Word", doc_buffer.getvalue(), "informe.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

                # Excel con pandas
                with e3:
                    ex_buffer = io.BytesIO()
                    with pd.ExcelWriter(ex_buffer, engine='openpyxl') as writer:
                        df_ev.to_excel(writer, index=False, sheet_name='Evidencias')
                    ex_buffer.seek(0)
                    st.download_button("Descargar Excel", ex_buffer.getvalue(), "evidencias.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        except Exception as e:
            st.error(f"Falla crítica en la visualización: {e}")
            st.code(e) # Para ver el error exacto en pantalla
