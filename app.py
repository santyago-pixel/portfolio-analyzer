import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Importar módulos personalizados
from portfolio_calculator import PortfolioCalculator
from example_data import generate_sample_data

# Configuración de la página
st.set_page_config(
    page_title="Portfolio Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .positive {
        color: #00C851;
    }
    .negative {
        color: #ff4444;
    }
    .neutral {
        color: #ffbb33;
    }
</style>
""", unsafe_allow_html=True)

def load_data():
    """Cargar datos de operaciones y precios"""
    st.info("📁 Carga tu archivo Excel o usa datos de ejemplo")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo Excel",
            type=['xlsx', 'xls'],
            help="El archivo debe contener dos hojas: 'Operaciones' y 'Precios'"
        )
        
        st.markdown("""
        **📋 Formato requerido:**
        
        **Hoja 'Operaciones':** Fecha, Operacion, Tipo de activo, Activo, Nominales, Precio, Valor
        **Hoja 'Precios':** Fechas en columna A, activos en fila 1
        """)
    
    with col2:
        if st.button("📊 Usar Datos de Ejemplo", type="secondary"):
            st.session_state.use_sample_data = True
    
    if uploaded_file is not None:
        try:
            # Cargar operaciones (estructura: Fecha, Operacion, Tipo de activo, Activo, Nominales, Precio, Valor)
            operaciones = pd.read_excel(uploaded_file, sheet_name='Operaciones')
            
            # Mapear columnas a formato esperado
            operaciones_mapped = pd.DataFrame()
            operaciones_mapped['Fecha'] = operaciones['Fecha']
            operaciones_mapped['Tipo'] = operaciones['Operacion']  # Compra/Venta
            operaciones_mapped['Activo'] = operaciones['Activo']
            operaciones_mapped['Cantidad'] = operaciones['Nominales']
            operaciones_mapped['Precio'] = operaciones['Precio']
            operaciones_mapped['Monto'] = operaciones['Valor']
            
            # Cargar precios (estructura: fechas en columna A, activos en fila 1)
            precios = pd.read_excel(uploaded_file, sheet_name='Precios')
            
            # La primera columna debe ser las fechas
            fecha_col = precios.columns[0]
            precios = precios.rename(columns={fecha_col: 'Fecha'})
            
            # Convertir a formato largo (melt)
            precios_long = precios.melt(
                id_vars=['Fecha'], 
                var_name='Activo', 
                value_name='Precio'
            )
            precios_long = precios_long.dropna()  # Eliminar filas con NaN
            
            st.session_state.use_sample_data = False
            return operaciones_mapped, precios_long
            
        except Exception as e:
            st.error(f"Error al cargar el archivo: {str(e)}")
            st.error("Verifica que el archivo tenga la estructura correcta:")
            st.error("- Hoja 'Operaciones': Fecha, Operacion, Tipo de activo, Activo, Nominales, Precio, Valor")
            st.error("- Hoja 'Precios': Fechas en columna A, activos en fila 1")
            return None, None
    
    # Usar datos de ejemplo si está habilitado
    if st.session_state.get('use_sample_data', False):
        from example_data import generate_sample_data_with_your_structure
        operaciones, precios = generate_sample_data_with_your_structure()
        st.success("✅ Datos de ejemplo cargados correctamente")
        return operaciones, precios
    
    return None, None

def create_advanced_metrics(calculator: PortfolioCalculator, risk_free_rate: float):
    """Crear métricas avanzadas usando el calculador"""
    metrics = calculator.calculate_metrics(risk_free_rate)
    
    # Crear tarjetas de métricas avanzadas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Sortino Ratio</div>
            <div class="metric-value {'positive' if metrics['sortino_ratio'] > 1 else 'negative' if metrics['sortino_ratio'] < 0 else 'neutral'}">
                {metrics['sortino_ratio']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Calmar Ratio</div>
            <div class="metric-value {'positive' if metrics['calmar_ratio'] > 1 else 'negative' if metrics['calmar_ratio'] < 0 else 'neutral'}">
                {metrics['calmar_ratio']:.2f}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">VaR 95%</div>
            <div class="metric-value negative">
                {metrics['var_95']:.2%}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">CVaR 95%</div>
            <div class="metric-value negative">
                {metrics['cvar_95']:.2%}
            </div>
        </div>
        """, unsafe_allow_html=True)

