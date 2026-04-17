import streamlit as st
import pandas as pd
from groq import Groq
import google.generativeai as genai
import requests # Para OpenRouter y Together AI
import json
import pdfplumber
from docx import Document
import time

# ==================== 1. CONFIGURACIÓN DE UI ====================
st.set_page_config(page_title="Finatrix Fortress v8.5", layout="wide")

st.markdown("""
    <style>
    .pilar-card { padding: 15px; border-radius: 8px; border-top: 4px solid #2563eb; background-color: #f8fafc; margin-bottom: 10px; border: 1px solid #e2e8f0; }
    .stMetric { background-color: #ffffff; border: 1px solid #e1e4e8; padding: 10px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# ==================== 2. MOTORES DE IA (LA FORTALEZA) ====================

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
    # Para DeepSeek-V3
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        data=json.dumps({
            "model": "deepseek/deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        })
    )
    return response.json()['choices'][0]['message']['content']

def motor_together(key, prompt):
    # Para Llama-3.1-70B
    client = Groq(api_key=key, base_url="https://api.together.xyz/v1")
    res = client.chat.completions.create(
        model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        messages=[{"role":"user", "content":prompt}],
        response_format={"type":"json_object"}
    )
    return json.loads(res.choices[0].message.content)

# ==================== 3. INTERFAZ PRINCIPAL ====================
st.title("🛡️ Finatrix Elite | The Fortress")

with st.sidebar:
    st.header("🔑 Llaves de Acceso")
    k_groq = st.text_input("1. Groq Key (Llama 3.3)", type="password")
    k_gemini = st.text_input("2. Gemini Key (1.5 Flash)", type="password")
    k_open = st.text_input("3. OpenRouter Key (DeepSeek)", type="password")
    k_together = st.text_input("4. Together Key (Llama 3.1)", type="password")
    st.caption("La app intentará los motores en orden si uno falla.")

archivo = st.file_uploader("Subir Estados Financieros", type=["xlsx", "pdf", "docx"])

if archivo and st.button("🚀 Iniciar Auditoría Global"):
    # Lógica de lectura simplificada para ahorrar espacio
    with pdfplumber.open(archivo) as pdf:
        raw_text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])[:15000]

    prompt_maestro = f"""Eres un CFO Senior. Analiza: {raw_text}. 
    Devuelve SOLO JSON con campos: score, resumen_ejecutivo, diagnostico_pilares (rentabilidad, liquidez, solvencia, creacion_valor), semaforo (verde, amarillo, rojo), plan_90_dias (t30, t60, t90), m (eva, wacc, score)."""

    analisis_exitoso = False
    data = None
    
    # --- CASCADA DE MOTORES ---
    motores = [
        ("Groq", k_groq, motor_groq),
        ("Gemini", k_gemini, motor_gemini),
        ("OpenRouter", k_open, motor_openrouter),
        ("Together", k_together, motor_together)
    ]

    for nombre, key, funcion in motores:
        if key and not analisis_exitoso:
            try:
                with st.spinner(f"Consultando Motor {nombre}..."):
                    data = funcion(key, prompt_maestro)
                    if isinstance(data, str): data = json.loads(data)
                    analisis_exitoso = True
                    st.success(f"✅ Análisis completado por {nombre}")
            except:
                st.warning(f"⚠️ Motor {nombre} saturado. Saltando...")

    if analisis_exitoso and data:
        # Aquí renderizamos los resultados (igual que la v8.0)
        st.write("---")
        m = data.get('m', {})
        c1, c2, c3 = st.columns(3)
        c1.metric("Salud Estratégica", f"{m.get('score', 0)}/100")
        c2.metric("EVA", f"${m.get('eva', 0):,.0f}")
        c3.metric("WACC", f"{m.get('wacc', 0):.2%}")
        
        st.info(data.get('resumen_ejecutivo', ''))
        # ... (Resto de la visualización de pilares y semáforo)
    else:
        st.error("❌ Fallo total: Todos los motores están fuera de servicio o no tienen llaves válidas.")
