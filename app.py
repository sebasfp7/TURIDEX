import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go
import io
from fpdf import FPDF  # Usamos FPDF que es más estable para Streamlit Cloud
from docx import Document

# ==================== 1. MOTOR FINANCIERO Y FORMATEO ====================
st.set_page_config(page_title="Finatrix Elite v6.5", layout="wide")

def safe_format(valor, tipo='num'):
    if not isinstance(valor, (int, float)): return "N/D"
    if tipo == 'pct': return f"{valor:.2%}"
    if tipo == 'x': return f"{valor:.2f}x"
    return f"${valor:,.0f}"

def safe_div(n, d):
    if n is None or d is None or d == 0: return None
    return n / d

def calcular_metricas_python(d_a1, d_a5):
    v1, v5, eb5 = d_a1.get('ventas'), d_a5.get('ventas'), d_a5.get('ebitda')
    cagr = ((v5 / v1)**(1/4) - 1) if v1 and v5 and v1 > 0 and v5 > 0 else None
    return {
        "cagr": cagr,
        "m_ebitda": safe_div(eb5, v5),
        "liquidez": safe_div(d_a5.get('activos_corrientes'), d_a5.get('pasivos_corrientes')),
        "incoherencia": True if (eb5 and v5 and eb5 > v5) else False,
        "eva": d_a5.get('eva'),
        "wacc": d_a5.get('wacc'),
        "uodi": d_a5.get('uodi'),
        "activos_totales": d_a5.get('activos_totales')
    }

def validar_balance_pro(d):
    act, pas, pat = d.get('activos_totales'), d.get('pasivos_totales'), d.get('patrimonio')
    if not all(isinstance(x, (int, float)) for x in [act, pas, pat]):
        return "⚠️ Datos de balance insuficientes."
    diff = abs(act - (pas + pat))
    return f"❌ Descuadre: ${diff:,.0f}" if diff > act * 0.01 else "✅ Balance Cuadrado"

# ==================== 2. EXTRACCIÓN Y NARRATIVA ====================
def extraer_datos_excel(archivo):
    xls = pd.ExcelFile(archivo)
    texto = ""
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet).head(35)
        df_clean = df.where(pd.notnull(df), None)
        texto += f"\n--- HOJA: {sheet} ---\n{df_clean.to_csv(index=False, sep='|')}\n"
    if len(texto) > 26000:
        st.sidebar.warning("⚠️ Datos truncados por tamaño de Excel.")
        return texto[:26000] + "\n[TRUNCADO]"
    return texto

def obtener_analisis_ia(contexto, m, client):
    c_txt, e_txt = safe_format(m['cagr'], 'pct'), safe_format(m['m_ebitda'], 'pct')
    l_txt, w_txt, ev_txt = safe_format(m['liquidez'], 'x'), safe_format(m['wacc'], 'pct'), safe_format(m['eva'])

    prompt = f"""Eres Senior Partner. Analiza estos datos verificados:
    - CAGR: {c_txt} | Margen EBITDA: {e_txt} | Liquidez: {l_txt}
    - WACC: {w_txt} | EVA: {ev_txt}
    - Alerta de Incoherencia: {"SÍ" if m['incoherencia'] else "No detectada"}

    Excel context: {contexto}

    RESPONDE EXCLUSIVAMENTE EN FORMATO JSON:
    {{ "diagnostico": "markdown extenso con estructura de consultoría...", "score": 0-100 }}
    """
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user", "content":prompt}],
        response_format={"type":"json_object"}
    )
    return json.loads(res.choices[0].message.content)

# ==================== 3. INTERFAZ Y FLUJO ====================
st.sidebar.header("🛡️ Finatrix Elite v6.5")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Archivo Excel", type=["xlsx"])

if not api_key:
    st.info("🔑 Ingresa tu API Key para activar el motor.")
