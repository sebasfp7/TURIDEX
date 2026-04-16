import streamlit as st
from groq import Groq
import PIL.Image
import base64
from gtts import gTTS
import io
import re
import requests
from io import BytesIO

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="TURIDEX", layout="wide")

# --- INICIALIZACIÓN DE SESSION STATE (DESACOPLADO) ---
if 'objetivo_actual' not in st.session_state:
    st.session_state.objetivo_actual = None
if 'tipo_entrada' not in st.session_state:
    st.session_state.tipo_entrada = None  # 'imagen' o 'texto'
if 'historial_ruta' not in st.session_state:
    st.session_state.historial_ruta = []
if 'categoria_heredada' not in st.session_state:
    st.session_state.categoria_heredada = None
if 'datos_cache' not in st.session_state:
    st.session_state.datos_cache = {}
if 'imagen_generada' not in st.session_state:
    st.session_state.imagen_generada = None

st.markdown("""
<style>
    .stApp {
        background-image: url('https://vignette.wikia.nocookie.net/es.pokemon/images/c/c1/Mapa_de_Kanto_GSC.png/revision/latest?cb=20191215132219');
        background-size: cover; 
        background-position: center; 
        background-attachment: fixed;
    }
    
    /* CONTENEDOR PRINCIPAL CON EFECTO GLASSMORPHISM */
    .pokedex-frame {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 4px solid #DC0A2D;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }
    
    /* HEADER UNIFICADO CON FLEXBOX */
    .pokedex-title-box {
        background-color: #000000;
        border: 4px solid #DC0A2D;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .pokedex-title { 
        color: #FFDE00 !important; 
        font-family: 'Courier New', monospace; 
        font-size: 3.5em; 
        margin: 0;
        text-shadow: 0 0 10px #FFDE00,
                     0 0 20px #FFDE00,
                     0 0 30px #FF0000,
                     3px 3px 0px #DC0A2D;
        letter-spacing: 8px;
        animation: glow 2s ease-in-out infinite alternate;
        text-align: center;
    }
    
    @keyframes glow {
        from { 
            text-shadow: 0 0 10px #FFDE00, 0 0 20px #FFDE00, 0 0 30px #FF0000; 
        }
        to { 
            text-shadow: 0 0 20px #FFDE00, 0 0 30px #FFDE00, 0 0 50px #FF0000, 0 0 60px #FF0000; 
        }
    }
    
    /* BARRA DE RUTA CON GLASSMORPHISM */
    .breadcrumb-box {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border: 3px solid #DC0A2D;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        text-align: center;
        font-family: 'Courier New', monospace;
        font-size: 1.2em;
        color: #000000;
        font-weight: bold;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    
    .breadcrumb-arrow {
        color: #DC0A2D;
        margin: 0 10px;
        font-size: 1.3em;
    }
    
    /* INDICADOR DE ESTADO */
    .status-indicator {
        background: rgba(0, 0, 0, 0.9);
        backdrop-filter: blur(5px);
        color: #00FF00;
        padding: 12px 20px;
        border-radius: 8px;
        text-align: center;
        font-family: 'Courier New', monospace;
        font-size: 1.1em;
        margin-bottom: 20px;
        border: 3px solid #00FF00;
        animation: pulse 1.5s ease-in-out infinite;
        box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* TEXTO CON MÁXIMA LEGIBILIDAD (GLASSMORPHISM) */
    .black-text, p, h1, h2, h3, span, label, div { 
        color: #000000 !important; 
        font-weight: 600;
    }
    
    .data-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-left: 6px solid #DC0A2D;
        padding: 18px;
        border-radius: 8px;
        margin: 12px 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
    }
    
    .historia-box {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        padding: 18px;
        border-radius: 8px;
        margin: 12px 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
        line-height: 1.6;
    }
    
    /* BOTONES INTERACTIVOS DE VARIANTES (BIDIRECCIONALES) */
    .variante-container {
        margin: 8px 0;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #FFCC00 0%, #FFD700 100%) !important;
        color: #000000 !important;
        padding: 15px 25px !important;
        border-radius: 18px !important;
        font-weight: bold !important;
        border: 3px solid #000 !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3) !important;
        width: 100% !important;
        margin: 8px 0 !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        font-size: 1.2em !important;
        cursor: pointer !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
        transform: translateY(-5px) scale(1.02) !important;
        box-shadow: 0 8px 20px rgba(220, 10, 45, 0.5) !important;
        border: 3px solid #DC0A2D !important;
    }
    
    .stButton > button:active {
        transform: translateY(-2px) scale(0.98) !important;
        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.4) !important;
    }
    
    /* IMAGEN GENERADA CON BORDE */
    .imagen-generada {
        border: 4px solid #DC0A2D;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
        margin: 10px 0;
    }
    
    /* VALIDACIÓN VISUAL DE CATEGORÍA */
    .categoria-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        margin: 5px;
        border: 2px solid #000;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.3);
    }
    
    .badge-comida { background: linear-gradient(135deg, #FF6B6B, #FF8E53); color: white; }
    .badge-animal { background: linear-gradient(135deg, #4ECDC4, #44A08D); color: white; }
    .badge-lugar { background: linear-gradient(135deg, #A770EF, #CF8BF3); color: white; }
</style>
""", unsafe_allow_html=True)

