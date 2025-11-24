import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client
from datetime import datetime, timedelta

# ============================================
# CONFIGURACIÓN DE SUPABASE
# ============================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Crear cliente de Supabase
@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# ============================================
# FUNCIONES DE DATOS
# ============================================
@st.cache_data(ttl=60)  # Cache por 60 segundos
def fetch_data(hours=24):
    """Obtiene datos de las últimas X horas"""
    cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    response = supabase.table('sensor_readings')\
        .select('*')\
        .gte('read_at', cutoff_time)\
        .order('read_at', desc=False)\
        .execute()
    
    df = pd.DataFrame(response.data)
    if not df.empty:
        df['read_at'] = pd.to_datetime(df['read_at'])
    return df

def get_latest_reading():
    """Obtiene la última lectura"""
    response = supabase.table('sensor_readings')\
        .select('*')\
        .order('read_at', desc=True)\
        .limit(1)\
        .execute()
    
    if response.data:
        return response.data[0]
    return None

# ============================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================
st.set_page_config(
    page_title="🌱 Monitor de Jardín",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# TÍTULO Y DESCRIPCIÓN
# ============================================
st.title("🌱 Dashboard de Monitoreo de Jardín")
st.markdown("---")

# ============================================
# SIDEBAR - CONTROLES
# ============================================
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Selector de rango de tiempo
    time_range = st.selectbox(
        "Rango de tiempo",
        options=[1, 6, 12, 24, 48, 72],
        index=3,
        format_func=lambda x: f"Últimas {x} horas"
    )
    
    st.markdown("---")
    
    # Configuración de rangos óptimos
    st.subheader("🎯 Rangos Óptimos")
    
    # Rangos de pH
    st.markdown("**🧪 pH**")
    col1, col2 = st.columns(2)
    with col1:
        ph_min = st.number_input("Mínimo", min_value=0.0, max_value=14.0, value=6.0, step=0.1, key="ph_min")
    with col2:
        ph_max = st.number_input("Máximo", min_value=0.0, max_value=14.0, value=7.5, step=0.1, key="ph_max")
    
    # Rangos de Humedad
    st.markdown("**💧 Humedad (%)**")
    col3, col4 = st.columns(2)
    with col3:
        humidity_min = st.number_input("Mínimo", min_value=0, max_value=100, value=60, step=5, key="hum_min")
    with col4:
        humidity_max = st.number_input("Máximo", min_value=0, max_value=100, value=100, step=5, key="hum_max")
    
    # Rangos de Luz
    st.markdown("**☀️ Luz (lux)**")
    col5, col6 = st.columns(2)
    with col5:
        light_min = st.number_input("Mínimo", min_value=0, max_value=100000, value=1000, step=100, key="light_min")
    with col6:
        light_max = st.number_input("Máximo", min_value=0, max_value=100000, value=10000, step=100, key="light_max")
    
    st.markdown("---")
    
    # Botón de actualización
    if st.button("🔄 Actualizar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Información del sistema
    st.subheader("ℹ️ Información")
    st.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    st.caption("Los datos se actualizan cada 10 segundos desde el ESP32")

# ============================================
# OBTENER DATOS
# ============================================
df = fetch_data(time_range)
latest = get_latest_reading()

# Filtrar valores -1 y null de pH en todo el DataFrame
if not df.empty:
    df.loc[(df['ph'] == -1) | (df['ph'].isna()), 'ph'] = None

# ============================================
# MÉTRICAS ACTUALES
# ============================================
if latest:
    st.subheader("📊 Lecturas Actuales")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        ph_value = latest['ph']
        if ph_value is not None and ph_value != -1:
            st.metric(
                label="🧪 pH",
                value=f"{ph_value:.2f}",
                delta=None
            )
            # Indicador de estado del pH usando rangos configurados
            if ph_min <= ph_value <= ph_max:
                st.success("✅ pH óptimo")
            elif (ph_min - 0.5) <= ph_value < ph_min or ph_max < ph_value <= (ph_max + 0.5):
                st.warning("⚠️ pH aceptable")
            else:
                st.error("❌ pH fuera de rango")
        else:
            st.metric(label="🧪 pH", value="--")
            st.info("💡 Activa el modo pH en el ESP32")
    
    with col2:
        humidity = latest['humidity']
        st.metric(
            label="💧 Humedad del Suelo",
            value=f"{humidity}%",
            delta=None
        )
        # Indicador de humedad usando rangos configurados
        if humidity_min <= humidity <= humidity_max:
            st.success("✅ Humedad óptima")
        elif (humidity_min - 10) <= humidity < humidity_min:
            st.warning("⚠️ Considera regar")
        else:
            st.error("❌ Riego necesario")
    
    with col3:
        light = latest['light']
        st.metric(
            label="☀️ Luminosidad",
            value=f"{light:.0f} lux",
            delta=None
        )
        # Indicador de luz usando rangos configurados
        if light_min <= light <= light_max:
            st.success("✅ Luz óptima")
        elif light > light_max:
            st.warning("☀️ Luz muy intensa")
        else:
            st.info("🌙 Poca luz")

    st.caption(f"Última lectura: {pd.to_datetime(latest['read_at']).strftime('%d/%m/%Y %H:%M:%S')}")

else:
    st.warning("⚠️ No hay datos disponibles")

st.markdown("---")

# ============================================
# GRÁFICOS DE TENDENCIAS
# ============================================
if not df.empty:
    st.subheader("📈 Tendencias")
    
    # Gráfico de pH
    st.markdown("### 🧪 Evolución del pH")
    # Filtrar valores válidos de pH (excluir null y -1)
    df_ph = df[(df['ph'].notna()) & (df['ph'] != -1)].copy()
    
    if not df_ph.empty:
        fig_ph = px.line(
            df_ph,
            x='read_at',
            y='ph',
            title='',
            labels={'read_at': 'Fecha y Hora', 'ph': 'pH'}
        )
        fig_ph.add_hline(y=7.0, line_dash="dash", line_color="gray", 
                         annotation_text="pH Neutro (7.0)")
        # Usar rangos configurados por el usuario
        fig_ph.add_hrect(y0=ph_min, y1=ph_max, fillcolor="green", opacity=0.1,
                         annotation_text="Rango óptimo", annotation_position="top left")
        fig_ph.update_layout(height=400)
        st.plotly_chart(fig_ph, use_container_width=True)
    else:
        st.info("💡 No hay lecturas de pH disponibles. Activa el modo pH en el ESP32.")
    
    # Gráfico de Humedad
    st.markdown("### 💧 Evolución de la Humedad del Suelo")
    fig_humidity = px.line(
        df,
        x='read_at',
        y='humidity',
        title='',
        labels={'read_at': 'Fecha y Hora', 'humidity': 'Humedad (%)'}
    )
    fig_humidity.add_hline(y=30, line_dash="dash", line_color="red",
                           annotation_text="Crítico (30%)")
    # Usar rangos configurados por el usuario
    fig_humidity.add_hrect(y0=humidity_min, y1=humidity_max, fillcolor="green", opacity=0.1,
                          annotation_text="Rango óptimo", annotation_position="top left")
    fig_humidity.update_layout(height=400)
    st.plotly_chart(fig_humidity, use_container_width=True)
    
    # Gráfico de Luminosidad
    st.markdown("### ☀️ Evolución de la Luminosidad")
    fig_light = px.area(
        df,
        x='read_at',
        y='light',
        title='',
        labels={'read_at': 'Fecha y Hora', 'light': 'Luminosidad (lux)'}
    )
    # Usar rangos configurados por el usuario
    fig_light.add_hrect(y0=light_min, y1=light_max, fillcolor="green", opacity=0.1,
                       annotation_text="Rango óptimo", annotation_position="top left")
    fig_light.update_layout(height=400)
    st.plotly_chart(fig_light, use_container_width=True)
    
    st.markdown("---")
    
    # ============================================
    # ESTADÍSTICAS
    # ============================================
    st.subheader("📊 Estadísticas del Período")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🧪 pH**")
        # Filtrar valores válidos para estadísticas
        df_ph_stats = df[(df['ph'].notna()) & (df['ph'] != -1)]
        if not df_ph_stats.empty:
            st.metric("Promedio", f"{df_ph_stats['ph'].mean():.2f}")
            st.metric("Mínimo", f"{df_ph_stats['ph'].min():.2f}")
            st.metric("Máximo", f"{df_ph_stats['ph'].max():.2f}")
        else:
            st.info("Sin datos de pH")
    
    with col2:
        st.markdown("**💧 Humedad**")
        st.metric("Promedio", f"{df['humidity'].mean():.1f}%")
        st.metric("Mínimo", f"{df['humidity'].min():.0f}%")
        st.metric("Máximo", f"{df['humidity'].max():.0f}%")
    
    with col3:
        st.markdown("**☀️ Luminosidad**")
        st.metric("Promedio", f"{df['light'].mean():.0f} lux")
        st.metric("Mínimo", f"{df['light'].min():.0f} lux")
        st.metric("Máximo", f"{df['light'].max():.0f} lux")
    
    st.markdown("---")
    
    # ============================================
    # TABLA DE DATOS RECIENTES
    # ============================================
    with st.expander("📋 Ver Datos Recientes (últimos 20 registros)"):
        df_display = df.tail(20).copy()
        df_display['read_at'] = df_display['read_at'].dt.strftime('%d/%m/%Y %H:%M:%S')
        # Reemplazar None con "--" para mejor visualización
        df_display['ph'] = df_display['ph'].apply(lambda x: "--" if pd.isna(x) else f"{x:.2f}")
        df_display = df_display[['read_at', 'ph', 'humidity', 'light']]
        df_display.columns = ['Fecha y Hora', 'pH', 'Humedad (%)', 'Luz (lux)']
        st.dataframe(df_display, use_container_width=True, hide_index=True)

else:
    st.info("⏳ No hay datos disponibles para el período seleccionado")

# ============================================
# FOOTER
# ============================================
st.markdown("---")
st.caption("🌱 Dashboard de Monitoreo de Jardín | Powered by ESP32 + Streamlit + Supabase")
