# Función para leer el archivo de forma segura
def extraer_contenido(archivo):
    try:
        extension = archivo.name.split('.')[-1].lower()
        
        if extension in ['xlsx', 'xls']:
            df = pd.read_excel(archivo)
            return df.to_string()
            
        elif extension == 'docx':
            doc = Document(archivo)
            return "\n".join([para.text for para in doc.paragraphs])
            
        elif extension == 'pdf':
            # Leemos el PDF desde la memoria
            archivo_bytes = archivo.read()
            doc = fitz.open(stream=archivo_bytes, filetype="pdf")
            texto = ""
            for pagina in doc:
                texto += pagina.get_text()
            return texto
        
        return None # Si es imagen, devuelve None para usar Scout
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

# --- PARTE DE LA INTERFAZ ---
st.title("📈 Finatrix Multi-Formato")

archivo_subido = st.file_uploader("Sube Balance (Excel, PDF, Word o Imagen)", 
                                  type=["pdf", "xlsx", "docx", "png", "jpg"])

if archivo_subido is not None:
    # Usamos la función que creamos arriba
    resultado = extraer_contenido(archivo_subido)
    
    if resultado:
        st.success("✅ Texto extraído con éxito")
        st.text_area("Previsualización del texto:", resultado[:500] + "...", height=150)
    else:
        st.warning("📸 No se detectó texto digital. Se requiere análisis de imagen (Scout).")