# HEADER CON FLEXBOX CENTRADO
st.markdown("<div class='pokedex-title-box'><h1 class='pokedex-title'>⚡ TURIDEX ⚡</h1></div>", unsafe_allow_html=True)

# BARRA DE RUTA
if st.session_state.historial_ruta:
    ruta_html = " <span class='breadcrumb-arrow'>→</span> ".join(st.session_state.historial_ruta)
    st.markdown(f"<div class='breadcrumb-box'>📍 {ruta_html}</div>", unsafe_allow_html=True)

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("⚠️ Error: Configura GROQ_API_KEY en secrets")

def encode_image(image_file):
    """Codifica imagen a base64"""
    return base64.b64encode(image_file.getvalue()).decode('utf-8')

def sanitizar_texto(texto):
    """Limpieza profunda de texto"""
    texto = re.sub(r'[*#_\[\]]', '', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()

def extraer_dato(tag, texto):
    """Extracción con Chain-of-Thought: primera aparición única"""
    patron = rf"{tag}:\s*(.*?)(?=\n(?:NOMBRE|CATEGORIA|DESC|HISTORIA|STATS|EVOS):|$)"
    matches = re.findall(patron, texto, re.S | re.I)
    
    if matches:
        contenido = matches[0].strip()
        return sanitizar_texto(contenido)
    return "No disponible"

def generar_imagen_ia(nombre_elemento, categoria):
    """
    Genera imagen usando API de generación (Pollinations.ai - gratuita)
    Puedes reemplazar con DALL-E, Flux, etc.
    """
    try:
        # Determinar estilo según categoría
        estilos = {
            'COMIDA': 'fotografía profesional de comida, alta calidad, fondo neutro, iluminación de estudio',
            'ANIMAL': 'fotografía de National Geographic, animal en su hábitat, alta definición, realista',
            'LUGAR': 'fotografía arquitectónica profesional, paisaje impresionante, 4K, perspectiva amplia'
        }
        
        estilo = estilos.get(categoria, 'fotografía profesional, alta calidad')
        prompt_imagen = f"{nombre_elemento}, {estilo}"
        
        # API gratuita de Pollinations (sin API key necesaria)
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt_imagen)}?width=800&height=800&nologo=true"
        
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return PIL.Image.open(BytesIO(response.content))
        
        return None
        
    except Exception as e:
        st.warning(f"No se pudo generar imagen: {e}")
        return None

