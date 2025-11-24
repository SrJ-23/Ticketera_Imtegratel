import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time

# ===========================
# 1. CONFIGURACIÓN Y CONSTANTES
# ===========================

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Ticketera",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cargar credenciales desde Secrets
def cargar_configuracion():
    """Carga configuración desde Secrets."""
    try:
        if hasattr(st, 'secrets'):
            USERS = dict(st.secrets["users"])
            GOOGLE_CREDS = dict(st.secrets["google_sheets"])
            return USERS, GOOGLE_CREDS
        else:
            # Para desarrollo local, puedes crear un archivo secrets.toml en carpeta .streamlit
            st.error("No se encontraron secrets configurados")
            return None, None
    except Exception as e:
        st.error(f"Error cargando configuración: {e}")
        return None, None

# Cargar configuración
USERS, GOOGLE_CREDS = cargar_configuracion()
if USERS is None or GOOGLE_CREDS is None:
    st.stop()

# Constantes de Negocio
OPCIONES_ORIGEN = [
    "Correo", "OperaX", "WhatsApp", "Llamada", 
    "Consulta interna", "Troubleticket"
]

OPCIONES_MOTIVO = [
    "Pendiente de llamar/ubicar al cliente", "Cliente Ok no requiere visita",
    "Enviado a Territorio", "Atendido por Territorio", "No se ubica para validar",
    "Validado", "Reenviado a Territorio", "Cliente en suspención",
    "Validación de Parametros", "Configuración de HGU", "Configuración de Deco",
    "Escalamiento por correo", "Averia Pendiente", "Cliente en baja",
    "No contesta", "Alerta de masiva", "Comercial pendiente",
    "Cliente no desea atención", "Escalamiento TDP", "Pedido con visita tec. Cancelado",
    "Se Deriva a Comercial", "Problemas Comerciales", "Consulta Reclamo",
    "Pedido con visita tec. Pendiente.", "CLIENTE CMS", "Cambio de Facilidades",
    "Avería Liquidada"
]

HOJA_CALCULO = "Ticketera_detalles"

# ===========================
# 2. GESTIÓN DE ESTADO Y UTILIDADES
# ===========================

def inicializar_session_state():
    """Inicializa las variables de estado si no existen."""
    default_values = {
        'logged_in': False,
        'user': None,
        'current_page': 'menu',
        'form_start_time': None,
        'form_origen': None,
        'form_campo_extra': "",
        'form_motivo': None,
        'form_detalles': "",
        'form_reset_counter': 0
    }
    
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

