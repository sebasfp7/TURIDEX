import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go
import pdfplumber
from docx import Document
from pptx import Presentation

# ==================== 1. CONFIGURACIÓN Y FORMATEO ====================
st.set_page_config(page_title="Finatrix Elite v7.3", layout="wide")

def safe_format(valor, tipo='num'):
    if not isinstance(valor, (int, float)): return "N/D"
    if tipo == 'pct': return f"{valor:.2%}"
    if tipo == 'x': return f"{valor:.2f}x"
    return f"${valor:,.0f}"

def safe_div(n, d):
    return n / d if d and d != 0 else None

# ==================== 2. LECTORES DE DOCUMENTOS ====================
def leer_contenido(uploaded_file):
    ext = uploaded_file.name.split('.')[-1].lower()
    text = ""
    try:
        if ext == 'xlsx':
            xls = pd.ExcelFile(uploaded_file)
            for sheet in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet).head(50)
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
        return text[:28000]
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

# ==================== 3. MOTOR DE INTELIGENCIA ESTRATÉGICA ====================
def obtener_analisis_ia(contexto, m, client):
    c_txt = safe_format(m['cagr'], 'pct')
    e_txt = safe_format(m['m_ebitda'], 'pct')
    l_txt = safe_format(m['liquidez'], 'x')
    w_txt = safe_format(m['wacc'], 'pct')
    ev_txt = safe_format(m['eva'])
    act_txt = safe_format(m['activos_totales'])

    prompt = f"""Eres un CFO Senior y Socio de Consultora Big4. Tu cliente es el dueño de la empresa.
    No seas genérico. Usa los números exactos que te doy. Si un dato es N/D, dilo y explica el riesgo de no tenerlo.

    DATOS DUROS VERIFICADOS POR EL AUDITOR:
    - Crecimiento Ventas CAGR: {c_txt}
    - Margen EBITDA Año 5: {e_txt}
    - Liquidez Corriente: {l_txt}
    - WACC: {w_txt} | EVA: {ev_txt}
    - Activos Totales: {act_txt}
    - Alerta Contable: {"EBITDA > Ventas detectado" if m['incoherencia'] else "Sin incoherencias"}

    CONTEXTO DEL DOCUMENTO: {contexto}

    TAREA: Devuelve SOLO JSON con esta estructura exacta:
    {{
      "score": 0-100,
      "resumen_ejecutivo": "...",
      "diagnostico_pilares": {{
        "rentabilidad": "...",
        "liquidez": "...",
        "solvencia": "...",
        "creacion_valor": "..."
      }},
      "hallazgos_criticos": [
        {{"tipo": "Riesgo", "titulo": "...", "impacto": "...", "evidencia": "...", "recomendacion": "..."}}
      ],
      "plan_90_dias": {{ "30_dias": "...", "60_dias": "...", "90_dias": "..." }},
      "semaforo": {{ "verde": [], "amarillo": [], "rojo": [] }}
    }}"""
    
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user", "content":prompt}],
        response_format={"type":"json_object"}
    )
    return json.loads(res.choices[0].message.content)

# ==================== 4. INTERFAZ PRINCIPAL ====================
st.title("🛡️ Finatrix Elite | CFO Strategy")
st.sidebar.header("🔑 Acceso Seguro")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Estados Financieros / Informes", type=["xlsx", "pdf", "docx", "pptx"])

if api_key and archivo:
    client = Groq(api_key=api_key)
    
    if st.button("🚀 Ejecutar Análisis de Consultoría"):
        with st.spinner("Auditando y cruzando datos financieros..."):
            raw_text = leer_contenido(archivo)
            
            # 1. Extracción Rápida de métricas base para el prompt
            extract_prompt = """Extrae solo estos números en JSON: 
            {"ventas_a1":num, "ventas_a5":num, "ebitda_a5":num, "activos_corr":num, "pasivos_corr":num, "activos_totales":num, "eva":num, "wacc":num}"""
            
            base_data = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"user", "content": f"{extract_prompt}\n{raw_text}"}],
                response_format={"type":"json_object"}
            )
            bd = json.loads(base_data.choices[0].message.content)
            
            # 2. Cálculos en Python
            m = {
                'cagr': ((bd.get('ventas_a5',0)/bd.get('ventas_a1',1))**(1/4)-1) if bd.get('ventas_a1') else None,
                'm_ebitda': safe_div(bd.get('ebitda_a5'), bd.get('ventas_a5')),
                'liquidez': safe_div(bd.get('activos_corr'), bd.get('pasivos_corr')),
                'wacc': bd.get('wacc'),
                'eva': bd.get('eva'),
                'activos_totales': bd.get('activos_totales'),
                'incoherencia': bd.get('ebitda_a5', 0) > bd.get('ventas_a5', 1)
            }
            
            # 3. Análisis Estratégico IA
            analisis = obtener_analisis_ia(raw_text, m, client)
            
            # --- RENDERIZADO DEL INFORME ---
            tab1, tab2 = st.tabs(["📊 Informe de Valor", "🔍 Auditoría Técnica"])
            
            with tab1:
                # Cabecera de Impacto
                col_s1, col_s2, col_s3 = st.columns(3)
                col_s1.metric("Salud Estratégica", f"{analisis.get('score')}/100")
                col_s2.metric("EVA", safe_format(m['eva']))
                col_s3.metric("WACC", safe_format(m['wacc'], 'pct'))

                st.subheader("📋 Resumen Ejecutivo")
                st.info(analisis.get('resumen_ejecutivo', ''))

                st.write("---")
                st.subheader("🔬 Diagnóstico por Pilares")
                diag = analisis.get('diagnostico_pilares', {})
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**📈 Rentabilidad:**\n{diag.get('rentabilidad','')}")
                    st.markdown(f"**💧 Liquidez:**\n{diag.get('liquidez','')}")
                with c2:
                    st.markdown(f"**🏗️ Solvencia:**\n{diag.get('solvencia','')}")
                    st.markdown(f"**💎 Creación de Valor:**\n{diag.get('creacion_valor','')}")

                st.write("---")
                st.subheader("🚦 Semáforo Directivo")
                sem = analisis.get('semaforo', {})
                cs1, cs2, cs3 = st.columns(3)
                cs1.success("**FORTALEZAS**\n\n" + "\n".join([f"• {x}" for x in sem.get('verde',[])]))
                cs2.warning("**ALERTAS**\n\n" + "\n".join([f"• {x}" for x in sem.get('amarillo',[])]))
                cs3.error("**CRÍTICO**\n\n" + "\n".join([f"• {x}" for x in sem.get('rojo',[])]))

                st.write("---")
                st.subheader("🎯 Plan de Acción 90 Días")
                plan = analisis.get('plan_90_dias', {})
                t30, t60, t90 = st.tabs(["Fase 1: Urgente (30 días)", "Fase 2: Táctico (60 días)", "Fase 3: Estratégico (90 días)"])
                t30.markdown(plan.get('30_dias',''))
                t60.markdown(plan.get('60_dias',''))
                t90.markdown(plan.get('90_dias',''))

            with tab2:
                st.subheader("Hallazgos Detallados")
                for h in analisis.get('hallazgos_criticos', []):
                    with st.expander(f"{h['tipo']}: {h['titulo']} ({h['impacto']})"):
                        st.write(f"**Evidencia:** {h['evidencia']}")
                        st.write(f"**Acción:** {h['recomendacion']}")
                st.write("### Datos Crudos de Auditoría")
                st.json(m)
