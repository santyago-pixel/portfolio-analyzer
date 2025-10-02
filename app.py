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
            operaciones_mapped['Tipo'] = operaciones['Operacion']  # Compra/Venta/Cupón/Dividendo/Flujo
            operaciones_mapped['Activo'] = operaciones['Activo']
            operaciones_mapped['Cantidad'] = operaciones['Nominales']
            operaciones_mapped['Precio_Concertacion'] = operaciones['Precio']  # Precio de la transacción
            operaciones_mapped['Monto'] = operaciones['Valor']
            
            # Filtrar filas válidas (eliminar NaN)
            operaciones_mapped = operaciones_mapped.dropna()
            
            st.write("🔍 Operaciones cargadas:")
            st.write(operaciones_mapped.head(10))
            
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

def create_portfolio_composition(calculator: PortfolioCalculator):
    """Crear sección de composición de la cartera"""
    if calculator.portfolio_data is None:
        calculator.portfolio_data = calculator.calculate_portfolio_value()
    
    # Obtener activos únicos y filtrar NaN
    assets = calculator.operaciones['Activo'].unique()
    assets = [asset for asset in assets if pd.notna(asset)]  # Filtrar NaN
    
    composition_data = []
    
    for asset in assets:
        # Obtener operaciones del activo
        asset_ops = calculator.operaciones[calculator.operaciones['Activo'] == asset]
        
        # Debug: mostrar operaciones del activo
        st.write(f"🔍 Debug {asset}: {len(asset_ops)} operaciones")
        if not asset_ops.empty:
            st.write(asset_ops[['Tipo', 'Cantidad', 'Precio_Concertacion', 'Monto']])
            
            # Debug: mostrar cálculos paso a paso
            st.write(f"🔍 Cálculos para {asset}:")
        
        # Calcular posición actual y precio promedio ponderado
        total_invested = 0
        total_quantity = 0
        weighted_price_sum = 0  # Para calcular precio promedio ponderado
        
        for _, op in asset_ops.iterrows():
            if op['Tipo'] == 'Compra':
                total_invested += op['Monto']
                total_quantity += op['Cantidad']
                # Acumular para precio promedio ponderado
                weighted_price_sum += op['Cantidad'] * op['Precio_Concertacion']
            elif op['Tipo'] == 'Venta':
                # Para ventas, reducimos cantidad pero mantenemos el precio promedio
                total_quantity -= op['Cantidad']
                # No afectamos weighted_price_sum para mantener precio promedio de compras
        
        # Debug: mostrar resultados de cálculos
        st.write(f"  - Total invertido: {total_invested}")
        st.write(f"  - Cantidad total: {total_quantity}")
        st.write(f"  - Suma ponderada: {weighted_price_sum}")
        
        # Mostrar todos los activos que han tenido operaciones
        if total_invested != 0 or total_quantity != 0:  # Mostrar si hay inversión o cantidad
            # Calcular precio promedio ponderado
            if total_quantity > 0:
                avg_price = weighted_price_sum / total_quantity
            else:
                avg_price = 0
                
            st.write(f"  - Precio promedio: {avg_price}")
            st.write(f"  - ✅ Incluido en composición")
        else:
            st.write(f"  - ❌ NO incluido en composición")
            
            # Obtener precio actual
            asset_prices = calculator.precios[calculator.precios['Activo'] == asset]
            if not asset_prices.empty and len(asset_prices) > 0:
                current_price = asset_prices['Precio'].iloc[-1]
                current_value = total_quantity * current_price
                
                # Calcular peso en la cartera
                portfolio_value = calculator.portfolio_data['Valor_Cartera'].iloc[-1] if not calculator.portfolio_data.empty and len(calculator.portfolio_data) > 0 else 1
                weight = current_value / portfolio_value if portfolio_value > 0 else 0
                
                # Calcular ganancia/pérdida
                gain_loss = current_value - total_invested
                gain_loss_pct = gain_loss / total_invested if total_invested > 0 else 0
                
                composition_data.append({
                    'Activo': asset,
                    'Cantidad': f"{total_quantity:,.0f}",
                    'Precio_Promedio': f"${avg_price:,.2f}" if avg_price > 0 else "N/A",
                    'Precio_Actual': f"${current_price:,.2f}",
                    'Valor_Actual': f"${current_value:,.2f}",
                    'Inversion_Total': f"${total_invested:,.2f}",
                    'Ganancia_Perdida': f"${gain_loss:,.2f}",
                    'Ganancia_Perdida_%': f"{gain_loss_pct:.2%}",
                    'Peso_Cartera': f"{weight:.2%}"
                })
            else:
                # Si no hay datos de precios, mostrar solo la información básica
                composition_data.append({
                    'Activo': asset,
                    'Cantidad': f"{total_quantity:,.0f}",
                    'Precio_Promedio': f"${avg_price:,.2f}" if avg_price > 0 else "N/A",
                    'Precio_Actual': "N/A",
                    'Valor_Actual': f"${0:,.2f}",
                    'Inversion_Total': f"${total_invested:,.2f}",
                    'Ganancia_Perdida': f"${-total_invested:,.2f}",
                    'Ganancia_Perdida_%': "-100.00%",
                    'Peso_Cartera': "0.00%"
                })
    
    if composition_data:
        composition_df = pd.DataFrame(composition_data)
        
        st.subheader("📋 Composición de la Cartera")
        
        # Mostrar resumen
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_assets = len(composition_df)
            st.metric("Total de Activos", total_assets)
        
        with col2:
            total_invested = sum([float(x.replace('$', '').replace(',', '')) for x in composition_df['Inversion_Total']])
            st.metric("Inversión Total", f"${total_invested:,.2f}")
        
        with col3:
            total_current = sum([float(x.replace('$', '').replace(',', '')) for x in composition_df['Valor_Actual']])
            st.metric("Valor Actual", f"${total_current:,.2f}")
        
        # Tabla detallada
        st.dataframe(
            composition_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Activo": st.column_config.TextColumn("Activo", width="medium"),
                "Cantidad": st.column_config.TextColumn("Cantidad", width="small"),
                "Precio_Promedio": st.column_config.TextColumn("Precio Promedio", width="medium"),
                "Precio_Actual": st.column_config.TextColumn("Precio Actual", width="medium"),
                "Valor_Actual": st.column_config.TextColumn("Valor Actual", width="medium"),
                "Inversion_Total": st.column_config.TextColumn("Inversión Total", width="medium"),
                "Ganancia_Perdida": st.column_config.TextColumn("Ganancia/Pérdida", width="medium"),
                "Ganancia_Perdida_%": st.column_config.TextColumn("Ganancia/Pérdida %", width="medium"),
                "Peso_Cartera": st.column_config.TextColumn("Peso en Cartera", width="medium")
            }
        )
        
        return composition_df
    
    return pd.DataFrame()

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
                
                # Composición de la cartera
                st.header("📋 Composición de la Cartera")
                composition_df = create_portfolio_composition(calculator)
                
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
                
                # Rendimiento Individual de Activos
                st.header("📈 Rendimiento Individual por Activo")
                
                # Estadísticas resumidas por activo
                asset_stats = calculator.get_asset_summary_stats()
                if not asset_stats.empty:
                    st.subheader("📊 Estadísticas por Activo")
                    
                    # Formatear las columnas para mejor visualización
                    asset_stats_display = asset_stats.copy()
                    percentage_cols = ['Rendimiento_Total', 'Rendimiento_Anualizado', 'Volatilidad_Anualizada', 
                                     'Sharpe_Ratio', 'Rendimiento_Maximo', 'Rendimiento_Minimo']
                    
                    for col in percentage_cols:
                        if col in asset_stats_display.columns:
                            if col == 'Sharpe_Ratio':
                                asset_stats_display[col] = asset_stats_display[col].apply(lambda x: f"{x:.3f}")
                            else:
                                asset_stats_display[col] = asset_stats_display[col].apply(lambda x: f"{x:.2%}")
                    
                    # Formatear precios
                    price_cols = ['Precio_Inicial', 'Precio_Final', 'Precio_Maximo', 'Precio_Minimo']
                    for col in price_cols:
                        if col in asset_stats_display.columns:
                            asset_stats_display[col] = asset_stats_display[col].apply(lambda x: f"${x:,.2f}")
                    
                    st.dataframe(asset_stats_display, use_container_width=True)
                    
                    # Gráfico de rendimientos por activo
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig_returns = px.bar(
                            asset_stats,
                            x='Activo',
                            y='Rendimiento_Total',
                            title="Rendimiento Total por Activo",
                            color='Rendimiento_Total',
                            color_continuous_scale=['red', 'yellow', 'green']
                        )
                        fig_returns.update_layout(yaxis_tickformat='.1%')
                        st.plotly_chart(fig_returns, use_container_width=True)
                    
                    with col2:
                        fig_sharpe = px.bar(
                            asset_stats,
                            x='Activo',
                            y='Sharpe_Ratio',
                            title="Sharpe Ratio por Activo",
                            color='Sharpe_Ratio',
                            color_continuous_scale=['red', 'yellow', 'green']
                        )
                        st.plotly_chart(fig_sharpe, use_container_width=True)
                
                # Performance histórica individual
                individual_performance = calculator.calculate_individual_asset_performance()
                if not individual_performance.empty:
                    st.subheader("📈 Evolución de Rendimientos Acumulados")
                    
                    fig_individual = px.line(
                        individual_performance,
                        x='Fecha',
                        y='Rendimiento_Acumulado',
                        color='Activo',
                        title="Rendimiento Acumulado por Activo",
                        labels={'Rendimiento_Acumulado': 'Rendimiento Acumulado'}
                    )
                    fig_individual.update_layout(yaxis_tickformat='.1%')
                    st.plotly_chart(fig_individual, use_container_width=True)
                    
                    # Comparación de precios
                    st.subheader("💰 Evolución de Precios")
                    fig_prices = px.line(
                        individual_performance,
                        x='Fecha',
                        y='Precio',
                        color='Activo',
                        title="Evolución de Precios por Activo",
                        labels={'Precio': 'Precio'}
                    )
                    st.plotly_chart(fig_prices, use_container_width=True)
                
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