def create_performance_chart(returns_df):
    """Crear gráfico de performance"""
    if returns_df is None:
        return None
    
    # Calcular retornos acumulados
    returns_df['Cumulative_Return'] = (1 + returns_df['Rendimiento_Diario']).cumprod()
    
    fig = go.Figure()
    
    # Línea de rendimiento acumulado
    fig.add_trace(go.Scatter(
        x=returns_df['Fecha'],
        y=returns_df['Cumulative_Return'],
        mode='lines',
        name='Rendimiento Acumulado',
        line=dict(color='#667eea', width=2)
    ))
    
    # Línea de referencia (100%)
    fig.add_hline(y=1, line_dash="dash", line_color="gray", 
                  annotation_text="Punto de partida")
    
    fig.update_layout(
        title="Performance de la Cartera",
        xaxis_title="Fecha",
        yaxis_title="Valor Acumulado",
        hovermode='x unified',
        template="plotly_white"
    )
    
    return fig

def create_returns_distribution(returns_df):
    """Crear gráfico de distribución de rendimientos"""
    if returns_df is None:
        return None
    
    fig = px.histogram(
        returns_df, 
        x='Rendimiento_Diario',
        nbins=50,
        title="Distribución de Rendimientos Diarios",
        labels={'Rendimiento_Diario': 'Rendimiento Diario', 'count': 'Frecuencia'}
    )
    
    fig.update_layout(template="plotly_white")
    
    return fig

