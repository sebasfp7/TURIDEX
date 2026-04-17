import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go
import io
from xhtml2pdf import pisa
from docx import Document # Nueva librería para Word

# ==================== 1. MOTOR FINANCIERO Y FORMATEO ====================
st.set_page_config(page_title="Finatrix Elite v6.3", layout="wide")

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
        return texto[:26000] + "\n[TRUNCADO]"
    return texto

def obtener_analisis_ia(contexto, m, client):
    c_txt, e_txt = safe_format(m['cagr'], 'pct'), safe_format(m['m_ebitda'], 'pct')
    l_txt, w_txt, ev_txt = safe_format(m['liquidez'], 'x'), safe_format(m['wacc'], 'pct'), safe_format(m['eva'])
    
    prompt = f"""Eres Senior Partner. Analiza: CAGR: {c_txt}, Margen EBITDA: {e_txt}, Liquidez: {l_txt}, WACC: {w_txt}, EVA: {ev_txt}.
    Incoherencia: {"SÍ" if m['incoherencia'] else "NO"}.
    Excel: {contexto}
    RESPONDE SOLO JSON: {{ "diagnostico": "markdown...", "score": 0-100 }}"""
    res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user", "content":prompt}], response_format={"type":"json_object"})
    return json.loads(res.choices[0].message.content)

# ==================== 3. INTERFAZ ====================
st.sidebar.header("⚙️ Finatrix Elite v6.3")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Simulación Excel", type=["xlsx"])

if not api_key:
    st.info("🔑 Ingresa tu API Key.")
elif archivo:
    client = Groq(api_key=api_key)
    if st.button("🚀 Iniciar Auditoría"):
        try:
            texto_excel = extraer_datos_excel(archivo)
            extract_prompt = """Extrae SOLO JSON: {"año1": {"ventas":num,"ebitda":num,"activos_corrientes":num,"pasivos_corrientes":num}, 
            "año5": {"ventas":num,"ebitda":num,"activos_totales":num,"pasivos_totales":num,"patrimonio":num,
            "activos_corrientes":num,"pasivos_corrientes":num,"eva":num,"wacc":num,"uodi":num}}"""
            
            res_raw = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role":"user", "content": f"{extract_prompt}\n{texto_excel}"}], response_format={"type":"json_object"})
            d = json.loads(res_raw.choices[0].message.content)
            
            d_a1, d_a5 = d.get('año1', {}), d.get('año5', {})
            m = calcular_metricas_python(d_a1, d_a5)
            status_bal = validar_balance_pro(d_a5)
            analisis = obtener_analisis_ia(texto_excel, m, client)
            
            t1, t2 = st.tabs(["📋 Informe", "🛡️ Auditoría"])
            
            with t1:
                diag_text = analisis.get('diagnostico', '')
                st.markdown(diag_text)
                
                col_down1, col_down2 = st.columns(2)
                
                # --- EXPORTAR PDF ---
                with col_down1:
                    if st.button("📄 Exportar a PDF"):
                        html_pdf = f"<html><body><h1>Informe Finatrix</h1><hr>{diag_text.replace('\n', '<br>')}</body></html>"
                        pdf_io = io.BytesIO()
                        pisa.CreatePDF(io.StringIO(html_pdf), dest=pdf_io)
                        st.download_button("⬇️ Descargar PDF", pdf_io.getvalue(), "informe.pdf", "application/pdf")
                
                # --- EXPORTAR WORD ---
                with col_down2:
                    if st.button("📝 Exportar a Word"):
                        doc = Document()
                        doc.add_heading('Informe Ejecutivo Finatrix Elite', 0)
                        doc.add_paragraph(diag_text)
                        doc_io = io.BytesIO()
                        doc.save(doc_io)
                        doc_io.seek(0)
                        st.download_button("⬇️ Descargar Word", doc_io.getvalue(), "informe.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

            with t2:
                st.metric("Score", f"{analisis.get('score', 0)}/100")
                st.write(f"**Validación:** {status_bal}")
                st.json(m)

            # --- SIMULADOR ---
            st.write("---")
            with st.expander("🎮 Simulador"):
                v_sim = st.number_input("Ventas", value=float(d_a5.get('ventas') or 0))
                e_sim = st.number_input("EBITDA", value=float(d_a5.get('ebitda') or 0))
                if st.button("📊 Simular"):
                    u_sim = (d_a5.get('uodi') or e_sim * 0.7)
                    eva_sim = u_sim - ((d_a5.get('activos_totales') or 0) * (d_a5.get('wacc') or 0.12))
                    st.metric("Nuevo EVA", safe_format(eva_sim))

        except Exception as e:
            st.error(f"Error: {e}")