def consultar_ia_multimodal(objetivo, tipo_entrada, imagen_b64=None, categoria_contexto=None):
    """
    Función unificada con Chain-of-Thought
    - tipo_entrada: 'imagen' o 'texto'
    - categoria_contexto: Para heredar categoría en variantes
    """
    
    # CONSTRUCCIÓN DEL PROMPT CON CHAIN-OF-THOUGHT
    if tipo_entrada == 'imagen':
        prompt = """Eres TURIDEX. Analiza esta imagen siguiendo el proceso CHAIN-OF-THOUGHT:

PASO 1 - CLASIFICACIÓN PRIMARIA:
Identifica QUÉ ES observando características clave:
- ¿Tiene ingredientes comestibles? → COMIDA
- ¿Es un ser vivo con características animales? → ANIMAL
- ¿Es una estructura/paisaje/monumento? → LUGAR

Emite tu decisión: [CATEGORIA: ___]

PASO 2 - ANÁLISIS ESPECÍFICO:
Basándote en la categoría, extrae información relevante.

PASO 3 - ASIGNACIÓN DE STATS:
Según la categoría detectada, asigna valores 0-100:

SI ES COMIDA:
- Sabor: popularidad y gusto general
- Picante: nivel de ají/especias (0 si no tiene)
- Salud: valor nutricional (frito/chatarra = 5-15)
- Rareza: dificultad de conseguir

SI ES ANIMAL:
- Fuerza: poder físico
- Agilidad: velocidad y reflejos
- Peligro: amenaza para humanos
- Rareza: estado de conservación

SI ES LUGAR:
- Historia: antigüedad e importancia histórica
- Belleza: atractivo visual
- Cultura: relevancia cultural
- Rareza: exclusividad

PASO 4 - VARIANTES SUSTANTIVAS:
Proporciona 3 elementos SIMILARES (mismo tipo, solo sustantivos).

FORMATO DE SALIDA:
NOMBRE: [nombre exacto]
CATEGORIA: [COMIDA/ANIMAL/LUGAR]
DESC: [máximo 15 palabras]
HISTORIA: [2 párrafos, 100-150 palabras]
STATS: [num1, num2, num3, num4]
EVOS: [Sustantivo1, Sustantivo2, Sustantivo3]

⚠️ PROHIBIDO: asteriscos, hashtags, corchetes, adjetivos en EVOS

Ejecuta el análisis AHORA:"""

        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagen_b64}"}}
            ]
        }]
    
    else:  # tipo_entrada == 'texto'
        # Heredar categoría del contexto
        categoria_forzada = categoria_contexto if categoria_contexto else "la misma categoría del elemento anterior"
        
        prompt = f"""Eres TURIDEX. Proporciona información sobre: {objetivo}

⚠️ CONTEXTO IMPORTANTE: Este elemento pertenece a la categoría {categoria_forzada}.
Debes mantener consistencia con esa categoría.

CHAIN-OF-THOUGHT:

PASO 1 - CONFIRMACIÓN DE CATEGORÍA:
Categoría asignada: {categoria_forzada}

PASO 2 - EXTRACCIÓN DE DATOS:
Investiga información real sobre "{objetivo}".

PASO 3 - STATS SEGÚN CATEGORÍA:
{"- Sabor, Picante, Salud, Rareza" if "COMIDA" in str(categoria_forzada) else ""}
{"- Fuerza, Agilidad, Peligro, Rareza" if "ANIMAL" in str(categoria_forzada) else ""}
{"- Historia, Belleza, Cultura, Rareza" if "LUGAR" in str(categoria_forzada) else ""}

PASO 4 - VARIANTES DEL MISMO TIPO:
Proporciona 3 sustantivos similares a "{objetivo}".

FORMATO DE SALIDA:
NOMBRE: {objetivo}
CATEGORIA: {categoria_forzada}
DESC: [máximo 15 palabras]
HISTORIA: [2 párrafos reales, 100-150 palabras]
STATS: [num1, num2, num3, num4]
EVOS: [Sustantivo1, Sustantivo2, Sustantivo3]

⚠️ PROHIBIDO: *, #, [], adjetivos en EVOS

Responde AHORA:"""

        messages = [{"role": "user", "content": prompt}]
    
    # LLAMADA A LA IA
    chat = client.chat.completions.create(
        messages=messages,
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0.05,
        max_tokens=1500
    )
    
    return chat.choices[0].message.content

def procesar_respuesta(respuesta_ia):
    """Procesamiento con validación de esquema"""
    
    nombre = extraer_dato("NOMBRE", respuesta_ia)
    categoria = extraer_dato("CATEGORIA", respuesta_ia).upper()
    
    # VALIDACIÓN: forzar categoría válida
    if categoria not in ['COMIDA', 'ANIMAL', 'LUGAR']:
        # Inferir por palabras clave
        if any(word in respuesta_ia.lower() for word in ['sabor', 'receta', 'ingrediente', 'plato']):
            categoria = 'COMIDA'
        elif any(word in respuesta_ia.lower() for word in ['especie', 'animal', 'fauna', 'mamífero']):
            categoria = 'ANIMAL'
        else:
            categoria = 'LUGAR'
    
    descripcion = extraer_dato("DESC", respuesta_ia)
    historia = extraer_dato("HISTORIA", respuesta_ia)
    stats_raw = extraer_dato("STATS", respuesta_ia)
    evos_raw = extraer_dato("EVOS", respuesta_ia)
    
    # Procesar números con validación
    numeros = [int(n) for n in re.findall(r'\d+', stats_raw)][:4]
    while len(numeros) < 4: 
        numeros.append(0)
    numeros = [min(100, max(0, n)) for n in numeros]
    
    # Procesar variantes (filtrar adjetivos comunes)
    adjetivos_prohibidos = ['fuerte', 'veloz', 'grande', 'pequeño', 'rápido', 'lento', 'delicioso', 'sabroso']
    variantes = []
    for v in evos_raw.split(","):
        v_clean = v.strip().lower()
        if v_clean and len(v_clean) > 2 and v_clean not in adjetivos_prohibidos:
            variantes.append(v.strip())
    
    variantes = variantes[:3]
    
    return {
        'nombre': nombre,
        'categoria': categoria,
        'descripcion': descripcion,
        'historia': historia,
        'numeros': numeros,
        'variantes': variantes
    }

