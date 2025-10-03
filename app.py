import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import warnings
import os
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
    # Intentar cargar automáticamente el archivo operaciones.xlsx
    default_file = "operaciones.xlsx"
    if os.path.exists(default_file):
        uploaded_file = default_file
    else:
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo Excel",
            type=['xlsx', 'xls'],
            help="El archivo debe contener dos hojas: 'Operaciones' y 'Precios'"
        )
    
    
    # Buscar archivo Excel automáticamente
    excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx')]
    if not uploaded_file and excel_files:
        # Si hay archivos Excel en el directorio, usar el primero
        excel_file = excel_files[0]
        uploaded_file = open(excel_file, 'rb')
    
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
            
            # Filtrar filas válidas (eliminar NaN pero mantener cupones que pueden tener NaN en cantidad/precio)
            # Primero convertir 'nan' strings a NaN reales
            operaciones_mapped['Tipo'] = operaciones_mapped['Tipo'].replace('nan', np.nan)
            
            # Para cupones y amortizaciones, llenar NaN en cantidad y precio con 0
            cupon_mask = operaciones_mapped['Tipo'].str.strip().str.lower().str.contains('cupon', na=False)
            amortization_mask = operaciones_mapped['Tipo'].str.strip().str.lower().str.contains('amortizacion', na=False)
            
            # Combinar máscaras para cupones y amortizaciones
            special_ops_mask = cupon_mask | amortization_mask
            
            operaciones_mapped.loc[special_ops_mask, 'Cantidad'] = operaciones_mapped.loc[special_ops_mask, 'Cantidad'].fillna(0)
            operaciones_mapped.loc[special_ops_mask, 'Precio_Concertacion'] = operaciones_mapped.loc[special_ops_mask, 'Precio_Concertacion'].fillna(0)
            
            # Ahora eliminar filas con NaN en columnas críticas
            operaciones_mapped = operaciones_mapped.dropna(subset=['Fecha', 'Tipo', 'Activo', 'Monto'])
            
            
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
        return operaciones, precios
    
    return None, None


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
        
        
        # Calcular posición actual y precio promedio ponderado
        total_invested = 0
        total_quantity = 0
        weighted_price_sum = 0  # Para calcular precio promedio ponderado
        
        for idx, op in asset_ops.iterrows():
            # Limpiar espacios en blanco del tipo de operación
            tipo_limpio = str(op['Tipo']).strip()
            
            if tipo_limpio == 'Compra':
                total_invested += op['Monto']
                total_quantity += op['Cantidad']
                # Acumular para precio promedio ponderado
                weighted_price_sum += op['Cantidad'] * op['Precio_Concertacion']
            elif tipo_limpio == 'Venta':
                # Para ventas, reducimos cantidad pero mantenemos el precio promedio
                total_quantity -= op['Cantidad']
                # No afectamos weighted_price_sum para mantener precio promedio de compras
        
        # Mostrar todos los activos que han tenido operaciones
        if total_invested != 0 or total_quantity != 0:  # Mostrar si hay inversión o cantidad
            # Calcular precio promedio ponderado
            if total_quantity > 0:
                avg_price = weighted_price_sum / total_quantity
            else:
                avg_price = 0
            
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
        
        st.header("Composición de la Cartera")
        
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
    st.title("Portfolio Analyzer")
    st.markdown("---")
    
    # Cargar datos automáticamente
    operaciones, precios = load_data()
    
    # Sidebar con configuración
    with st.sidebar:
        st.header("Configuración")
        
        # Período de análisis
        st.subheader("Período de Análisis")
        start_date = st.date_input("Fecha de Inicio", value=datetime.now() - timedelta(days=365))
        end_date = st.date_input("Fecha de Fin", value=datetime.now())
        
        # Mostrar información del período filtrado en el sidebar
        if operaciones is not None and precios is not None:
            # Filtrar operaciones por período seleccionado
            operaciones_period = operaciones[
                (operaciones['Fecha'] >= pd.to_datetime(start_date)) & 
                (operaciones['Fecha'] <= pd.to_datetime(end_date))
            ]
            
            # Crear calculador temporal para verificar activos
            calculator_temp = PortfolioCalculator(operaciones, precios, pd.to_datetime(start_date))
            initial_positions = calculator_temp._get_initial_positions(pd.to_datetime(start_date))
            has_assets_in_portfolio = any(pos['cantidad'] > 0 for pos in initial_positions.values())
            
            if not operaciones_period.empty:
                st.info(f"**Período:** {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')} ({len(operaciones_period)} operaciones)")
            elif has_assets_in_portfolio:
                st.info(f"**Período:** {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')} (sin operaciones, pero con activos en cartera)")
            else:
                st.warning(f"No hay operaciones ni activos en cartera en el período seleccionado")
    
    if operaciones is not None and precios is not None:
        # Convertir fechas a datetime si no lo están
        operaciones['Fecha'] = pd.to_datetime(operaciones['Fecha'])
        precios['Fecha'] = pd.to_datetime(precios['Fecha'])
        
        # Filtrar precios por período seleccionado (solo para visualización)
        precios_filtered = precios[
            (precios['Fecha'] >= pd.to_datetime(start_date)) & 
            (precios['Fecha'] <= pd.to_datetime(end_date))
        ]
        
        # Filtrar operaciones por período seleccionado (solo para visualización)
        operaciones_period = operaciones[
            (operaciones['Fecha'] >= pd.to_datetime(start_date)) & 
            (operaciones['Fecha'] <= pd.to_datetime(end_date))
        ]
        
        # Crear calculador de cartera con TODOS los datos y fecha de inicio
        calculator = PortfolioCalculator(operaciones, precios, pd.to_datetime(start_date))
        
        # Verificar si hay activos en cartera a la fecha de inicio
        initial_positions = calculator._get_initial_positions(pd.to_datetime(start_date))
        has_assets_in_portfolio = any(pos['cantidad'] > 0 for pos in initial_positions.values())
        
        # Verificar si hay datos para mostrar
        if operaciones_period.empty and not has_assets_in_portfolio:
            st.warning(f"No hay operaciones ni activos en cartera en el período seleccionado: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
            return
        
        # Calcular rendimientos diarios
        returns_df = calculator.calculate_daily_returns()
        
        if returns_df is not None:
            # Calcular métricas
            metrics = calculator.calculate_metrics(0.05)  # Tasa libre de riesgo fija del 5%
            
            if metrics is not None:
                # Mostrar métricas principales
                st.header("Métricas de Performance")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    # Calcular rendimiento total usando la misma fórmula que la última sección
                    if 'Rendimiento_Diario' in returns_df.columns:
                        cumulative_return = (1 + returns_df['Rendimiento_Diario']).prod() - 1
                    else:
                        cumulative_return = metrics['total_return'] # Fallback if no daily returns
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Rendimiento Total</div>
                        <div class="metric-value {'positive' if cumulative_return > 0 else 'negative'}">
                            {cumulative_return:.2%}
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
                        <div class="metric-label">Volatilidad</div>
                        <div class="metric-value">
                            {metrics['volatility']:.2%}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value {'positive' if metrics['sharpe_ratio'] > 0 else 'negative'}">
                            {metrics['sharpe_ratio']:.2f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
            
            # Análisis Visual
            st.header("Análisis Visual")
            
            # Gráfico de rendimientos acumulados
            fig_cumulative = px.line(
                returns_df, 
                x='Fecha', 
                y='Valor_Cartera',
                title="Evolución del Valor de la Cartera"
            )
            fig_cumulative.update_layout(template="plotly_white")
            st.plotly_chart(fig_cumulative, use_container_width=True)
            
            # Gráfico de rendimientos diarios
            fig_daily = px.line(
                returns_df, 
                x='Fecha', 
                y='Rendimiento_Diario',
                title="Rendimientos Diarios"
            )
            fig_daily.update_layout(template="plotly_white")
            st.plotly_chart(fig_daily, use_container_width=True)
            
            # Análisis de Atribución
            st.header("Análisis de Atribución")
            
            
            # Calcular análisis de atribución
            attribution = calculator.calculate_attribution_analysis()
            
            if not attribution.empty:
                # Gráfico de contribución por activo
                fig_attribution = px.bar(
                    attribution, 
                    x='Activo', 
                    y='Contribucion',
                    title="Contribución al Rendimiento por Activo"
                )
                fig_attribution.update_layout(template="plotly_white")
                st.plotly_chart(fig_attribution, use_container_width=True)
                
                # Tabla de atribución
                st.subheader("Contribución por Activo")
                
                # Formatear columnas
                attribution_display = attribution.copy()
                
                # Formatear porcentajes
                percentage_cols = ['Peso', 'Retorno_vs_Costo', 'Retorno_Total', 'Contribucion']
                for col in percentage_cols:
                    if col in attribution_display.columns:
                        attribution_display[col] = attribution_display[col].apply(lambda x: f"{x:.2%}")
                
                # Formatear precios
                price_cols = ['Valor_Actual', 'Precio_Promedio', 'Precio_Actual', 'Ganancias_Realizadas', 'Ingresos_Cupones_Dividendos', 'Amortizaciones', 'Ganancias_No_Realizadas', 'Inversion_Total']
                for col in price_cols:
                    if col in attribution_display.columns:
                        attribution_display[col] = attribution_display[col].apply(lambda x: f"${x:,.2f}")
                
                # Formatear cantidad
                if 'Cantidad' in attribution_display.columns:
                    attribution_display['Cantidad'] = attribution_display['Cantidad'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(attribution_display, use_container_width=True)
            
            # Rendimiento Individual de Activos
            st.header("Rendimiento Individual por Activo")
            
            # Estadísticas resumidas por activo (usando análisis de atribución corregido)
            asset_stats = calculator.calculate_attribution_analysis()
            if not asset_stats.empty:
                st.subheader("Estadísticas por Activo")
                
                # Formatear las columnas para mejor visualización
                asset_stats_display = asset_stats.copy()
                percentage_cols = ['Retorno_Total', 'Retorno_vs_Costo', 'Contribucion']
                
                for col in percentage_cols:
                    if col in asset_stats_display.columns:
                        asset_stats_display[col] = asset_stats_display[col].apply(lambda x: f"{x:.2%}")
                
                # Formatear precios
                    price_cols = ['Precio_Promedio', 'Precio_Actual', 'Valor_Actual', 'Ganancias_Realizadas', 'Ingresos_Cupones_Dividendos', 'Ganancias_No_Realizadas', 'Inversion_Total']
                for col in price_cols:
                    if col in asset_stats_display.columns:
                        asset_stats_display[col] = asset_stats_display[col].apply(lambda x: f"${x:,.2f}")
                
                # Formatear peso
                if 'Peso' in asset_stats_display.columns:
                    asset_stats_display['Peso'] = asset_stats_display['Peso'].apply(lambda x: f"{x:.1%}")
                
                # Formatear cantidad
                if 'Cantidad' in asset_stats_display.columns:
                    asset_stats_display['Cantidad'] = asset_stats_display['Cantidad'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(asset_stats_display, use_container_width=True)
                
                # Gráfico de rendimientos por activo
                col1, col2 = st.columns(2)
                
                with col1:
                    fig_returns = px.bar(
                        asset_stats,
                        x='Activo',
                        y='Retorno_Total',
                        title="Rendimiento Total por Activo",
                        color='Retorno_Total',
                        color_continuous_scale=['red', 'yellow', 'green']
                    )
                    fig_returns.update_layout(yaxis_tickformat='.1%')
                    st.plotly_chart(fig_returns, use_container_width=True)
                
                with col2:
                    fig_contribution = px.bar(
                        asset_stats,
                        x='Activo',
                        y='Contribucion',
                        title="Contribución al Portfolio por Activo",
                        color='Contribucion',
                        color_continuous_scale=['red', 'yellow', 'green']
                    )
                    fig_contribution.update_layout(yaxis_tickformat='.1%')
                    st.plotly_chart(fig_contribution, use_container_width=True)
            
            # Performance histórica individual
            individual_performance = calculator.calculate_asset_cumulative_returns()
            if not individual_performance.empty:
                st.subheader("Evolución de Rendimientos Acumulados")
                
                fig_individual = px.line(
                    individual_performance,
                    x='Fecha',
                    y='Rendimiento_Acumulado',
                    color='Activo',
                    title="Rendimiento Acumulado por Activo (Sin Flujos de Cash)",
                    labels={'Rendimiento_Acumulado': 'Rendimiento Acumulado'}
                )
                fig_individual.update_layout(yaxis_tickformat='.1%')
                st.plotly_chart(fig_individual, use_container_width=True)
            
            # Comparación de precios (usar función original que incluye precios)
            individual_prices = calculator.calculate_individual_asset_performance()
            if not individual_prices.empty:
                st.subheader("Evolución de Precios")
                fig_prices = px.line(
                    individual_prices,
                    x='Fecha',
                    y='Precio',
                    color='Activo',
                    title="Evolución de Precios por Activo",
                    labels={'Precio': 'Precio'}
                )
                st.plotly_chart(fig_prices, use_container_width=True)
            
            
            # Tabla de datos
            st.header("Datos de Rendimientos")
            
            if returns_df is not None and not returns_df.empty:
                # Formatear la tabla para mejor visualización
                display_df = returns_df.copy()
                
                # Calcular rendimiento acumulado
                if 'Rendimiento_Diario' in display_df.columns:
                    display_df['Rendimiento_Acumulado'] = (1 + display_df['Rendimiento_Diario']).cumprod() - 1
                
                # Formatear fechas
                if 'Fecha' in display_df.columns:
                    display_df['Fecha'] = pd.to_datetime(display_df['Fecha']).dt.strftime('%Y-%m-%d')
                
                # Formatear porcentajes
                percentage_cols = ['Rendimiento_Diario', 'Rendimiento_Acumulado']
                for col in percentage_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.2%}")
                
                # Formatear valores monetarios
                money_cols = ['Valor_Cartera', 'Valor_Inicial', 'Daily_Cash_Flow', 'Value_Without_Cash_Flow']
                for col in money_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}")
                
                st.dataframe(display_df, use_container_width=True)
                
                # Mostrar estadísticas resumidas
                st.subheader("Resumen de Rendimientos")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if 'Rendimiento_Diario' in returns_df.columns:
                        avg_return = returns_df['Rendimiento_Diario'].mean()
                        st.metric("Rendimiento Promedio Diario", f"{avg_return:.2%}")
                
                with col2:
                    if 'Rendimiento_Diario' in returns_df.columns:
                        volatility = returns_df['Rendimiento_Diario'].std()
                        st.metric("Volatilidad Diaria", f"{volatility:.2%}")
                
                with col3:
                    if 'Rendimiento_Diario' in returns_df.columns:
                        # Usar el mismo cálculo que la tabla para consistencia
                        cumulative_return = (1 + returns_df['Rendimiento_Diario']).prod() - 1
                        st.metric("Rendimiento Total", f"{cumulative_return:.2%}")
            else:
                st.warning("No hay datos de rendimientos disponibles.")
    
    else:
        # Mostrar información de ejemplo
        st.info("""
        ## Formato Esperado del Excel
        
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
        st.subheader("Ejemplo de Datos")
        
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
