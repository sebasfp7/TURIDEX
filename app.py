import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import requests
import json
import pdfplumber

# ==================== 1. MOTOR DE INTELIGENCIA (EL CEREBRO) ====================

def motor_groq(key, prompt):
    client = Groq(api_key=key)
    res = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user", "content":prompt}],
        response_format={"type":"json_object"}
    )
    return json.loads(res.choices[0].message.content)

def motor_gemini(key, prompt):
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
    res = model.generate_content(prompt)
    return json.loads(res.text)

def motor_openrouter(key, prompt):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        data=json.dumps({
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        })
    )
    return json.loads(response.json()['choices'][0]['message']['content'])

def motor_together(key, prompt):
    client = Groq(api_key=key, base_url="https://api.together.xyz/v1")
    res = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        messages=[{"role":"user", "content":prompt}],
        response_format={"type":"json_object"}
    )
    return json.loads(res.choices[0].message.content)

# ==================== 2. INTERFAZ Y LÓGICA FINAL ====================
st.set_page_config(page_title="Finatrix Elite v9.5", layout="wide")

st.markdown("""
    <style>
    .pilar-card { padding: 15px; border-radius: 8px; border-top: 4px solid #2563eb; background-color: #f8fafc; margin-bottom: 10px; border: 1px solid #e2e8f0; }
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Finatrix Elite | CFO Virtual")

archivo = st.file_uploader("Subir Estados Financieros", type=["pdf", "xlsx"])

if archivo and st.button("🚀 Iniciar Gran Auditoría"):
    with st.spinner("Leyendo y auditando datos..."):
        try:
            with pdfplumber.open(archivo) as pdf:
                raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])[:15000]
        except:
            st.error("Error al leer el archivo.")
            st.stop()

    # EL PROMPT QUE RECUPERA TODO
    prompt_maestro = f"""Eres un CFO Senior y Socio de Big4. Analiza este contenido: {raw_text}
    Devuelve ÚNICAMENTE un JSON con esta estructura exacta:
    {{
      "m": {{ "cagr": 0, "ebitda_m": 0, "liquidez": 0, "eva": 0, "wacc": 0, "score": 0 }},
      "resumen_ejecutivo": "2 párrafos de análisis profundo.",
      "diagnostico_pilares": {{ 
        "rentabilidad": "Análisis detallado.", 
        "liquidez": "Análisis detallado.", 
        "solvencia": "Análisis detallado.", 
        "creacion_valor": "Análisis de EVA brutalmente honesto." 
      }},
      "semaforo": {{ "verde": ["3 fortalezas"], "amarillo": ["2 alertas"], "rojo": ["2 peligros"] }},
      "plan_90_dias": {{ "t30": "Acciones urgentes", "t60": "Acciones tácticas", "t90": "Acción estratégica" }}
    }}"""

    analisis_exitoso = False
    data = None
    motores = [
        ("Groq", st.secrets.get("GROQ_KEY"), motor_groq),
        ("Gemini", st.secrets.get("GEMINI_KEY"), motor_gemini),
        ("OpenRouter", st.secrets.get("OPENROUTER_KEY"), motor_openrouter),
        ("Together", st.secrets.get("TOGETHER_KEY"), motor_together)
    ]

    for nombre, key, funcion in motores:
        if key and not analisis_exitoso:
            try:
                with st.spinner(f"Solicitando informe a {nombre}..."):
                    data = funcion(key, prompt_maestro)
                    analisis_exitoso = True
                    st.success(f"✅ Informe generado por {nombre}")
            except:
                st.warning(f"⚠️ {nombre} saturado...")

    if analisis_exitoso and data:
        # --- RENDERIZADO DEL INFORME COMPLETO ---
        m = data.get('m', {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Salud Estratégica", f"{m.get('score', 0)}/100")
        c2.metric("EVA", f"${m.get('eva', 0):,.0f}")
        c3.metric("WACC", f"{m.get('wacc', 0):.2%}")

        st.write("---")
        st.subheader("📋 Resumen Ejecutivo")
        st.info(data.get('resumen_ejecutivo', ''))

        st.write("---")
        st.subheader("🔬 Diagnóstico por Pilares")
        diag = data.get('diagnostico_pilares', {})
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f'<div class="pilar-card"><strong>📈 Rentabilidad:</strong><br>{diag.get("rentabilidad")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="pilar-card"><strong>💧 Liquidez:</strong><br>{diag.get("liquidez")}</div>', unsafe_allow_html=True)
        with col_p2:
            st.markdown(f'<div class="pilar-card"><strong>🏗️ Solvencia:</strong><br>{diag.get("solvencia")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="pilar-card"><strong>💎 Creación de Valor:</strong><br>{diag.get("creacion_valor")}</div>', unsafe_allow_html=True)

        st.write("---")
        st.subheader("🚦 Semáforo Directivo")
        sem = data.get('semaforo', {})
        cs1, cs2, cs3 = st.columns(3)
        cs1.success("**VERDE**\n\n" + "\n".join([f"• {x}" for x in sem.get('verde', [])]))
        cs2.warning("**AMARILLO**\n\n" + "\n".join([f"• {x}" for x in sem.get('amarillo', [])]))
        cs3.error("**ROJO**\n\n" + "\n".join([f"• {x}" for x in sem.get('rojo', [])]))

        st.write("---")
        st.subheader("🎯 Plan de Acción 90 Días")
        plan = data.get('plan_90_dias', {})
        t1, t2, t3 = st.tabs(["30 Días", "60 Días", "90 Días"])
        t1.markdown(plan.get('t30', ''))
        t2.markdown(plan.get('t60', ''))
        t3.markdown(plan.get('t90', ''))