def obtener_etiquetas(categoria):
    """Mapeo estricto de etiquetas por categoría"""
    mapeo = {
        'COMIDA': ["😋 Sabor", "🌶️ Picante", "🥗 Salud", "💎 Rareza"],
        'ANIMAL': ["🐾 Fuerza", "⚡ Agilidad", "⚠️ Peligro", "💎 Rareza"],
        'LUGAR': ["🏛️ Historia", "📸 Belleza", "🌍 Cultura", "💎 Rareza"]
    }
    return mapeo.get(categoria, mapeo['COMIDA'])

def obtener_badge_categoria(categoria):
    """Genera badge visual según categoría"""
    badges = {
        'COMIDA': '<span class="categoria-badge badge-comida">🍕 COMIDA</span>',
        'ANIMAL': '<span class="categoria-badge badge-animal">🦁 ANIMAL</span>',
        'LUGAR': '<span class="categoria-badge badge-lugar">🏛️ LUGAR</span>'
    }
    return badges.get(categoria, '')

def renderizar_ficha(datos, etiquetas):
    """Renderiza ficha con glassmorphism"""
    
    st.markdown(f"## 📋 {datos['nombre']}")
    
    badge_html = obtener_badge_categoria(datos['categoria'])
    st.markdown(f"<div class='data-card'>{badge_html}<p style='margin-top:10px;'>{datos['descripcion']}</p></div>", unsafe_allow_html=True)
    
    st.markdown("### 📖 Historia")
    st.markdown(f"<div class='historia-box'>{datos['historia']}</div>", unsafe_allow_html=True)
    
    st.markdown("### 📊 Puntos Base")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"<p><b>{etiquetas[0]}:</b> {datos['numeros'][0]}%</p>", unsafe_allow_html=True)
        st.progress(datos['numeros'][0]/100)
        st.markdown(f"<p><b>{etiquetas[1]}:</b> {datos['numeros'][1]}%</p>", unsafe_allow_html=True)
        st.progress(datos['numeros'][1]/100)
    with c2:
        st.markdown(f"<p><b>{etiquetas[2]}:</b> {datos['numeros'][2]}%</p>", unsafe_allow_html=True)
        st.progress(datos['numeros'][2]/100)
        st.markdown(f"<p><b>{etiquetas[3]}:</b> {datos['numeros'][3]}%</p>", unsafe_allow_html=True)
        st.progress(datos['numeros'][3]/100)
    
    st.markdown("### 🔄 Variantes Registradas")
    st.markdown("*Haz clic para explorar*")
    
    return datos['variantes']

# ========================================
# GESTOR DE ESTADOS (DESACOPLADO)
# ========================================

