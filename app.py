import streamlit as st
import pandas as pd
from groq import Groq
import json
import plotly.graph_objects as go

# ==================== UTILIDADES DE TRANSPARENCIA ====================

def calcular_con_traza(nombre, n, d, unidad=""):
    """Realiza el cálculo y devuelve la explicación textual."""
    res = None
    if n is not None and d is not None and d != 0:
        res = n / d
        return res, f"{nombre}: {n:,.2f} / {d:,.2f} = {res:,.2f}{unidad}"
    return None, f"{nombre}: Datos insuficientes ({n} / {d})"

# ==================== PROMPT DE EXTRACCIÓN CON CITAS ====================

def obtener_prompt_transparente(texto):
    return f"""
    Eres un Auditor Forense. Tu objetivo es extraer datos y CITAR en qué hoja los encontraste.
    
    JSON REQUERIDO:
    {{
      "datos": {{
        "ventas_a5": {{"valor": num, "fuente": "Hoja X"}},
        "ebitda_a5": {{"valor": num, "fuente": "Hoja Y"}},
        "punto_equilibrio_a5": {{"valor": num, "fuente": "Hoja Z"}},
        "uodi_a5": {{"valor": num, "fuente": "Hoja W"}},
        "activos_totales": {{"valor": num, "fuente": "Hoja A"}},
        "pasivos_totales": {{"valor": num, "fuente": "Hoja B"}},
        "patrimonio": {{"valor": num, "fuente": "Hoja C"}},
        "eva": {{"valor": num, "fuente": "Hoja D"}}
      }},
      "verificacion_auditor": "Breve nota sobre si las cifras de las diferentes hojas coinciden entre sí."
    }}

    TEXTO A PROCESAR: {texto[:26000]}
    """

# ==================== MOTOR DE ANÁLISIS EXPLICATIVO ====================

def realizar_auditoria_explicada(datos_ia, client):
    d = datos_ia['datos']
    log_calculos = []
    
    # 1. Margen Operativo (UODI / Ventas)
    margen, traza = calcular_con_traza(
        "Margen Operativo", 
        d['uodi_a5']['valor'], 
        d['ventas_a5']['valor'], 
        "%"
    )
    log_calculos.append(f"• {traza} (Fuente: {d['uodi_a5']['fuente']} y {d['ventas_a5']['fuente']})")
    
    # 2. Cobertura de Punto de Equilibrio
    cobertura, traza_pe = calcular_con_traza(
        "Indice de Cobertura PE", 
        d['ventas_a5']['valor'], 
        d['punto_equilibrio_a5']['valor'], 
        "x"
    )
    log_calculos.append(f"• {traza_pe} (Fuente: {d['punto_equilibrio_a5']['fuente']})")

    # 3. Construcción del Diagnóstico con IA
    # Le pasamos los cálculos ya hechos para que la IA solo interprete la lógica
    prompt_diag = f"""
    Como Socio de Consultoría, interpreta estos cálculos realizados por el sistema:
    - {traza}
    - {traza_pe}
    - EVA reportado: {d['eva']['valor']} (Fuente: {d['eva']['fuente']})
    
    Explica al cliente:
    1. ¿Por qué el margen es bueno o malo según su sector?
    2. ¿Qué tan peligroso es estar a esa distancia del Punto de Equilibrio?
    3. Si el EVA es coherente con el resultado operativo.
    """
    
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt_diag}]
    )
    
    return res.choices[0].message.content, log_calculos

# ==================== UI DASHBOARD ====================

st.title("🛡️ Finatrix Auditor v4.5")
st.subheader("Auditoría Transparente: Citas, Fuentes y Fórmulas")

# ... (Lógica de carga de archivo y API Key) ...

if 'datos_ia' in st.session_state:
    datos = st.session_state.datos_ia
    
    tab1, tab2, tab3 = st.tabs(["📊 Informe Estratégico", "🔍 Memoria de Cálculo", "📑 Verificación de Fuentes"])
    
    with tab1:
        informe, log = realizar_auditoria_explicada(datos, client)
        st.markdown(informe)
        
    with tab2:
        st.info("Aquí puedes ver cómo el sistema llegó a cada número:")
        for linea in log:
            st.code(linea) # Usamos code para que resalte como fórmula
            
    with tab3:
        st.write("### Trazabilidad de Datos (IA Extractora)")
        df_fuentes = pd.DataFrame([
            {"Concepto": k, "Valor": v['valor'], "Fuente en Excel": v['fuente']}
            for k, v in datos['datos'].items()
        ])
        st.table(df_fuentes)
        st.success(f"Nota del Auditor: {datos['verificacion_auditor']}")