def resetear_formulario():
    """Limpia los campos del formulario y reinicia el timer."""
    st.session_state['form_origen'] = None
    st.session_state['form_campo_extra'] = ""
    st.session_state['form_motivo'] = None
    st.session_state['form_detalles'] = ""
    st.session_state['form_start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state['form_reset_counter'] += 1

def cambiar_pagina(pagina):
    """Navegación simple."""
    st.session_state['current_page'] = pagina
    if pagina == 'formulario':
        if not st.session_state.get('form_start_time'):
            st.session_state['form_start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.rerun()

# ===========================
# 3. SERVICIOS (GOOGLE SHEETS)
# ===========================

@st.cache_resource(ttl=3600)
def conectar_google_sheets():
    """Conecta con Google Sheets usando credenciales de Secrets."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Usar credenciales desde Secrets (ya es un diccionario)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDS, scope)
        client = gspread.authorize(creds)
        
        # Intentar abrir la hoja para validar conexión
        sheet = client.open(HOJA_CALCULO).sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Error de conexión con Google Sheets: {e}")
        return None

def guardar_registro(sheet, datos):
    """Guarda un nuevo registro en Google Sheets."""
    try:
        sheet.append_row(datos)
        return True
    except Exception as e:
        st.error(f"Error al escribir en la hoja: {e}")
        return False

# ===========================
# 4. COMPONENTES DE UI
# ===========================

def sidebar_info():
    """Muestra información del usuario y navegación en la barra lateral."""
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=80)
        st.title(f"Hola, {st.session_state['user']}")
        st.markdown("---")
        
        if st.button("🏠 Menú Principal", use_container_width=True):
            cambiar_pagina('menu')
            
        st.markdown("---")
        if st.button("🔒 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()


# ===========================
# 5. PÁGINAS
# ===========================

def login_page():
    """Página de inicio de sesión."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🎫 Ticketera Login")
        st.markdown("Ingresa tus credenciales para acceder al sistema.")
        
        with st.form("login_form"):
            username = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            
            if submit:
                if username in USERS and USERS[username] == password:
                    st.session_state['user'] = username
                    st.session_state['logged_in'] = True
                    st.toast(f"Bienvenido {username}", icon="👋")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")

def menu_principal():
    """Menú Dashboard."""
    sidebar_info()
    st.title("📌 Panel de Control")
    st.markdown("Selecciona una acción para comenzar.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.subheader("📝 Nuevo Ticket")
            st.markdown("Registra una nueva incidencia, llamada o correo.")
            if st.button("Crear Registro", key="btn_nuevo", type="primary", use_container_width=True):
                # Limpiamos antes de entrar para asegurar un formulario fresco
                resetear_formulario()
                cambiar_pagina('formulario')
    
    with col2:
        with st.container(border=True):
            st.subheader("📊 Historial")
            st.markdown("Visualiza los últimos registros ingresados al sistema.")
            if st.button("Ver Registros", key="btn_ver", use_container_width=True):
                cambiar_pagina('registros')

def pagina_registros():
    """Muestra la tabla de registros."""
    sidebar_info()
    st.title("📋 Historial de Registros")
    
    sheet = conectar_google_sheets()
    if not sheet: return

    with st.spinner("Cargando datos..."):
        try:
            datos = sheet.get_all_values()
            if len(datos) > 1:
                df = pd.DataFrame(datos[1:], columns=datos[0])
                st.dataframe(
                    df.tail(15).iloc[::-1], # Mostramos los ultimos 15, invertidos (más reciente arriba)
                    use_container_width=True, 
                    hide_index=True
                )
                st.caption(f"Total histórico de registros: {len(df)}")
            else:
                st.info("La base de datos está vacía.")
        except Exception as e:
            st.error(f"Error al procesar datos: {e}")

def pagina_formulario():
    """Formulario de ingreso de datos."""
    sidebar_info()
    st.title("📝 Nuevo Incidente")
    
    sheet = conectar_google_sheets()
    if not sheet: return

    # Variables automáticas
    usuario = st.session_state['user']
    fecha_inicio = st.session_state.get('form_start_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Layout Info
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.info(f"👤 **Operador:** {usuario}")
    with col_info2:
        st.warning(f"🕒 **Inicio:** {fecha_inicio}")

    st.markdown("---")

    # --- CAMPOS DEL FORMULARIO ---
    # Usamos keys únicas que incluyen el contador de reset para evitar el error
    
    origen = st.selectbox(
        "Origen de la Incidencia *", 
        OPCIONES_ORIGEN, 
        index=None, 
        placeholder="Seleccione origen...",
        key=f"origen_{st.session_state.form_reset_counter}"
    )

    # Actualizar el estado del formulario cuando cambia el widget
    if origen != st.session_state.form_origen:
        st.session_state.form_origen = origen

    # Lógica de campo dinámico
    label_dinamico = None
    placeholder_dinamico = None
    
    if st.session_state.form_origen == "Correo":
        label_dinamico = "Asunto del Correo *"
        placeholder_dinamico = "Copie el asunto exacto"
    elif st.session_state.form_origen == "WhatsApp":
        label_dinamico = "Número de Contacto *"
        placeholder_dinamico = "51999..."
    elif st.session_state.form_origen == "Consulta interna":
        label_dinamico = "Solicitante *"
        placeholder_dinamico = "Nombre del área/persona"
    elif st.session_state.form_origen == "Troubleticket":
        label_dinamico = "Número INC *"
        placeholder_dinamico = "INC0000..."

    campo_extra = ""
    if label_dinamico:
        campo_extra = st.text_input(
            label_dinamico, 
            placeholder=placeholder_dinamico,
            value=st.session_state.form_campo_extra,
            key=f"campo_extra_{st.session_state.form_reset_counter}"
        )
        # Actualizar el estado del formulario
        if campo_extra != st.session_state.form_campo_extra:
            st.session_state.form_campo_extra = campo_extra

    motivo = st.selectbox(
        "Motivo/Solución *", 
        OPCIONES_MOTIVO, 
        index=None, 
        placeholder="Seleccione tipificación...",
        key=f"motivo_{st.session_state.form_reset_counter}"
    )

    # Actualizar el estado del formulario cuando cambia el widget
    if motivo != st.session_state.form_motivo:
        st.session_state.form_motivo = motivo

    detalles = st.text_area(
        "Detalles del caso *", 
        height=100,
        placeholder="Resumen ejecutivo de la gestión...",
        value=st.session_state.form_detalles,
        key=f"detalles_{st.session_state.form_reset_counter}"
    )

    # Actualizar el estado del formulario cuando cambia el widget
    if detalles != st.session_state.form_detalles:
        st.session_state.form_detalles = detalles

    # --- ACCIONES ---
    col_btn1, col_btn2 = st.columns([1, 4])

    with col_btn1:
        if st.button("💾 Finalizar y Guardar", type="primary", use_container_width=True):
            # Usar los valores del estado del formulario para validación
            errores = []
            if not st.session_state.form_origen: 
                errores.append("Falta el Origen.")
            if label_dinamico and not st.session_state.form_campo_extra: 
                errores.append(f"Falta: {label_dinamico}.")
            if not st.session_state.form_motivo: 
                errores.append("Falta el Motivo.")
            if not st.session_state.form_detalles: 
                errores.append("Faltan los Detalles.")

            if errores:
                for e in errores: 
                    st.error(f"⚠️ {e}")
            else:
                fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                datos_fila = [
                    usuario, 
                    fecha_inicio, 
                    fecha_cierre, 
                    st.session_state.form_origen, 
                    st.session_state.form_campo_extra, 
                    st.session_state.form_motivo, 
                    st.session_state.form_detalles
                ]
                
                with st.status("Guardando en la nube...", expanded=True) as status:
                    st.write("Conectando con base de datos...")
                    exito = guardar_registro(sheet, datos_fila)
                    
                    if exito:
                        status.update(label="¡Registro Exitoso!", state="complete", expanded=False)
                        st.success("✅ Datos guardados correctamente.")
                        # Opcional: resetear después de guardar exitosamente
                        # resetear_formulario()
                    else:
                        status.update(label="Error al guardar", state="error")

    with col_btn2:
        if st.button("📝 Nuevo Registro", use_container_width=True):
            resetear_formulario()
            st.rerun()

# ===========================
# 6. MAIN APP LOOP
# ===========================
def main():
    inicializar_session_state()

    if not st.session_state['logged_in']:
        login_page()
    else:
        pagina = st.session_state['current_page']
        
        if pagina == 'menu':
            menu_principal()
        elif pagina == 'formulario':
            pagina_formulario()
        elif pagina == 'registros':
            pagina_registros()

if __name__ == "__main__":
    main()