with st.container():
    st.markdown("<div class='pokedex-frame'>", unsafe_allow_html=True)
    
    estado_placeholder = st.empty()
    
    # DECISIÓN DE FLUJO SEGÚN ESTADO
    if st.session_state.objetivo_actual and st.session_state.tipo_entrada:
        
        # HAY UN OBJETIVO PENDIENTE (imagen o variante)
        nombre_objetivo = st.session_state.objetivo_actual
        tipo = st.session_state.tipo_entrada
        
        if tipo == 'texto':
            estado_placeholder.markdown(f"<div class='status-indicator'>🔄 Accediendo a base de datos: {nombre_objetivo}</div>", unsafe_allow_html=True)
        else:
            estado_placeholder.markdown(f"<div class='status-indicator'>🔍 Analizando objetivo capturado</div>", unsafe_allow_html=True)
        
        try:
            # Consultar IA según tipo
            if tipo == 'imagen':
                respuesta = consultar_ia_multimodal(
                    nombre_objetivo, 
                    'imagen', 
                    imagen_b64=st.session_state.get('imagen_b64'),
                    categoria_contexto=None
                )
            else:  # texto (variante)
                respuesta = consultar_ia_multimodal(
                    nombre_objetivo, 
                    'texto',
                    categoria_contexto=st.session_state.categoria_heredada
                )
            
            datos = procesar_respuesta(respuesta)
            etiquetas = obtener_etiquetas(datos['categoria'])
            
            # Actualizar historial
            if tipo == 'imagen':
                st.session_state.historial_ruta = [datos['nombre']]
            else:
                st.session_state.historial_ruta.append(datos['nombre'])
            
            st.session_state.categoria_heredada = datos['categoria']
            st.session_state.datos_cache[datos['nombre']] = datos
            
            # Layout
            col_img, col_info = st.columns([1, 2])
            
            with col_img:
                if tipo == 'imagen' and st.session_state.get('imagen_original'):
                    st.image(st.session_state.imagen_original, use_container_width=True, caption="Objetivo Escaneado")
                else:
                    # Generar imagen para variante
                    with st.spinner(f"Generando visualización de {datos['nombre']}..."):
                        imagen_gen = generar_imagen_ia(datos['nombre'], datos['categoria'])
                        if imagen_gen:
                            st.image(imagen_gen, use_container_width=True, caption=f"Imagen generada: {datos['nombre']}")
                        else:
                            st.info(f"📊 **{datos['nombre']}**\n\nCategoría: {datos['categoria']}")
            
            with col_info:
                variantes = renderizar_ficha(datos, etiquetas)
                
                # Botones de variantes (bidireccionales)
                st.markdown("---")
                for idx, var in enumerate(variantes):
                    col_btn = st.columns([1])[0]
                    with col_btn:
                        if st.button(f"🔍 Explorar: {var}", key=f"var_{var}_{idx}", use_container_width=True):
                            st.session_state.objetivo_actual = var
                            st.session_state.tipo_entrada = 'texto'
                            st.rerun()
            
            # Audio
            try:
                texto_audio = f"{datos['nombre']}. {datos['descripcion']}"
                texto_audio = sanitizar_texto(texto_audio)
                tts = gTTS(text=texto_audio, lang='es')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)
            except:
                pass
            
            estado_placeholder.markdown("<div class='status-indicator'>✅ Datos cargados correctamente</div>", unsafe_allow_html=True)
            
            # Resetear objetivo (permitir nueva entrada)
            st.session_state.objetivo_actual = None
            st.session_state.tipo_entrada = None
            
        except Exception as e:
            estado_placeholder.markdown(f"<div class='status-indicator'>❌ Error: {str(e)}</div>", unsafe_allow_html=True)
            st.error(f"Error en procesamiento: {e}")
            st.session_state.objetivo_actual = None
    
    else:
        # MODO ESPERA: Captura de imagen
        estado_placeholder.markdown("<div class='status-indicator'>⏳ Sistema listo. Captura un objetivo...</div>", unsafe_allow_html=True)
        
        col_upload, col_placeholder = st.columns([1, 2])
        
        with col_upload:
            archivo = st.file_uploader("📸 Cargar Imagen", type=["jpg", "png", "jpeg"])
            
            if archivo:
                imagen_pil = PIL.Image.open(archivo)
                st.image(imagen_pil, use_container_width=True, caption="Vista Previa")
                
                if st.button("🔍 INICIAR ESCANEO", type="primary", use_container_width=True):
                    # Guardar en estado
                    st.session_state.imagen_b64 = encode_image(archivo)
                    st.session_state.imagen_original = imagen_pil
                    st.session_state.objetivo_actual = "imagen_cargada"
                    st.session_state.tipo_entrada = 'imagen'
                    st.rerun()
        
        with col_placeholder:
            st.info("""
            ### 🎯 Instrucciones
            
            1. **Carga una imagen** de comida, animal o lugar
            2. **Presiona INICIAR ESCANEO** para analizar
            3. **Explora variantes** haciendo clic en los botones amarillos
            4. **Navega infinitamente** entre elementos relacionados
            
            ---
            
            **Características:**
            - ✅ Análisis multimodal con Chain-of-Thought
            - ✅ Generación automática de imágenes para variantes
            - ✅ Validación de esquema por categoría
            - ✅ Navegación desacoplada imagen→texto
            - ✅ Interfaz Glassmorphism adaptativa
            """)
    
    st.markdown("</div>", unsafe_allow_html=True)
