import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from docx import Document
from groq import Groq
import json
import io
import re
from datetime import datetime
from fpdf import FPDF

# IMPORTACIONES CRÍTICAS QUE FALTABAN (Fix NameError)
from pydantic import BaseModel
from typing import Optional

# ==================== 1. MOTOR DE PDF PROFESIONAL ====================
class FinatrixPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'FINATRIX: INFORME FINANCIERO PROFESIONAL', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 10, f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(4)

def generar_pdf(ratios, diagnostico):
    pdf = FinatrixPDF()
    pdf.add_page()
    
    score = ratios.get('finatrix_score', 0)
    pdf.chapter_title("1. EVALUACION GENERAL")
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"FINATRIX SCORE: {score}/100", 0, 1, 'C')
    
    pdf.ln(5)
    pdf.chapter_title("2. INDICADORES CLAVE")
    pdf.set_font('Arial', '', 10)
    for k, v in ratios.items():
        if k != "finatrix_score":
            label = k.replace('_', ' ').title()
            val = f"{v:,.2f}" if isinstance(v, (int, float)) else str(v)
            pdf.cell(100, 7, label, 1)
            pdf.cell(0, 7, val, 1, 1)

    pdf.ln(5)
    pdf.chapter_title("3. DIAGNOSTICO ESTRATEGICO")
    pdf.set_font('Arial', '', 10)
    # Limpieza de caracteres para FPDF
    clean_diag = diagnostico.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_diag)
    
    return pdf.output(dest='S')

# ==================== 2. MODELO Y LOGICA (Fix NameError & ValidationError) ====================
class FinatrixData(BaseModel):
    ingresos_totales: Optional[float] = 0.0
    costo_ventas: Optional[float] = 0.0
    gastos_operativos: Optional[float] = 0.0
    utilidad_neta: Optional[float] = 0.0
    activos_corrientes: Optional[float] = 0.0
    activos_totales: Optional[float] = 0.0
    pasivos_corrientes: Optional[float] = 0.0
    pasivos_totales: Optional[float] = 0.0
    patrimonio: Optional[float] = 0.0

def calcular_metricas(d: FinatrixData):
    ing = d.ingresos_totales or 0.0
    ebitda = ing - (d.costo_ventas or 0.0) - (d.gastos_operativos or 0.0)
    
    def div(n, d_val): return n / d_val if d_val and d_val != 0 else 0
    
    r = {
        "ebitda": ebitda,
        "liquidez_corriente": div(d.activos_corrientes, d.pasivos_corrientes),
        "roe": div(d.utilidad_neta, d.patrimonio) * 100,
        "endeudamiento": div(d.pasivos_totales, d.activos_totales) * 100,
    }
    
    pts = 30
    pts += 25 if r["liquidez_corriente"] >= 1.1 else -10
    pts += 25 if r["ebitda"] > 0 else -20
    pts += 20 if r["endeudamiento"] < 70 else 5
    r["finatrix_score"] = int(max(0, min(100, pts)))
    return r

# ==================== 3. EXTRACCION MULTI-FORMATO ====================
def extraer_texto(archivo):
    ext = archivo.name.split('.')[-1].lower()
    buffer = archivo.getbuffer()
    try:
        if ext == 'pdf':
            doc = fitz.open(stream=buffer, filetype="pdf")
            return "\n".join([p.get_text() for p in doc])
        elif ext in ['xlsx', 'xls']:
            return pd.read_excel(io.BytesIO(buffer)).to_string()
        elif ext == 'docx':
            doc = Document(io.BytesIO(buffer))
            return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
    return None

# ==================== 4. UI Y FLUJO PRINCIPAL ====================
st.set_page_config(page_title="Finatrix V6.5", layout="wide")
st.title("🛡️ Finatrix V6.5 - Estabilidad Total")

# Configuración de API
if "GROQ_API_KEY" not in st.secrets:
    st.error("Falta la clave API en secrets.")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
archivo = st.file_uploader("Subir Balance", type=["pdf", "xlsx", "docx"])

if archivo:
    if st.button("🚀 Ejecutar Análisis"):
        with st.spinner("Analizando y blindando datos..."):
            texto = extraer_texto(archivo)
            if not texto: st.stop()

            # 1. IA: Extracción
            res_datos = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"Extrae JSON contable: {texto[:10000]}"}],
                response_format={"type": "json_object"}
            )
            datos_raw = json.loads(res_datos.choices[0].message.content)
            
            # 2. IA: Diagnóstico (Valor Agregado)
            res_diag = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"Da un diagnóstico de CFO para estos datos: {datos_raw}"}]
            )
            diagnostico = res_diag.choices[0].message.content

            # 3. ESCUDO DE DATOS (Limpieza Radical)
            datos_limpios = {}
            for campo in FinatrixData.model_fields:
                val = datos_raw.get(campo, 0.0)
                if isinstance(val, str):
                    val = re.sub(r'[^\d.-]', '', val.replace(',', '.'))
                try:
                    datos_limpios[campo] = float(val) if val else 0.0
                except:
                    datos_limpios[campo] = 0.0

            # 4. CÁLCULOS Y UI
            data_instancia = FinatrixData(**datos_limpios)
            ratios = calcular_metricas(data_instancia)
            
            st.success("✅ Auditoría completada")
            c1, c2, c3 = st.columns(3)
            c1.metric("SCORE", f"{ratios['finatrix_score']}/100")
            c2.metric("EBITDA", f"${ratios['ebitda']:,.0f}")
            c3.metric("LIQUIDEZ", f"{ratios['liquidez_corriente']:.2f}")

            st.info(f"**Diagnóstico CFO:**\n\n{diagnostico}")

            # 5. PDF
            pdf_bytes = generar_pdf(ratios, diagnostico)
            st.download_button("📥 Descargar Reporte PDF", pdf_bytes, "Reporte_Finatrix.pdf", "application/pdf")
