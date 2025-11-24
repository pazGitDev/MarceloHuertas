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

# ============================================
# MÉTRICAS ACTUALES
# ============================================
if latest:
    st.subheader("📊 Lecturas Actuales")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        ph_value = latest['ph']
        if ph_value is not None:
            st.metric(
                label="🧪 pH",
                value=f"{ph_value:.2f}",
                delta=None
            )
            # Indicador de estado del pH
            if 6.0 <= ph_value <= 7.5:
                st.success("✅ pH óptimo")
            elif 5.5 <= ph_value < 6.0 or 7.5 < ph_value <= 8.0:
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
        # Indicador de humedad
        if humidity >= 60:
            st.success("✅ Humedad óptima")
        elif 30 <= humidity < 60:
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
        # Indicador de luz
        if light > 10000:
            st.success("☀️ Luz solar directa")
        elif light > 1000:
            st.info("⛅ Luz indirecta")
        else:
            st.warning("🌙 Poca luz")

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
    df_ph = df[df['ph'].notna()].copy()
    
    if not df_ph.empty:
        fig_ph = px.line(
            df_ph,
            x='read_at',
            y='ph',
            title='',
            labels={'read_at': 'Fecha y Hora', 'ph': 'pH'}
        )
        fig_ph.add_hline(y=7.0, line_dash="dash", line_color="green", 
                         annotation_text="pH Neutro (7.0)")
        fig_ph.add_hrect(y0=6.0, y1=7.5, fillcolor="green", opacity=0.1,
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
                           annotation_text="Mínimo (30%)")
    fig_humidity.add_hrect(y0=60, y1=100, fillcolor="green", opacity=0.1,
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
        df_ph_stats = df[df['ph'].notna()]
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
