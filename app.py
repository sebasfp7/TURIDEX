import streamlit as st
import pandas as pd
import fitz
from docx import Document
from groq import Groq
import json
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from fpdf import FPDF
import io

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

def generar_pdf(ratios, alertas, diagnostico):
    pdf = FinatrixPDF()
    pdf.add_page()
    
    # Score
    score = ratios.get('finatrix_score', 0)
    pdf.chapter_title("1. EVALUACION GENERAL")
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"FINATRIX SCORE: {score}/100", 0, 1, 'C')
    
    # Ratios
    pdf.ln(5)
    pdf.chapter_title("2. INDICADORES CLAVE")
    pdf.set_font('Arial', '', 10)
    for k, v in ratios.items():
        if k != "finatrix_score" and v:
            pdf.cell(100, 7, k.replace('_', ' ').title(), 1)
            pdf.cell(0, 7, f"{v:.2f}", 1, 1)

    # Diagnóstico (Recuperado para el PDF)
    pdf.ln(5)
    pdf.chapter_title("3. DIAGNOSTICO ESTRATEGICO")
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, diagnostico.encode('latin-1', 'replace').decode('latin-1'))
    
    return pdf.output(dest='S')

# ==================== 2. LÓGICA FINANCIERA ====================
class FinatrixData(BaseModel):
    ingresos_totales: Optional[float] = None
    costo_ventas: Optional[float] = None
    gastos_operativos: Optional[float] = None
    utilidad_neta: Optional[float] = None
    activos_corrientes: Optional[float] = None
    activos_totales: Optional[float] = None
    pasivos_corrientes: Optional[float] = None
    pasivos_totales: Optional[float] = None
    patrimonio: Optional[float] = None

def calcular_metricas(d: FinatrixData):
    def s(v): return v if v is not None else 0.0
    ing = s(d.ingresos_totales)
    ebitda = ing - s(d.costo_ventas) - s(d.gastos_operativos)
    
    r = {
        "ebitda": ebitda,
        "liquidez_corriente": s(d.activos_corrientes) / s(d.pasivos_corrientes) if s(d.pasivos_corrientes) > 0.1 else 0,
        "roe": (s(d.utilidad_neta) / s(d.patrimonio) * 100) if s(d.patrimonio) > 0 else 0,
        "endeudamiento": (s(d.pasivos_totales) / s(d.activos_totales) * 100) if s(d.activos_totales) > 0 else 0,
    }
    
    # Score normalizado
    pts = 30 # Base
    pts += 25 if r["liquidez_corriente"] >= 1.2 else -10
    pts += 25 if r["ebitda"] > 0 else -20
    pts += 20 if r["endeudamiento"] < 60 else 5
    r["finatrix_score"] = int(max(0, min(100, pts)))
    return r

# ==================== 3. PROCESAMIENTO MULTI-FORMATO ====================
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
        st.error(f"Error al leer archivo: {e}")
    return None

def analizar_con_ia(texto, client):
    # 1. Extracción de Datos
    p1 = f"Extrae SOLO JSON con campos contables: {texto[:10000]}"
    res_datos = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": p1}],
        response_format={"type": "json_object"}
    )
    datos_raw = json.loads(res_datos.choices[0].message.content)
    
    # 2. Diagnóstico Narrativo (Recuperado)
    p2 = f"Como CFO, da un diagnóstico breve de 3 puntos sobre estos datos: {datos_raw}"
    res_diag = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": p2}]
    )
    return datos_raw, res_diag.choices[0].message.content

# ==================== 4. INTERFAZ ====================
st.set_page_config(page_title="Finatrix V6.3", layout="wide")
st.title("🛡️ Finatrix V6.3 - Enterprise")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
archivo = st.file_uploader("Sube Balance (PDF, Excel, Word)", type=["pdf", "xlsx", "docx"])

if archivo:
    if st.button("🚀 Iniciar Auditoría"):
        with st.spinner("Procesando multi-formato e IA..."):
            texto = extraer_texto(archivo)
            if not texto or len(texto.strip()) < 50:
                st.error("Documento ilegible o vacío.")
                st.stop()
                
            datos_raw, diagnostico = analizar_con_ia(texto, client)
            
            # Limpieza y validación
            for k, v in datos_raw.items():
                if isinstance(v, str):
                    datos_raw[k] = float(v.replace(',','').replace('$','')) if v else 0.0
            
            ratios = calcular_metricas(FinatrixData(**datos_raw))
            
            # UI de Resultados
            st.success("Análisis completo")
            c1, c2, c3 = st.columns(3)
            c1.metric("SCORE", f"{ratios['finatrix_score']}/100")
            c2.metric("LIQUIDEZ", f"{ratios['liquidez_corriente']:.2f}")
            c3.metric("ENDEUDAMIENTO", f"{ratios['endeudamiento']:.1f}%")
            
            st.subheader("📝 Diagnóstico del CFO")
            st.info(diagnostico)
            
            # Botón de Descarga
            pdf_bytes = generar_pdf(ratios, {"positivas": ["Análisis exitoso"]}, diagnostico)
            st.download_button("📥 Descargar Reporte PDF", pdf_bytes, "Reporte.pdf", "application/pdf")