def main():
    st.title("📊 Portfolio Analyzer")
    st.markdown("---")
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Tasa libre de riesgo
        risk_free_rate = st.number_input(
            "Tasa Libre de Riesgo (%)",
            min_value=0.0,
            max_value=20.0,
            value=5.0,
            step=0.1
        ) / 100
        
        # Período de análisis
        st.subheader("📅 Período de Análisis")
        start_date = st.date_input("Fecha de Inicio", value=datetime.now() - timedelta(days=365))
        end_date = st.date_input("Fecha de Fin", value=datetime.now())
    
    # Cargar datos
    operaciones, precios = load_data()
    
    if operaciones is not None and precios is not None:
        # Crear calculador de cartera
        calculator = PortfolioCalculator(operaciones, precios)
        
        # Calcular rendimientos diarios
        returns_df = calculator.calculate_daily_returns()
        
        if returns_df is not None:
            # Calcular métricas
            metrics = calculator.calculate_metrics(risk_free_rate)
            
            if metrics is not None:
                # Mostrar métricas principales
                st.header("📈 Métricas de Performance")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Rendimiento Total</div>
                        <div class="metric-value {'positive' if metrics['total_return'] > 0 else 'negative'}">
                            {metrics['total_return']:.2%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Rendimiento Anualizado</div>
                        <div class="metric-value {'positive' if metrics['annualized_return'] > 0 else 'negative'}">
                            {metrics['annualized_return']:.2%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Volatilidad Anualizada</div>
                        <div class="metric-value neutral">
                            {metrics['volatility']:.2%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value {'positive' if metrics['sharpe_ratio'] > 1 else 'negative' if metrics['sharpe_ratio'] < 0 else 'neutral'}">
                            {metrics['sharpe_ratio']:.2f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas adicionales
                col5, col6, col7, col8 = st.columns(4)
                
                with col5:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Máxima Pérdida</div>
                        <div class="metric-value negative">
                            {metrics['max_drawdown']:.2%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col6:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Tasa de Éxito</div>
                        <div class="metric-value positive">
                            {metrics['win_rate']:.1%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col7:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Días Positivos</div>
                        <div class="metric-value positive">
                            {metrics['positive_days']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col8:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Total de Días</div>
                        <div class="metric-value neutral">
                            {metrics['total_days']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Métricas avanzadas
                st.header("🔬 Métricas Avanzadas")
                create_advanced_metrics(calculator, risk_free_rate)
                
                # Gráficos
                st.header("📊 Análisis Visual")
                
                # Gráfico de performance
                performance_chart = create_performance_chart(returns_df)
                if performance_chart:
                    st.plotly_chart(performance_chart, use_container_width=True)
                
                # Gráfico de distribución de rendimientos
                returns_dist = create_returns_distribution(returns_df)
                if returns_dist:
                    st.plotly_chart(returns_dist, use_container_width=True)
                
                # Análisis de atribución
                st.header("🎯 Análisis de Atribución")
                attribution_df = calculator.calculate_attribution_analysis()
                
                if not attribution_df.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Contribución por Activo")
                        st.dataframe(attribution_df, use_container_width=True)
                    
                    with col2:
                        # Gráfico de contribución
                        fig_attr = px.pie(
                            attribution_df, 
                            values='Contribucion', 
                            names='Activo',
                            title="Contribución al Rendimiento Total"
                        )
                        st.plotly_chart(fig_attr, use_container_width=True)
                
                # Resumen de performance mensual
                st.header("📅 Resumen Mensual")
                monthly_summary = calculator.get_performance_summary()
                
                if not monthly_summary.empty:
                    st.dataframe(monthly_summary, use_container_width=True)
                    
                    # Gráfico de rendimientos mensuales
                    fig_monthly = px.bar(
                        monthly_summary.reset_index(),
                        x='Fecha',
                        y='Retorno_Mensual',
                        title="Rendimientos Mensuales",
                        color='Retorno_Mensual',
                        color_continuous_scale=['red', 'yellow', 'green']
                    )
                    st.plotly_chart(fig_monthly, use_container_width=True)
                
                # Tabla de datos
                st.header("📋 Datos de Rendimientos")
                st.dataframe(returns_df.tail(10), use_container_width=True)
    
    else:
        # Mostrar información de ejemplo
        st.info("""
        ## 📋 Formato Esperado del Excel
        
        Tu archivo Excel debe contener dos hojas:
        
        ### Hoja "Operaciones"
        - **Fecha**: Fecha de la operación
        - **Tipo**: Compra, Venta, Cupón, Dividendo, Flujo
        - **Activo**: Nombre del activo
        - **Cantidad**: Cantidad de activos
        - **Precio**: Precio por unidad
        - **Monto**: Monto total de la operación
        
        ### Hoja "Precios"
        - **Fecha**: Fecha del precio
        - **Activo**: Nombre del activo
        - **Precio**: Precio de cierre
        """)
        
        # Mostrar ejemplo de datos
        st.subheader("📊 Ejemplo de Datos")
        
        # Ejemplo de operaciones
        st.write("**Operaciones de Ejemplo:**")
        ejemplo_operaciones = pd.DataFrame({
            'Fecha': ['2024-01-01', '2024-01-15', '2024-02-01'],
            'Tipo': ['Compra', 'Cupón', 'Venta'],
            'Activo': ['BONO_GD30', 'BONO_GD30', 'BONO_GD30'],
            'Cantidad': [100, 0, 50],
            'Precio': [95.50, 0, 96.20],
            'Monto': [9550, 250, 4810]
        })
        st.dataframe(ejemplo_operaciones)
        
        # Ejemplo de precios
        st.write("**Precios de Ejemplo:**")
        ejemplo_precios = pd.DataFrame({
            'Fecha': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'Activo': ['BONO_GD30', 'BONO_GD30', 'BONO_GD30'],
            'Precio': [95.50, 95.80, 96.10]
        })
        st.dataframe(ejemplo_precios)

if __name__ == "__main__":
    main()
