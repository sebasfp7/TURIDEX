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

# ==================== 1. MOTOR DE PDF PROFESIONAL (Fix Encoding) ====================
class FinatrixPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'FINATRIX: INFORME FINANCIERO PROFESIONAL', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 10, f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.ln(4)

def generar_pdf(ratios, diagnostico, alertas):
    pdf = FinatrixPDF()
    pdf.add_page()
    
    # 1. Score
    score = ratios.get('finatrix_score', 0)
    pdf.chapter_title("1. RESUMEN EJECUTIVO")
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, f"FINATRIX SCORE: {score}/100", 0, 1, 'C')
    
    # 2. Ratios (Los 12 recuperados)
    pdf.ln(5)
    pdf.chapter_title("2. INDICADORES FINANCIEROS CLAVE")
    pdf.set_font('Arial', '', 10)
    for k, v in ratios.items():
        if k != "finatrix_score":
            label = k.replace('_', ' ').title()
            val = f"{v:,.2f}%" if "margen" in k or "roe" in k or "endeudamiento" in k else f"{v:,.2f}"
            pdf.cell(100, 7, label, 1)
            pdf.cell(0, 7, val, 1, 1)

    # 3. Diagnóstico (Limpieza de tildes para evitar ?)
    pdf.ln(5)
    pdf.chapter_title("3. DIAGNOSTICO ESTRATEGICO (CFO)")
    pdf.set_font('Arial', '', 10)
    # Reemplazo básico de caracteres latinos para FPDF estándar
    clean_diag = diagnostico.replace('í','i').replace('á','a').replace('é','e').replace('ó','o').replace('ú','u').replace('ñ','n')
    pdf.multi_cell(0, 6, clean_diag)
    
    return pdf.output(dest='S')

# ==================== 2. MODELO Y LÓGICA (Los 12 Ratios + Inventarios) ====================
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
    inventarios: Optional[float] = 0.0 # Recuperado

def calcular_metricas(d: FinatrixData):
    def div(n, dv): return n / dv if dv and dv != 0 else 0
    ing = d.ingresos_totales or 0.0
    ebitda = ing - (d.costo_ventas or 0.0) - (d.gastos_operativos or 0.0)
    
    r = {
        "ebitda": ebitda,
        "margen_ebitda": div(ebitda, ing) * 100,
        "margen_neto": div(d.utilidad_neta, ing) * 100,
        "liquidez_corriente": div(d.activos_corrientes, d.pasivos_corrientes),
        "prueba_acida": div(d.activos_corrientes - d.inventarios, d.pasivos_corrientes),
        "roe": div(d.utilidad_neta, d.patrimonio) * 100,
        "endeudamiento": div(d.pasivos_totales, d.activos_totales) * 100,
        "deuda_patrimonio": div(d.pasivos_totales, d.patrimonio),
        "cobertura_gastos": div(ing, d.gastos_operativos)
    }
    
    # Score Profesional (Escalado)
    pts = 0
    pts += 30 if r["liquidez_corriente"] >= 1.2 else 10
    pts += 30 if r["margen_ebitda"] > 15 else 15
    pts += 20 if r["endeudamiento"] < 60 else 5
    pts += 20 if r["roe"] > 10 else 5
    r["finatrix_score"] = int(pts)
    return r

# ==================== 3. EXTRACCIÓN Y IA (Prompt Estructurado) ====================
def extraer_texto(archivo):
    ext = archivo.name.split('.')[-1].lower()
    try:
        content = archivo.read()
        if ext == 'pdf':
            doc = fitz.open(stream=content, filetype="pdf")
            return "\n".join([p.get_text() for p in doc])
        elif ext in ['xlsx', 'xls']:
            return pd.read_excel(io.BytesIO(content)).to_string()
        elif ext == 'docx':
            doc = Document(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs])
    except Exception as e:
        st.error(f"Error procesando archivo: {e}")
    return None

def llamar_ia(texto, client):
    # Prompt 1: Extracción estricta
    p_ext = f"""Extrae estos campos EXACTOS en JSON (usa 0 si no existen):
    ingresos_totales, costo_ventas, gastos_operativos, utilidad_neta, 
    activos_corrientes, activos_totales, pasivos_corrientes, pasivos_totales, patrimonio, inventarios.
    Texto: {texto[:10000]}"""
    
    try:
        res_d = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": p_ext}],
            response_format={"type": "json_object"}
        )
        datos = json.loads(res_d.choices[0].message.content)
        
        # Prompt 2: Diagnóstico basado en Ratios calculados (No en data cruda)
        p_diag = f"Como CFO, analiza estos ratios y da 3 consejos breves: {datos}"
        res_diag = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": p_diag}]
        )
        return datos, res_diag.choices[0].message.content
    except Exception as e:
        st.error(f"Error de IA: {e}")
        return None, None

# ==================== 4. UI Y ALERTAS ====================
st.set_page_config(page_title="Finatrix V6.6", layout="wide")
st.title("🛡️ Finatrix V6.6 - Enterprise Edition")

if "GROQ_API_KEY" not in st.secrets:
    st.error("Falta API Key")
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
archivo = st.file_uploader("Balance (PDF, Excel, Word)", type=["pdf", "xlsx", "docx"])

if archivo:
    if st.button("🚀 Iniciar Auditoría Master"):
        with st.spinner("Ejecutando motores de análisis..."):
            texto = extraer_texto(archivo)
            if not texto: st.stop()
            
            datos_raw, diagnostico = llamar_ia(texto, client)
            if not datos_raw: st.stop()

            # Escudo de datos
            datos_limpios = {}
            for campo in FinatrixData.model_fields:
                v = datos_raw.get(campo, 0)
                if isinstance(v, str): v = re.sub(r'[^\d.-]', '', v.replace(',', '.'))
                datos_limpios[campo] = float(v) if v else 0.0

            instancia = FinatrixData(**datos_limpios)
            r = calcular_metricas(instancia)
            
            # Dashboard
            st.success("Análisis Finalizado")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("SCORE", f"{r['finatrix_score']}/100")
            c2.metric("LIQUIDEZ", f"{r['liquidez_corriente']:.2f}x")
            c3.metric("MARGEN EBITDA", f"{r['margen_ebitda']:.1f}%")
            c4.metric("ENDEUDAMIENTO", f"{r['endeudamiento']:.1f}%")

            # Alertas visuales
            st.divider()
            col_a, col_b = st.columns(2)
            with col_a:
                if r["liquidez_corriente"] < 1.0: st.error("🚨 Riesgo de Insolvencia a corto plazo")
                if r["endeudamiento"] > 70: st.warning("⚠️ Apalancamiento elevado")
            with col_b:
                if r["roe"] > 15: st.success("🌟 Rentabilidad sobre patrimonio sobresaliente")
                if r["finatrix_score"] > 75: st.success("✅ Salud financiera sólida")

            st.subheader("📝 Diagnóstico Estratégico")
            st.info(diagnostico)

            # Exportación
            pdf_bytes = generar_pdf(r, diagnostico, [])
            st.download_button("📥 Descargar Reporte Completo", pdf_bytes, "Informe_Finatrix.pdf", "application/pdf")
