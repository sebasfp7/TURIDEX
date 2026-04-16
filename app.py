import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TURIDEX", layout="wide")

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; background-position: center; background-attachment: fixed;
    }
    .pokedex-frame {
        background-color: rgba(255, 255, 255, 0.95);
        border: 4px solid #DC0A2D;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }
    .pokedex-title-box {
        background-color: #000000;
        border: 4px solid #DC0A2D;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .pokedex-title { color: #FFFFFF !important; font-family: 'Courier New', monospace; font-size: 3em; margin: 0; }
    .black-text, p, h1, h2, h3, span, label, div { color: #000000 !important; font-weight: 600; }
    .data-card {
        background-color: rgba(0, 0, 0, 0.05);
        border-left: 5px solid #DC0A2D;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .evo-tag {
        background-color: #FFCC00;
        color: black !important;
        padding: 6px 14px;
        border-radius: 15px;
        font-weight: bold;
        display: inline-block;
        margin: 4px;
        border: 1px solid #000;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='pokedex-title-box'><h1 class='pokedex-title'>TURIDEX</h1></div>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Error: Configura la API KEY.")

def encode_image(image_file):
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

with st.container():
    st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
    col_img, col_info = st.columns([1, 2])
    
    with col_img:
        archivo = st.file_uploader("", type=["jpg", "png", "jpeg"])
        if archivo:
            st.image(PIL.Image.open(archivo), use_container_width=True)
            analizar = st.button("🔍 ESCANEAR OBJETIVO")

    if archivo and analizar:
        with st.spinner("Analizando..."):
            try:
                img_b64 = encode_image(archivo)
                
                # ========================================
                # 🎯 PROMPT DEFINITIVO ULTRA-ESPECÍFICO
                # ========================================
                prompt = """Eres el sistema TURIDEX. Analiza esta imagen con MÁXIMA PRECISIÓN.

🔍 PASO 1 - IDENTIFICACIÓN EXACTA:
Observa la imagen y determina QUÉ ES usando estos criterios ESTRICTOS:

📌 COMIDA - Identifica por ingredientes visuales:
   • SALCHIPAPA: Papas fritas cortadas en bastones + trozos de salchicha rosada/roja. NO tiene chips de maíz.
   • NACHOS: Chips triangulares de maíz amarillo/blanco con queso derretido. NO tiene papas ni salchichas.
   • PIZZA: Masa circular con salsa roja, queso y toppings.
   • HAMBURGUESA: Pan con carne entre dos mitades.
   • CEVICHE: Pescado crudo con limón, cebolla y ají.

📌 ANIMAL - Identifica por características biológicas:
   • LEÓN: Melena grande, felino grande, color dorado.
   • PERRO: Doméstico, orejas caídas/paradas, cola.
   • ÁGUILA: Ave rapaz, pico curvo, alas grandes.
   • SERPIENTE: Reptil sin patas, cuerpo largo.

📌 LUGAR - Identifica por arquitectura/geografía:
   • MACHU PICCHU: Ruinas incas en montañas.
   • TORRE EIFFEL: Estructura metálica en París.
   • GRAN CAÑÓN: Formación rocosa con estratos.

🎯 PASO 2 - CLASIFICACIÓN Y STATS:
Una vez identificado, asigna la CATEGORÍA y valores según esta TABLA OBLIGATORIA:

┌─────────────────────────────────────────────────────────────┐
│ SI ES COMIDA → CATEGORIA: COMIDA                            │
├─────────────────────────────────────────────────────────────┤
│ STATS (0-100):                                              │
│ • Sabor: Qué tan delicioso es (popular = alto)             │
│ • Picante: Nivel de ají/chile (sin picante = 0)            │
│ • Salud: Valor nutricional (frito/chatarra = 5-15)         │
│ • Rareza: Qué tan único/difícil de encontrar               │
│                                                             │
│ EVOS: SOLO otras comidas similares                         │
│ Ejemplos válidos: Salchipapa → [Papas fritas, Hot dog, Choripán] │
│ ❌ PROHIBIDO: Incluir animales o lugares                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ SI ES ANIMAL → CATEGORIA: ANIMAL                            │
├─────────────────────────────────────────────────────────────┤
│ STATS (0-100):                                              │
│ • Fuerza: Poder físico/capacidad de carga                  │
│ • Agilidad: Velocidad y reflejos                           │
│ • Peligro: Amenaza para humanos                            │
│ • Rareza: Estado de conservación (extinto = 100)           │
│                                                             │
│ EVOS: SOLO animales de la misma familia/orden              │
│ Ejemplos válidos: León → [Tigre, Jaguar, Leopardo]        │
│ ❌ PROHIBIDO: Incluir comidas o lugares                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ SI ES LUGAR → CATEGORIA: LUGAR                              │
├─────────────────────────────────────────────────────────────┤
│ STATS (0-100):                                              │
│ • Historia: Antigüedad y relevancia histórica              │
│ • Belleza: Atractivo visual/turístico                      │
│ • Cultura: Importancia cultural/religiosa                  │
│ • Rareza: Exclusividad/dificultad de acceso                │
│                                                             │
│ EVOS: SOLO lugares similares geográfica o culturalmente    │
│ Ejemplos válidos: Machu Picchu → [Chichén Itzá, Petra, Angkor Wat] │
│ ❌ PROHIBIDO: Incluir comidas o animales                   │
└─────────────────────────────────────────────────────────────┘

📋 FORMATO DE RESPUESTA OBLIGATORIO (copia exactamente esta estructura):

NOMBRE: [Nombre exacto del elemento identificado]
CATEGORIA: [Escribe COMIDA, ANIMAL o LUGAR]
DESC: [Una frase de máximo 20 palabras describiendo qué es]
HISTORIA: [Escribe exactamente 2 párrafos: párrafo 1 sobre origen/historia, párrafo 2 sobre importancia actual o datos curiosos. Cada párrafo debe tener 3-4 oraciones completas]
STATS: [Número1, Número2, Número3, Número4]
EVOS: [Variante1, Variante2, Variante3]

⚠️ REGLAS CRÍTICAS:
1. NO repitas ninguna sección
2. NO incluyas asteriscos, hashtags ni símbolos especiales
3. Los números en STATS deben estar entre 0-100
4. Las EVOS deben ser EXACTAMENTE 3 elementos del MISMO tipo
5. Si la imagen es borrosa, usa tu mejor criterio pero mantén el formato
6. NUNCA mezcles categorías en EVOS

Analiza la imagen ahora y responde:"""

                # ========================================
                # Llamada a la IA
                # ========================================
                chat = client.chat.completions.create(
                    messages=[{
                        "role": "user", 
                        "content": [
                            {"type": "text", "text": prompt}, 
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]
                    }],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    temperature=0.05,  # Muy baja para máxima consistencia
                    max_tokens=1000
                )
                
                res = chat.choices[0].message.content

                # ========================================
                # Extracción con limpieza avanzada
                # ========================================
                def extraer(tag, texto):
                    # Busca el tag y extrae hasta el siguiente tag o fin de texto
                    patron = rf"{tag}:\s*\**(.*?)(?=\n(?:NOMBRE|CATEGORIA|DESC|HISTORIA|STATS|EVOS):|$)"
                    match = re.search(patron, texto, re.S | re.I)
                    if match:
                        contenido = match.group(1).strip()
                        # Limpia asteriscos y símbolos
                        contenido = re.sub(r'[*#_\[\]]', '', contenido)
                        return contenido
                    return "Dato no disponible"

                nombre = extraer("NOMBRE", res)
                cat = extraer("CATEGORIA", res).upper()
                desc = extraer("DESC", res)
                historia = extraer("HISTORIA", res)
                stats_raw = extraer("STATS", res)
                evos_raw = extraer("EVOS", res)
                
                # Extrae números de stats
                nums = [int(n) for n in re.findall(r'\d+', stats_raw)][:4]
                while len(nums) < 4: 
                    nums.append(0)

                # Limita valores a 0-100
                nums = [min(100, max(0, n)) for n in nums]

                # ========================================
                # Renderizado ÚNICO de información
                # ========================================
                with col_info:
                    # Título
                    st.markdown(f"## 📋 {nombre}")
                    
                    # Categoría y descripción
                    st.markdown(f"<div class='data-card'><p><b>CATEGORÍA:</b> {cat}</p><p>{desc}</p></div>", unsafe_allow_html=True)
                    
                    # Historia
                    st.markdown("### 📖 Historia")
                    st.markdown(f"<p style='color:black;'>{historia}</p>", unsafe_allow_html=True)
                    
                    # Determinar etiquetas según categoría
                    if "ANIMAL" in cat:
                        labels = ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"]
                    elif "LUGAR" in cat:
                        labels = ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
                    else:  # COMIDA
                        labels = ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"]

                    # Stats con barras
                    st.markdown("### 📊 Puntos Base")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"<p>{labels[0]}: {nums[0]}%</p>", unsafe_allow_html=True)
                        st.progress(nums[0]/100)
                        st.markdown(f"<p>{labels[1]}: {nums[1]}%</p>", unsafe_allow_html=True)
                        st.progress(nums[1]/100)
                    with c2:
                        st.markdown(f"<p>{labels[2]}: {nums[2]}%</p>", unsafe_allow_html=True)
                        st.progress(nums[2]/100)
                        st.markdown(f"<p>{labels[3]}: {nums[3]}%</p>", unsafe_allow_html=True)
                        st.progress(nums[3]/100)

                    # Variantes
                    st.markdown("### 🔄 Variantes Registradas")
                    evos_lista = [e.strip() for e in evos_raw.split(",") if e.strip() and len(e.strip()) > 2]
                    for evo in evos_lista[:3]:  # Máximo 3
                        st.markdown(f"<span class='evo-tag'>{evo}</span>", unsafe_allow_html=True)

                # Audio
                texto_audio = f"{nombre}. {desc}. {historia[:200]}"
                texto_audio = re.sub(r'[*#_\[\]]', '', texto_audio)
                tts = gTTS(text=texto_audio, lang='es')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)

            except Exception as e:
                st.error(f"⚠️ Error en el análisis: {str(e)}")
                
    st.markdown("</div>", unsafe_allow_html=True)