elif archivo:
    client = Groq(api_key=api_key)
    if st.button("🚀 Iniciar Análisis de Valor"):
        try:
            with st.spinner("Auditando estados financieros..."):
                texto_excel = extraer_datos_excel(archivo)

                extract_prompt = """Extrae SOLO JSON. Si un dato no existe usa null.
                {"año1": {"ventas":num,"ebitda":num,"activos_corrientes":num,"pasivos_corrientes":num},
                "año5": {"ventas":num,"ebitda":num,"activos_totales":num,"pasivos_totales":num,"patrimonio":num,
                "activos_corrientes":num,"pasivos_corrientes":num,"eva":num,"wacc":num,"uodi":num}}"""

                res_raw = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role":"user", "content": f"{extract_prompt}\n{texto_excel}"}],
                    response_format={"type":"json_object"}
                )
                d_raw = json.loads(res_raw.choices[0].message.content)

                d_a1, d_a5 = d_raw.get('año1', {}), d_raw.get('año5', {})
                m = calcular_metricas_python(d_a1, d_a5)
                status_bal = validar_balance_pro(d_a5)
                analisis = obtener_analisis_ia(texto_excel, m, client)

                tab1, tab2 = st.tabs(["📋 Informe Estratégico", "🛡️ Centro de Auditoría"])

                with tab1:
                    diag_md = analisis.get('diagnostico', '')
                    st.markdown(diag_md)

                    st.write("---")
                    c_down1, c_down2 = st.columns(2)

                    with c_down1:
                        if st.button("📄 Generar Informe PDF"):
                            pdf = FPDF()
                            pdf.add_page()
                            pdf.set_font("Arial", 'B', 16)
                            pdf.cell(0, 10, "Informe Finatrix Elite v6.5", 0, 1, 'C')
                            pdf.ln(10)
                            pdf.set_font("Arial", size=11)
                            
                            # Limpieza de caracteres para PDF
                            for line in diag_md.split('\n'):
                                line_clean = line.encode('latin-1', 'replace').decode('latin-1')
                                pdf.multi_cell(0, 6, line_clean)
                            
                            pdf_output = pdf.output(dest='S').encode('latin-1')
                            st.download_button("⬇️ Descargar PDF", pdf_output, "informe_finatrix.pdf", "application/pdf")

                    with c_down2:
                        if st.button("📝 Descargar Word"):
                            doc = Document()
                            doc.add_heading('Informe de Consultoría Finatrix Elite', 0)
                            for line in diag_md.split('\n'):
                                doc.add_paragraph(line)
                            doc_io = io.BytesIO()
                            doc.save(doc_io)
                            doc_io.seek(0)
                            st.download_button("⬇️ Obtener Word", doc_io.getvalue(), "informe.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

                with tab2:
                    st.metric("Score de Calidad", f"{analisis.get('score', 0)}/100")
                    st.write(f"**Validación:** {status_bal}")
                    if m['incoherencia']: st.error("🚨 Inconsistencia detectada: EBITDA > Ventas.")
                    st.write("### Trazabilidad de Números")
                    st.json(m)

                # --- SIMULADOR ---
                st.write("---")
                with st.expander("🎮 Simulador de Escenarios (CFO Dashboard)"):
                    sc1, sc2, sc3 = st.columns(3)
                    v_s = sc1.number_input("Ventas Proyectadas", value=float(d_a5.get('ventas') or 0))
                    e_s = sc2.number_input("EBITDA Proyectado", value=float(d_a5.get('ebitda') or 0))
                    w_s = sc3.number_input("WACC (%)", value=float((d_a5.get('wacc') or 0.12)*100)) / 100

                    if st.button("📊 Recalcular Valor", disabled=d_a5.get('activos_totales') is None):
                        u_base = d_a5.get('uodi')
                        u_sim = u_base if u_base is not None else e_s * 0.7
                        cap = d_a5.get('activos_totales') or 1
                        eva_sim = u_sim - (cap * w_s)

                        rc1, rc2, rc3 = st.columns(3)
                        rc1.metric("Nuevo Margen EBITDA", safe_format(safe_div(e_s, v_s), 'pct'))
                        rc2.metric("Nuevo EVA", safe_format(eva_sim), delta=safe_format(eva_sim - (m['eva'] or 0)))
                        rc3.write("✅ Generación de Valor" if eva_sim > 0 else "❌ Destrucción de Valor")

        except Exception as e:
            st.error(f"Falla crítica: {e}")
