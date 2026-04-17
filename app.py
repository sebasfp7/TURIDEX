import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go
import hashlib

# ==================== CONFIGURACIÓN Y ESTILO ====================
st.set_page_config(page_title="Finatrix Elite Auditor v4.2", layout="wide")

# ==================== NÚCLEO DE CÁLCULO SEGURO ====================
def safe_div(n, d):
    if n is None or d is None or d == 0:
        return None
    return n / d

def calcular_cagr(v_ini, v_fin, periodos=4):
    if v_ini is None or v_fin is None or v_ini <= 0:
        return None
    # Protegemos contra crecimientos negativos (pérdidas)
    if v_fin <= 0: return -1.0 
    return (v_fin / v_ini) ** (1 / periodos) - 1

def validar_balance_elite(d):
    act, pas, pat = d.get('activos_totales'), d.get('pasivos_totales'), d.get('patrimonio')
    if not all([act, pas, pat]) or act <= 0:
        return "❌ Datos de balance inválidos o incompletos para el Año 5."
    
    diff = abs(act - (pas + pat))
    if diff > act * 0.01:
        porcentaje_error = (diff / act) * 100
        return f"❌ Balance descuadrado: Dif. ${diff:,.0f} ({porcentaje_error:.2f}% del Activo)."
    return None

# ==================== MOTOR DE INSIGHTS JERARQUIZADOS ====================
def generar_analisis_consultoria(d_a1, d_a5):
    criticos, importantes, info = [], [], []
    
    # 1. Análisis de Crecimiento y Drivers
    cagr = calcular_cagr(d_a1.get('ventas'), d_a5.get('ventas'))
    m_ebitda = safe_div(d_a5.get('ebitda'), d_a5.get('ventas'))
    
    if cagr is not None and cagr > 0.20:
        if m_ebitda is not None and m_ebitda < 0.10:
            criticos.append("🔥 Crecimiento Peligroso: Ventas suben >20% pero margen EBITDA es <10%. Riesgo de insolvencia operativa.")
        else:
            importantes.append("🚀 Crecimiento Sostenible: Expansión fuerte con márgenes saludables.")
    
    # 2. Análisis de Riesgo Operativo (GAO + Punto Equilibrio)
    gao = d_a5.get('gao')
    pe_ratio = safe_div(d_a5.get('ventas'), d_a5.get('punto_equilibrio_año5'))
    
    if gao is not None and gao > 4:
        if pe_ratio is not None and pe_ratio < 1.2:
            criticos.append("⚠️ Vulnerabilidad Extrema: Alto GAO y ventas peligrosamente cerca del Punto de Equilibrio.")
        else:
            importantes.append("🟡 Apalancamiento Alto: Sensibilidad elevada a cambios en ventas.")

    # 3. Creación de Valor (EVA vs WACC)
    eva = d_a5.get('eva')
    if eva is not None:
        if eva < 0:
            criticos.append("❌ Destrucción de Valor: El EVA es negativo. La rentabilidad no cubre el costo de capital.")
        else:
            info.append("🟢 Generación de Valor: La empresa supera su costo de oportunidad.")

    # 4. Eficiencia y Rotación
    rotacion = safe_div(d_a5.get('ventas'), d_a5.get('activos_totales'))
    if rotacion is not None and rotacion < 0.6:
        importantes.append(f"⚠️ Baja Eficiencia de Activos: Rotación de {rotacion:.2f}x. Se requiere revisar activos ociosos.")

    # 5. Detección de Incoherencias
    if d_a5.get('ebitda') and d_a5.get('uodi'):
        if d_a5['uodi'] > d_a5['ebitda']:
            criticos.append("❌ Incoherencia Contable: UODI mayor que el EBITDA detectado.")

    return criticos, importantes, info

# ==================== EXTRACCIÓN ROBUSTA ====================
def extraer_datos_excel(archivo):
    xls = pd.ExcelFile(archivo)
    texto_contexto = ""
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet).fillna('').head(40)
        # Usamos markdown para que la IA entienda perfectamente las columnas
        texto_contexto += f"\n### HOJA: {sheet} ###\n{df.to_markdown(index=False)}\n"
    return texto_contexto[:26000]

# ==================== UI STREAMLIT ====================
st.sidebar.header("⚙️ Configuración Pro")
api_key = st.sidebar.text_input("Groq API Key", type="password")
archivo = st.sidebar.file_uploader("Subir Plantilla Finatrix", type=["xlsx"])

if archivo and api_key:
    client = Groq(api_key=api_key)
    
    if st.button("🚀 Ejecutar Auditoría Elite"):
        with st.spinner("Procesando ADN financiero..."):
            texto_excel = extraer_datos_excel(archivo)
            
            prompt = f"""
            Eres un Socio de Consultoría Financiera. Extrae los datos para el Año 1 y Año 5.
            Si un dato no existe, usa null. 
            MAPEO: 'uodi' es Utilidad Operativa Después de Impuestos en hoja WACC-EVA.
            
            Devuelve SOLO JSON:
            {{
              "año1": {{"ventas": num, "ebitda": num, "gao": num}},
              "año5": {{
                "ventas": num, "ebitda": num, "uodi": num, 
                "activos_totales": num, "pasivos_totales": num, "patrimonio": num,
                "punto_equilibrio_año5": num, "eva": num, "wacc": num, "gao": num
              }}
            }}
            DATOS: {texto_excel}
            """
            
            try:
                chat_completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                datos = json.loads(chat_completion.choices[0].message.content)
                
                # --- PROCESAMIENTO ---
                d1, d5 = datos['año1'], datos['año5']
                
                # Índice de confianza
                campos_totales = len(d1) + len(d5)
                validos = sum(1 for v in {**d1, **d5}.values() if v is not None)
                confianza = validos / campos_totales
                
                # --- DASHBOARD ---
                st.metric("Índice de Confianza del Análisis", f"{confianza:.0%}")
                
                error_bal = validar_balance_elite(d5)
                if error_bal:
                    st.error(error_bal)
                    if "❌" in error_bal: st.stop()

                # Visualización
                c1, c2 = st.columns([2, 1])
                with c1:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name='Año 1', x=['Ventas', 'EBITDA'], y=[d1.get('ventas') or 0, d1.get('ebitda') or 0]))
                    fig.add_trace(go.Bar(name='Año 5', x=['Ventas', 'EBITDA'], y=[d5.get('ventas') or 0, d5.get('ebitda') or 0]))
                    st.plotly_chart(fig, use_container_width=True)
                
                with c2:
                    st.subheader("Perfil de Empresa")
                    if confianza < 0.7: st.warning("Datos incompletos")
                    elif d5.get('eva', 0) > 0: st.success("Generadora de Valor")
                    else: st.error("Estructura de Riesgo")

                # Insights Jerarquizados
                crit, imp, inf = generar_analisis_consultoria(d1, d5)
                
                t1, t2, t3 = st.tabs(["🔴 Críticos", "🟡 Importantes", "🔵 Informativos"])
                with t1: 
                    for c in crit: st.error(c)
                with t2:
                    for i in imp: st.warning(i)
                with t3:
                    for f in inf: st.info(f)

            except Exception as e:
                st.error(f"Error en el motor: {e}")

else:
    st.info("Configura la API Key y sube el archivo para comenzar.")
