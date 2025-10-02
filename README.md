# Portfolio Analyzer 📊

Una aplicación web profesional para analizar el rendimiento de carteras de inversión con métricas avanzadas y visualizaciones interactivas.

## 🚀 Características Principales

### 📈 Métricas de Performance
- **Rendimiento Total**: Retorno acumulado del período
- **Rendimiento Anualizado**: Tasa de retorno anualizada
- **Volatilidad**: Medida de riesgo (desviación estándar anualizada)
- **Sharpe Ratio**: Retorno ajustado por riesgo
- **Sortino Ratio**: Retorno ajustado por riesgo de caída
- **Calmar Ratio**: Retorno anualizado / Máxima pérdida
- **Máxima Pérdida (Drawdown)**: Mayor pérdida desde un pico
- **VaR 95%**: Value at Risk al 95% de confianza
- **CVaR 95%**: Conditional Value at Risk al 95%
- **Tasa de Éxito**: Porcentaje de días con rendimiento positivo

### 📊 Visualizaciones Interactivas
- Gráfico de performance acumulada
- Distribución de rendimientos diarios
- Análisis de atribución por activo
- Rendimientos mensuales
- Contribución de cada activo al rendimiento total

### 🎯 Funcionalidades Avanzadas
- Carga de datos desde Excel
- Datos de ejemplo para testing
- Cálculo automático de métricas profesionales
- Análisis de atribución de rendimientos
- Resumen de performance mensual
- Exportación de resultados

## 🛠️ Instalación

### Opción 1: Ejecución Directa
```bash
# Clonar o descargar el proyecto
cd portfolio-analyzer

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la aplicación
streamlit run app.py
```

### Opción 2: Usando el Script de Ejecución
```bash
# Ejecutar el script automático
python run.py
```

## 📋 Formato de Datos

### Hoja "Operaciones"
| Fecha | Tipo | Activo | Cantidad | Precio | Monto |
|-------|------|--------|----------|--------|-------|
| 2024-01-01 | Compra | BONO_GD30 | 100 | 95.50 | 9550 |
| 2024-01-15 | Cupón | BONO_GD30 | 0 | 0 | 250 |
| 2024-02-01 | Venta | BONO_GD30 | 50 | 96.20 | 4810 |
| 2024-03-01 | Dividendo | ACCION_YPF | 0 | 0 | 500 |
| 2024-04-01 | Flujo | - | 0 | 0 | 10000 |

### Hoja "Precios"
| Fecha | Activo | Precio |
|-------|--------|--------|
| 2024-01-01 | BONO_GD30 | 95.50 |
| 2024-01-02 | BONO_GD30 | 95.80 |
| 2024-01-03 | BONO_GD30 | 96.10 |
| 2024-01-01 | ACCION_YPF | 8500.00 |
| 2024-01-02 | ACCION_YPF | 8520.00 |

## 🎮 Uso

1. **Carga de Datos**: 
   - Sube tu archivo Excel con las hojas "Operaciones" y "Precios"
   - O usa el botón "Usar Datos de Ejemplo" para testing

2. **Configuración**: 
   - Ajusta la tasa libre de riesgo en el sidebar
   - Selecciona el período de análisis

3. **Análisis**: 
   - Visualiza las métricas de performance
   - Explora los gráficos interactivos
   - Analiza la contribución de cada activo

4. **Exportación**: 
   - Descarga los resultados para análisis adicional

## 📊 Métricas Explicadas

### Rendimiento Total
El retorno acumulado desde el inicio del período hasta la fecha actual.

### Rendimiento Anualizado
La tasa de retorno anual que habría generado el mismo retorno total.

### Volatilidad
La desviación estándar de los rendimientos diarios, anualizada. Mide la variabilidad de los retornos.

### Sharpe Ratio
Mide el retorno excedente por unidad de riesgo. Valores > 1 son considerados buenos.

### Sortino Ratio
Similar al Sharpe Ratio, pero solo considera la volatilidad de los rendimientos negativos.

### Calmar Ratio
Relación entre el rendimiento anualizado y la máxima pérdida. Valores > 1 indican buen rendimiento ajustado por riesgo.

### VaR (Value at Risk)
La pérdida máxima esperada con un 95% de confianza en un día típico.

### CVaR (Conditional Value at Risk)
La pérdida promedio en el peor 5% de los casos.

## 🔧 Estructura del Proyecto

```
portfolio-analyzer/
├── app.py                    # Aplicación principal Streamlit
├── portfolio_calculator.py   # Módulo de cálculos avanzados
├── example_data.py          # Generador de datos de ejemplo
├── requirements.txt         # Dependencias del proyecto
├── run.py                   # Script de ejecución automática
└── README.md               # Documentación
```

## 🧪 Testing

Para probar la aplicación con datos de ejemplo:

```python
from example_data import generate_sample_data

# Generar datos de ejemplo
operaciones, precios = generate_sample_data()

# Guardar en Excel
from example_data import save_sample_data
save_sample_data("mi_cartera_ejemplo.xlsx")
```

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Si tienes problemas o preguntas:

1. Revisa la documentación
2. Busca en los issues existentes
3. Crea un nuevo issue con detalles del problema

## 🎯 Roadmap

- [ ] Integración con APIs de datos financieros
- [ ] Análisis de correlación entre activos
- [ ] Optimización de cartera
- [ ] Backtesting de estrategias
- [ ] Alertas de riesgo
- [ ] Exportación a PDF/Excel
- [ ] Dashboard en tiempo real
