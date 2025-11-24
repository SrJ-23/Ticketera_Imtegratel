import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import time

# ===========================
# 1. CONFIGURACIÓN Y CONSTANTES
# ===========================

st.set_page_config(
    page_title="Sistema de Ticketera",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DEFINICIÓN DE LISTAS Y DICCIONARIOS SEGÚN REQUERIMIENTO ---

OPCIONES_ORIGEN = ["Correo", "WhatsApp", "Troubleticket", "Gestel"]

# Listas de motivos comunes para reutilizar
MOTIVOS_COMUNES_BASE = [
    "Pendiente de llamar/ubicar al cliente",
    "Cliente Ok no requiere visita",
    "Enviado a Territorio",
    "Cliente no contesta",
    "Reenviado a Territorio",
    "Cliente en suspención",
    "Configuración de HGU",
    "Averia Pendiente",
    "Alerta de masiva",
    "Comercial pendiente",
    "Atendido por BO",
    "CLIENTE CMS",
    "Troubleshoting"
]

# Diccionario que mapea cada Origen con sus Soluciones específicas
MOTIVOS_POR_ORIGEN = {
    "Correo": MOTIVOS_COMUNES_BASE, # La lista base tal cual
    "WhatsApp": MOTIVOS_COMUNES_BASE + ["Cambio de facilidades"], # Base + extra
    "Troubleticket": MOTIVOS_COMUNES_BASE, # La lista base tal cual
    "Gestel": [
        "Portabilidad",
        "Migraciones",
        "Cambio de Velocidades",
        "Baja total",
        "Cambio de circuito",
        "Independencia PBX",
        "Troubleshoting",
        "Enrutamiento",
        "Masivas",
        "Configuracion",
        "Facilidades de clase",
        "Reconfiguración",
        "Desviación de llamadas"
    ]
}

HOJA_CALCULO = "Ticketera_detalles"

# --- FUNCIONES DE CARGA ---

def cargar_configuracion():
    """Carga configuración desde Secrets."""
    try:
        if hasattr(st, 'secrets'):
            USERS = dict(st.secrets["users"])
            GOOGLE_CREDS = dict(st.secrets["google_sheets"])
            return USERS, GOOGLE_CREDS
        else:
            st.error("No se encontraron secrets configurados")
            return None, None
    except Exception as e:
        st.error(f"Error cargando configuración: {e}")
        return None, None

USERS, GOOGLE_CREDS = cargar_configuracion()
if USERS is None or GOOGLE_CREDS is None:
    st.stop()

# ===========================
# 2. GESTIÓN DE ESTADO
# ===========================

def inicializar_session_state():
    default_values = {
        'logged_in': False,
        'user': None,
        'current_page': 'menu',
        'form_start_time': None,
        'form_reset_counter': 0
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

def resetear_formulario():
    st.session_state['form_start_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state['form_reset_counter'] += 1

def cambiar_pagina(pagina):
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
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDS, scope)
        client = gspread.authorize(creds)
        sheet = client.open(HOJA_CALCULO).sheet1
        return sheet
    except Exception as e:
        st.error(f"❌ Error de conexión con Google Sheets: {e}")
        return None

def guardar_registro(sheet, datos):
    try:
        sheet.append_row(datos)
        return True
    except Exception as e:
        st.error(f"Error al escribir en la hoja: {e}")
        return False

# ===========================
# 4. COMPONENTES Y PÁGINAS
# ===========================

def sidebar_info():
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

def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🎫 Ticketera Login")
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
                    st.error("Credenciales incorrectas")

def menu_principal():
    sidebar_info()
    st.title("📌 Panel de Control")
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("📝 Nuevo Ticket")
            if st.button("Crear Registro", key="btn_nuevo", type="primary", use_container_width=True):
                resetear_formulario()
                cambiar_pagina('formulario')
    with col2:
        with st.container(border=True):
            st.subheader("📊 Mis Registros")
            if st.button("Ver Historial", key="btn_ver", use_container_width=True):
                cambiar_pagina('registros')

def pagina_registros():
    """
    Muestra solo los registros del usuario actual.
    """
    sidebar_info()
    st.title("📋 Mis Registros")
    
    sheet = conectar_google_sheets()
    if not sheet: return

    with st.spinner("Cargando sus datos..."):
        try:
            datos = sheet.get_all_values()
            if len(datos) > 1:
                # 1. Crear DataFrame
                df = pd.DataFrame(datos[1:], columns=datos[0])
                
                # 2. FILTRAR POR USUARIO (SOLO MUESTRA LO SUYO)
                usuario_actual = st.session_state['user']
                
                # Asumimos que la columna 0 o llamada 'Usuario' (o similar) tiene el nombre
                # Ajusta el nombre de la columna según tu Google Sheet real.
                # Aquí busco la columna que contenga "usuario" o uso la primera columna.
                col_usuario = df.columns[0] # Por defecto la primera
                for col in df.columns:
                    if "usuario" in col.lower() or "operador" in col.lower():
                        col_usuario = col
                        break
                
                df_filtrado = df[df[col_usuario] == usuario_actual]

                if not df_filtrado.empty:
                    st.dataframe(
                        df_filtrado.tail(20).iloc[::-1], # Últimos 20 registros del usuario
                        use_container_width=True, 
                        hide_index=True
                    )
                    st.caption(f"Total de mis registros: {len(df_filtrado)}")
                else:
                    st.info(f"No tienes registros ingresados con el usuario: {usuario_actual}")
            else:
                st.info("La base de datos está vacía.")
        except Exception as e:
            st.error(f"Error al procesar datos: {e}")

def pagina_formulario():
    sidebar_info()
    st.title("📝 Nuevo Incidente")
    
    sheet = conectar_google_sheets()
    if not sheet: return

    usuario = st.session_state['user']
    fecha_inicio = st.session_state.get('form_start_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    counter = st.session_state['form_reset_counter']

    # Info visual
    st.info(f"Usuario: **{usuario}** | Hora Inicio: **{fecha_inicio}**")
    st.markdown("---")

    # 1. SELECCIÓN DE ORIGEN
    origen = st.selectbox(
        "Origen de la Incidencia *", 
        OPCIONES_ORIGEN, 
        index=None, 
        placeholder="Seleccione origen...",
        key=f"origen_{counter}"
    )

    # 2. CAMPOS DINÁMICOS (REFERENCIAS)
    referencia_final = "" # Variable que guardaremos en la columna de referencia/extra
    input_val_1 = ""
    input_val_2 = ""

    if origen == "Correo":
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            input_val_1 = st.text_input("Asunto del Correo *", placeholder="Copie el asunto...", key=f"asunto_{counter}")
        with col_c2:
            input_val_2 = st.text_input("Remitente (Email) *", placeholder="cliente@correo.com", key=f"remitente_{counter}")
        
        # Concatenamos para guardar en una sola columna si tu Excel tiene estructura fija
        if input_val_1 and input_val_2:
            referencia_final = f"Asunto: {input_val_1} | Remitente: {input_val_2}"
        
    elif origen == "WhatsApp":
        input_val_1 = st.text_input("Número de Remitente *", placeholder="51999...", key=f"wa_num_{counter}")
        referencia_final = input_val_1

    elif origen == "Troubleticket":
        input_val_1 = st.text_input("Número INC *", placeholder="INC0000...", key=f"inc_{counter}")
        referencia_final = input_val_1

    elif origen == "Gestel":
        input_val_1 = st.text_input("Número de Orden *", placeholder="Ingrese orden...", key=f"orden_{counter}")
        referencia_final = input_val_1

    # 3. SELECCIÓN DE MOTIVO (DINÁMICO)
    lista_motivos = []
    if origen in MOTIVOS_POR_ORIGEN:
        lista_motivos = MOTIVOS_POR_ORIGEN[origen]
    
    motivo = st.selectbox(
        "Motivo / Solución *", 
        lista_motivos, 
        index=None, 
        placeholder="Seleccione primero el origen..." if not origen else "Seleccione solución...",
        disabled=(origen is None),
        key=f"motivo_{counter}"
    )

    # 4. DETALLES
    detalles = st.text_area(
        "Detalles del caso *", 
        height=100,
        key=f"detalles_{counter}"
    )

    st.markdown("---")
    col_btn1, col_btn2 = st.columns([1, 4])

    with col_btn1:
        if st.button("💾 Guardar", type="primary", use_container_width=True):
            # Validaciones
            errores = []
            if not origen: errores.append("Falta el Origen.")
            
            # Validar campos específicos
            if origen == "Correo":
                if not input_val_1 or not input_val_2: errores.append("Falta Asunto o Remitente.")
            elif origen == "WhatsApp" and not input_val_1: errores.append("Falta el Número.")
            elif origen == "Troubleticket" and not input_val_1: errores.append("Falta el INC.")
            elif origen == "Gestel" and not input_val_1: errores.append("Falta el Nro de Orden.")
            
            if not motivo: errores.append("Falta el Motivo.")
            if not detalles: errores.append("Faltan los Detalles.")

            if errores:
                for e in errores: st.error(f"⚠️ {e}")
            else:
                fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Preparamos la fila. 
                # Estructura asume: [Usuario, F.Inicio, F.Cierre, Origen, REFERENCIA(EXTRA), Motivo, Detalles]
                datos_fila = [
                    usuario, 
                    fecha_inicio, 
                    fecha_cierre, 
                    origen, 
                    referencia_final, # Aquí va el dato combinado o simple según origen
                    motivo, 
                    detalles
                ]
                
                with st.status("Guardando...", expanded=True) as status:
                    exito = guardar_registro(sheet, datos_fila)
                    if exito:
                        status.update(label="¡Guardado!", state="complete", expanded=False)
                        st.success("✅ Registro exitoso.")
                        time.sleep(1)
                        resetear_formulario()
                        st.rerun()
                    else:
                        status.update(label="Error", state="error")

    with col_btn2:
        if st.button("Limpiar / Nuevo", use_container_width=True):
            resetear_formulario()
            st.rerun()

# ===========================
# 5. EJECUCIÓN
# ===========================
def main():
    inicializar_session_state()
    if not st.session_state['logged_in']:
        login_page()
    else:
        pagina = st.session_state['current_page']
        if pagina == 'menu': menu_principal()
        elif pagina == 'formulario': pagina_formulario()
        elif pagina == 'registros': pagina_registros()

if __name__ == "__main__":
    main()