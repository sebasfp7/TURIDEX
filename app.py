import streamlit as st
import pandas as pd
import fitz
from docx import Document
from groq import Groq
import json
import io
import re
from datetime import datetime
from fpdf import FPDF
from pydantic import BaseModel
from typing import Optional

# ==================== CONFIGURACIÓN Y ESTADO ====================
if 'analisis' not in st.session_state:
    st.session_state.analisis = None

# ==================== UTILIDADES ====================
def limpiar_texto_pdf(texto):
    """Limpia tildes (Mayús/Minús) y caracteres especiales para FPDF"""
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U',
        '¿': '', '¡': '', '«': '"', '»': '"', '—': '-'
    }
    for old, new in reemplazos.items():
        texto = texto.replace(old, new)
    return texto

# ==================== ENGINE DE PDF ====================
class FinatrixPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'FINATRIX: INFORME FINANCIERO PROFESIONAL', 0, 1, 'C')
        self.ln(10)

def generar_pdf(ratios, diagnostico):
    pdf = FinatrixPDF()
    pdf.add_page()
    
    # Formatos explícitos
    FORMATOS = {
        'ebitda': ('USD', False), 'margen_ebitda': ('%', True), 
        'margen_neto': ('%', True), 'liquidez_corriente': ('x', True),
        'prueba_acida': ('x', True), 'roe': ('%', True), 
        'endeudamiento': ('%', True), 'deuda_patrimonio': ('x', True),
        'cobertura_gastos': ('x', True)
    }

    # Score con color
    score = ratios.get('finatrix_score', 0)
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 15, f"FINATRIX SCORE: {score}/100", 1, 1, 'C')
    pdf.ln(5)

    # Ratios
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "INDICADORES FINANCIEROS", 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    
    for k, v in ratios.items():
        if k == "finatrix_score": continue
        label = k.replace('_', ' ').title()
        sufijo, es_p = FORMATOS.get(k, ('', False))
        val = f"{v:.2f}{sufijo}" if es_p else (f"${v:,.0f}" if sufijo == 'USD' else f"{v:.2f}{sufijo}")
        
        pdf.cell(100, 7, label, 1)
        pdf.cell(0, 7, val, 1, 1)

    # Diagnóstico
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "DIAGNOSTICO ESTRATEGICO", 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(0, 6, limpiar_texto_pdf(diagnostico))
    
    return pdf.output(dest='S')

# ==================== LÓGICA FINANCIERA ====================
class FinatrixData(BaseModel):
    ingresos_totales: float = 0.0
    costo_ventas: float = 0.0
    gastos_operativos: float = 0.0
    utilidad_neta: float = 0.0
    activos_corrientes: float = 0.0
    activos_totales: float = 0.0
    pasivos_corrientes: float = 0.0
    pasivos_totales: float = 0.0
    patrimonio: float = 0.0
    inventarios: float = 0.0

def calcular_metricas(d: FinatrixData):
    div = lambda n, dv: n / dv if dv != 0 else 0
    ebitda = d.ingresos_totales - d.costo_ventas - d.gastos_operativos
    
    r = {
        "ebitda": ebitda,
        "margen_ebitda": div(ebitda, d.ingresos_totales) * 100,
        "margen_neto": div(d.utilidad_neta, d.ingresos_totales) * 100,
        "liquidez_corriente": div(d.activos_corrientes, d.pasivos_corrientes),
        "prueba_acida": div(d.activos_corrientes - d.inventarios, d.pasivos_corrientes),
        "roe": div(d.utilidad_neta, d.patrimonio) * 100,
        "endeudamiento": div(d.pasivos_totales, d.activos_totales) * 100,
        "deuda_patrimonio": div(d.pasivos_totales, d.patrimonio),
        "cobertura_gastos": div(d.ingresos_totales, d.gastos_operativos)
    }

    # Score Gradual (Fix #1 Auditoría)
    pts = 0
    lq = r["liquidez_corriente"]
    if lq >= 1.5: pts += 30
    elif lq >= 1.2: pts += 20
    elif lq >= 1.0: pts += 10

    m_eb = r["margen_ebitda"]
    if m_eb >= 20: pts += 30
    elif m_eb >= 10: pts += 15

    end = r["endeudamiento"]
    if end <= 40: pts += 20
    elif end <= 60: pts += 10

    roe = r["roe"]
    if roe >= 15: pts += 20
    elif roe >= 8: pts += 10

    r["finatrix_score"] = int(max(0, min(100, pts)))
    return r

# ==================== IA CON FALLBACK ====================
def llamar_ia_seguro(texto, client):
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    p_ext = f"Extrae estos campos contables en JSON: ingresos_totales, costo_ventas, gastos_operativos, utilidad_neta, activos_corrientes, activos_totales, pasivos_corrientes, pasivos_totales, patrimonio, inventarios. Texto: {texto[:12000]}"
    
    for model in models:
        try:
            # 1. Extracción
            res = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": p_ext}],
                response_format={"type": "json_object"}
            )
            raw_data = json.loads(res.choices[0].message.content)
            
            # 2. Cálculo intermedio para el diagnóstico (Fix #1 Bug Crítico)
            instancia = FinatrixData(**{k: float(str(v).replace(',','')) for k,v in raw_data.items() if k in FinatrixData.model_fields})
            ratios = calcular_metricas(instancia)
            
            # 3. Diagnóstico basado en RATIOS
            res_diag = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": f"Como CFO, analiza estos RATIOS y da 3 consejos: {ratios}"}]
            )
            return raw_data, ratios, res_diag.choices[0].message.content
        except Exception as e:
            st.warning(f"Fallo en {model}, reintentando con backup...")
            continue
    return None, None, None

# ==================== UI STREAMLIT ====================
st.title("🛡️ Finatrix V6.8 Enterprise")

with st.sidebar:
    st.header("Configuración")
    key = st.text_input("Groq API Key", type="password")
    archivo = st.file_uploader("Subir Balance", type=["pdf", "docx", "xlsx"])

if archivo and key:
    client = Groq(api_key=key)
    
    if st.button("🚀 Iniciar Análisis"):
        with st.spinner("Ejecutando auditoría multicapa..."):
            # Extracción simple de texto
            if archivo.type == "application/pdf":
                doc = fitz.open(stream=archivo.read(), filetype="pdf")
                texto = "\n".join([page.get_text() for page in doc])
            else:
                texto = "Simulación de texto para otros formatos" # (Añadir lógica docx/xlsx aquí)

            raw, ratios, diag = llamar_ia_seguro(texto, client)
            
            if raw:
                st.session_state.analisis = {"ratios": ratios, "diag": diag}
                st.success("Análisis completado con éxito.")

if st.session_state.analisis:
    data = st.session_state.analisis
    r = data["ratios"]
    
    # Dashboard
    col1, col2, col3 = st.columns(3)
    col1.metric("SCORE", f"{r['finatrix_score']}/100")
    col2.metric("Liquidez", f"{r['liquidez_corriente']:.2f}x")
    col3.metric("Endeudamiento", f"{r['endeudamiento']:.1f}%")

    st.subheader("Diagnóstico Estratégico")
    st.info(data["diag"])

    # Preview & Download (Fix #11)
    with st.expander("👁️ Vista previa del Reporte"):
        st.write("El PDF incluirá todos los indicadores y el diagnóstico CFO.")
        pdf_bytes = generar_pdf(r, data["diag"])
        st.download_button("📥 Descargar PDF Oficial", pdf_bytes, "Reporte_Finatrix.pdf", "application/pdf")
