import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# --- CONFIGURACIÓN DE PÁGINA Y BRANDING OWLA ---
st.set_page_config(page_title="Simulador Dinámico OWLA", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(to bottom, #ffffff 0%, #fcfbf9 100%); }
    h1, h2, h3, h4, .st-emotion-cache-10trblm { color: #bd9b60 !important; font-weight: bold;}
    [data-testid="stMetricValue"] { color: #bd9b60 !important; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# --- PANEL LATERAL (SIDEBAR) ---
try:
    st.sidebar.image("Owla.jpg", use_container_width=True)
except Exception:
    pass # Falla silenciosamente si no está el logo para no romper la app

st.sidebar.header("⚙️ Parámetros del Sistema")

# 1. Masas
with st.sidebar.expander("Distribución Másica (g)", expanded=True):
    m_chasis = st.number_input("Masa Chasis", value=48.0)
    m_cartucho = st.number_input("Masa Cartucho", value=20.0)
    m_gas = st.number_input("Masa Gas CO2", value=8.0)
    m_w_front = st.number_input("Masa Rueda Delantera", value=1.4)
    m_w_rear = st.number_input("Masa Rueda Trasera", value=1.8)
    r_rueda = st.number_input("Radio Rueda (mm)", value=14.25) / 1000.0

# 2. Aerodinámica
with st.sidebar.expander("Mecánica de Fluidos (Aero)", expanded=False):
    altitud = st.number_input("Altitud Pista (m)", value=0.0, step=50.0)
    cd = st.number_input("Coeficiente Drag (Cd)", value=0.18, step=0.01) # Reducido para mantener velocidad
    area = st.number_input("Área Frontal (m²)", value=0.0012, format="%.5f")
    cd_a = cd * area

# 3. Tribología: Ruedas y Tether Line
with st.sidebar.expander("Fricción y Guiado (Tribología)", expanded=True):
    st.markdown("**Rodamientos (Ejes):**")
    tipo_rodamiento = st.selectbox("Material Rodamiento", 
        ("Cerámicos (μ=0.002)", "Mixtos ABEC7 (μ=0.004)", "Metálicos (μ=0.008)"))
    mu_ruedas = 0.002 if "Cerámicos" in tipo_rodamiento else (0.004 if "Mixtos" in tipo_rodamiento else 0.008)
    
    st.markdown("**Tether Line Guides (Guiado):**")
    tipo_tether = st.selectbox("Material Arandela (contra Nylon)", 
        ("PTFE/Teflón (μ=0.04)", "PEEK (μ=0.15)", "Acetal/POM (μ=0.20)", "Impresión 3D PLA (μ=0.35)"))
    
    dict_tether = {"PTFE/Teflón (μ=0.04)": 0.04, "PEEK (μ=0.15)": 0.15, "Acetal/POM (μ=0.20)": 0.20, "Impresión 3D PLA (μ=0.35)": 0.35}
    mu_tether = dict_tether[tipo_tether]
    
    # La pista genera una tensión y vibración constante sobre el cable que aprieta la arandela
    fuerza_normal_cable = st.slider("Fuerza Normal Equivalente Cable (N)", 0.1, 2.0, 0.4, help="Fuerza con la que el cable presiona la arandela por tensión y vibración.")

# 4. Motor
with st.sidebar.expander("Perfil de Empuje CO2", expanded=False):
    t_empuje = st.number_input("Tiempo de Empuje (s)", value=0.45) # Aumentado para llegar a ~24m/s
    f_media = st.number_input("Fuerza Promedio (N)", value=5.8)

# --- NÚCLEO DE CÁLCULO FÍSICO ---
m_total = (m_chasis + m_cartucho + m_gas) / 1000.0
# Inercia Rotacional
m_efectiva = m_total + 2 * (0.5 * (m_w_front/1000.0)) + 2 * (0.5 * (m_w_rear/1000.0))
# Densidad aire ISA
rho = 1.225 * (1 - 2.25577e-5 * altitud)**4.2561

st.title("Arquitectura Computacional de Telemetría")
st.markdown("Integración numérica con análisis avanzado de fricción de **Tether Line** y disipación energética.")

def modelo_cinematico(t, y):
    v = y[1]
    
    # 1. Empuje (Motor)
    thrust = f_media if t <= t_empuje else 0.0
    
    # 2. Arrastre (Aero)
    drag = 0.5 * rho * cd_a * (v**2)
    
    # 3. Fricción Ruedas (Constante)
    friction_wheels = mu_ruedas * m_total * 9.81
    
    # 4. Fricción Tether Line (Dinámica contra el cable)
    # Se añade un pequeño factor dependiente de v^2 simulando el "flutter" aerodinámico que sacude el cable
    friction_tether = mu_tether * (fuerza_normal_cable + 0.01 * v)
    
    a = (thrust - drag - friction_wheels - friction_tether) / m_efectiva
    
    if v <= 0 and a < 0: a = 0.0
    return [v, a]

def cruce_meta(t, y): return y[0] - 20.0
cruce_meta.terminal = True
cruce_meta.direction = 1

sol = solve_ivp(modelo_cinematico, [0, 1.5], [0, 0], events=cruce_meta, max_step=0.001)

# --- VISUALIZACIÓN ANALÍTICA MULTI-GRÁFICA ---
if sol.status == 1:
    t_arr = sol.t
    x_arr = sol.y[0]
    v_arr = sol.y[1]
    
    tiempo_pista = sol.t_events[0][0]
    vel_maxima = max(v_arr)
    vel_meta = v_arr[-1]
    
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("⏱️ Tiempo Pista", f"{tiempo_pista:.3f} s")
    col2.metric("🚀 Velocidad Punta", f"{vel_maxima:.2f} m/s", f"{vel_maxima*3.6:.1f} km/h")
    col3.metric("🏁 Velocidad Meta", f"{vel_meta:.2f} m/s", "Fase de inercia")
    col4.metric("⚖️ Masa Efectiva", f"{m_efectiva*1000:.1f} g", "Incluye inercia ruedas")

    # --- RECONSTRUCCIÓN DE VECTORES PARA GRÁFICAS ---
    thrust_arr = np.where(t_arr <= t_empuje, f_media, 0.0)
    drag_arr = 0.5 * rho * cd_a * (v_arr**2)
    fric_w_arr = np.full_like(t_arr, mu_ruedas * m_total * 9.81)
    fric_t_arr = mu_tether * (fuerza_normal_cable + 0.01 * v_arr)
    accel_arr = (thrust_arr - drag_arr - fric_w_arr - fric_t_arr) / m_efectiva
    
    # Energías
    energia_cinetica = 0.5 * m_efectiva * (v_arr**2)

    # --- CREACIÓN DEL DASHBOARD DE GRÁFICAS (2x2) ---
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor('#fcfbf9')
    color_owla = '#bd9b60'

    # 1. Cinemática (V y X)
    ax1 = axs[0, 0]
    ax1.plot(t_arr, v_arr, color=color_owla, lw=3, label="Velocidad (m/s)")
    ax1_twin = ax1.twinx()
    ax1_twin.plot(t_arr, x_arr, color='#333', ls='--', alpha=0.5, label="Posición (m)")
    ax1.set_title("1. Perfil Cinemático", fontweight='bold', color=color_owla)
    ax1.set_xlabel("Tiempo (s)")
    ax1.set_ylabel("Velocidad (m/s)")
    ax1_twin.set_ylabel("Espacio (m)")
    ax1.grid(alpha=0.3)

    # 2. Aceleración
    ax2 = axs[0, 1]
    ax2.plot(t_arr, accel_arr, color='#971B2F', lw=2)
    ax2.fill_between(t_arr, accel_arr, 0, where=(accel_arr>=0), color='#91d6ac', alpha=0.3, label="Acelerando")
    ax2.fill_between(t_arr, accel_arr, 0, where=(accel_arr<0), color='#971B2F', alpha=0.3, label="Decelerando")
    ax2.set_title("2. Fuerzas G (Aceleración)", fontweight='bold', color=color_owla)
    ax2.set_xlabel("Tiempo (s)")
    ax2.set_ylabel("Aceleración (m/s²)")
    ax2.axhline(0, color='black', lw=1)
    ax2.legend()
    ax2.grid(alpha=0.3)

    # 3. Desglose de Fuerzas Vectoriales
    ax3 = axs[1, 0]
    ax3.plot(t_arr, thrust_arr, color='#91d6ac', lw=2, label="Empuje CO2")
    ax3.plot(t_arr, drag_arr, color='#971B2F', lw=2, label="Drag Aero")
    ax3.plot(t_arr, fric_t_arr, color='#bd9b60', lw=2, label="Fricción Tether Line")
    ax3.set_title("3. Interacción de Fuerzas (N)", fontweight='bold', color=color_owla)
    ax3.set_xlabel("Tiempo (s)")
    ax3.set_ylabel("Fuerza (Newtons)")
    ax3.legend()
    ax3.grid(alpha=0.3)

    # 4. Dinámica Energética
    ax4 = axs[1, 1]
    ax4.plot(t_arr, energia_cinetica, color='#05C3DE', lw=2, label="Energía Cinética (J)")
    ax4.set_title("4. Conservación de Energía", fontweight='bold', color=color_owla)
    ax4.set_xlabel("Tiempo (s)")
    ax4.set_ylabel("Energía (Julios)")
    ax4.fill_between(t_arr, energia_cinetica, 0, color='#05C3DE', alpha=0.1)
    ax4.legend()
    ax4.grid(alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig)
    
else:
    st.error("Error en la integración: Revisa los parámetros extremos.")