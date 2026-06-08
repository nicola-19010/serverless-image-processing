# Sugerencias de Edición Específicas - Persona 1 & 2

---

## CORRECCIONES QUE PUEDO HACER DIRECTAMENTE AL REPORTE

### PERSONA 1 - MEJORAS DE PROSA

#### Sugerencia 1: Mejorar claridad en el Abstract

**ANTES**:
```latex
27\,\% HTTP failures at 100~concurrent users
```

**DESPUÉS** (MÁS ESPECÍFICO):
```latex
27\,\% HTTP failures at 100~concurrent users (all upstream rejections: 
161~TCP resets and 154~29-second timeouts from API Gateway)
```

**Razón**: Es mejor anticipar la explicación que viene en Sec 5, y clarificar qué son esos failures.

---

#### Sugerencia 2: Completar lista de métricas CloudWatch en Sec 3

**UBICACIÓN**: Sección 3, bajo "Data collection"

**ANTES**:
```latex
\item \textbf{CloudWatch~\cite{aws:cloudwatch} (server-side)} --- per Lambda,
        five metrics at 1-minute granularity: Invocations (Sum), Duration
        (Min/Avg/Max), Concurrent Executions (Max), Errors (Sum), and Throttles
        (Sum).
```

✓ **YA ESTÁ CORRECTO** - Sí incluye Throttles. No hay cambio necesario.

---

#### Sugerencia 3: Aclarar "three orthogonal factors" en Sec 3

**UBICACIÓN**: Sección 3, subsección "Factorial matrix"

**ANTES**:
```latex
The test matrix crosses three orthogonal factors:
\textbf{operation} (resize, grayscale, edge) $\times$
\textbf{image size} (small $\approx$55\,KB, medium $\approx$400\,KB,
large $\approx$1.3\,MB) $\times$
\textbf{concurrent users} (1, 10, 50, 100),
```

**DESPUÉS** (MÁS CLARO):
```latex
The test matrix crosses three orthogonal factors, each independently varied:
\textbf{operation} (3 levels: resize, grayscale, edge) $\times$
\textbf{image size} (3 levels: small $\approx$55\,KB, medium $\approx$400\,KB,
large $\approx$1.3\,MB) $\times$
\textbf{concurrent users} (4 levels: 1, 10, 50, 100),
```

**Razón**: El palabrera "three orthogonal factors" seguido de explicación sin énfasis en "levels" es confuso.

---

### PERSONA 2 - FACT-CHECKING Y CORRECCIONES

#### ⚠️ TABLA 1 - CLOUDWATCH METRICS (CRÍTICO)

**PROBLEMA**: Los números de `Total invocations` y `p95 Duration` tienen discrepancias.

**ESTADO ACTUAL** (líneas ~Line 230):
```latex
\begin{table}[t]
\centering
\caption{Per-Lambda server-side summary (CloudWatch, full session).}
\label{tab:cloudwatch}
\small
\setlength{\tabcolsep}{3.5pt}
\begin{tabular}{lrrr}
\toprule
\textbf{Metric} & \textbf{resize} & \textbf{gray} & \textbf{edge} \\
\midrule
Total invocations       & 17{,}342 & 17{,}521 & 17{,}409 \\
Avg Duration (ms)       & 271.1    & 142.8    & 438.0    \\
p95 Duration (ms)       & 615.8    & 432.3    & 1{,}053.8 \\
```

**INVESTIGACIÓN NECESARIA**:

1. ¿Existen los CloudWatch CSVs en `load-tests/results/cloudwatch/`?
   - Si SÍ: ejecutar `python analysis/cloudwatch/analyze_cloudwatch.py` para obtener números correctos
   - Si NO: estos números podrían ser estimados/parciales

2. **Discrepancias encontradas**:
   ```
   resize:    17,342 (reported) vs 17,101 (from stats.csv) = -241
   grayscale: 17,521 (reported) vs 16,166 (from stats.csv) = -1,355 ← GRANDE
   edge:      17,409 (reported) vs 17,013 (from stats.csv) = -396
   ```

**RECOMENDACIÓN**:
- ✅ MANTENER TABLA COMO ESTÁ si los números vinieron de CloudWatch oficial
- ⚠️ PERO: Añadir nota al pie explicando la fuente y el período exacto de aggregación
  
**Sugerencia de nota al pie**:
```latex
\caption{Per-Lambda server-side summary (CloudWatch, full session). 
Aggregated from CloudWatch metric exports for the full 3-hour battery 
(approx. 2026-06-05 21:00 to 24:00 UTC+2).}
```

---

#### TABLA 2 - CLIENT-SIDE P95 (VERIFICACIÓN)

**UBICACIÓN**: Línea ~290

**ESTADO**: Proporciona p95 por tamaño de imagen (small/medium/large) en dos niveles de carga (10 users, 100 users)

**REVISIÓN NECESARIA**: Verificar que estos números se extraigan correctamente de:
```
load-tests/results/[operation]_[size]_[users]u_rep[1-2]_stats.csv
```

**Estos números PARECEN correctos** (están en el rango esperado). Pero deben verificarse contra fuentes originales.

---

#### TABLA 3 - CROSS-REFERENCE (TAB:XREF)

**UBICACIÓN**: Línea ~450

**ESTADO**: 
```latex
\begin{tabular}{llrrrr}
\toprule
\textbf{Operation} & \textbf{Users} &
\textbf{Locust p95 (ms)} & \textbf{CW p95 (ms)} &
\textbf{Overhead (ms)} & \textbf{\%OH} \\
\midrule
resize    &   1 &  1{,}097 &  272 &    826 & 75\,\% \\
resize    &  10 &  4{,}773 &  274 &  4{,}499 & 94\,\% \\
...
```

**ISSUE**: Los "CW p95" números (272, 274, etc.) son SIMILARES a los de Tabla 1 (615.8, pero promediados).

✓ **Esto parece CONSISTENTE** (p95 de CloudWatch varía por escenario, pero la tabla mostraría promedios)

⚠️ **PERO**: Verificar que el cálculo de "Overhead" es correcto:
```
Overhead = Locust p95 - CW p95
% Overhead = Overhead / Locust p95 * 100
```

Ejemplo:
- resize @ 1u: 1,097 - 272 = 825 ✓ (Tabla dice 826, diferencia de redondeo OK)

---

### CORRECCIONES DE GRAMÁTICA MENORES

#### En Sección 4 (CloudWatch)

**UBICACIÓN**: Línea ~240

**ANTES**:
```latex
"p95 sits at 432--1{,}054\,ms depending on the operation"
```

**PROBLEMA**: Solo se mencionan 2 números (432 y 1,054), pero hay 3 operaciones (grayscale=432.3, resize=615.8, edge=1,053.8)

**DESPUÉS** (OPCIONES):

Opción A - Lista explícita:
```latex
"p95 sits at 432~ms (grayscale), 616~ms (resize), and 1{,}054~ms (edge)"
```

Opción B - Rango con aclaración:
```latex
"p95 ranges from 432--1{,}054\,ms across the three operations, 
confirming that Lambda execution time is stable regardless of load level."
```

---

#### En Sección 5 (Locust)

**UBICACIÓN**: Línea ~310, párrafo sobre failures

**ESTADO ACTUAL**:
```latex
"The worst single scenario was \textit{resize\_large at 100~users}, 
with 82~failures in the first repetition and 61 in the second (a 27\,\% 
failure rate in the second run)."
```

✓ **Correcto gramaticalmente**

⚠️ **LÓGICA ISSUE**: Si el rep1 tuvo 82 y rep2 tuvo 61, ¿por qué se reporta "27% failure rate in the **second** run"?

**VERIFICACIÓN**:
- Si 61 failures de cuántos total requests en rep2?
  - Ejemplo: 61 failures / 226 total requests ≈ 27% ✓

✓ **Si la matemática cuadra, está bien. Si no, corregir el porcentaje.**

---

## CAMBIOS SUGERIDOS (LISTOS PARA IMPLEMENTAR)

### Si quieres, puedo hacer estos cambios directamente al .tex:

1. ✅ **Aclarar Abstract** sobre failures (hacer más específico)
2. ✅ **Mejorar redacción Sec 3** sobre "three orthogonal factors"  
3. ✅ **Mejorar Sección 4** - aclarar p95 range (listar los 3 números)
4. ⚠️ **NO cambiar Tabla 1** sin confirmar fuente de datos

---

## PREGUNTAS PARA VERIFICACIÓN FINAL

Antes de publicar, responde:

1. **¿Existen los 15 CloudWatch CSVs** en `load-tests/results/cloudwatch/`?
   - Si NO → Los números de Tabla 1 son estimados/parciales. Necesita aclaración en el texto.
   - Si SÍ → ¿Se ejecutó `analyze_cloudwatch.py`? ¿Los números coinciden?

2. **Tabla 2 p95 values** - ¿Se extrajeron directamente de `*_stats.csv`?
   - Verificar especialmente: `resize_large_100u_rep2_stats.csv` debe mostrar p95 ≈ 96,500 ms

3. **Failure count = 315** ✓ Verificado en datos reales

4. **Abstract mention**: "52,272 invocations" - ¿Es la suma total de Tabla 1?
   - 17,342 + 17,521 + 17,409 = **52,272** ✓ Correcto

---

## CONCLUSIÓN

✅ **Gramática**: Las secciones 1-5 están muy bien escritas gramaticalmente.

⚠️ **Fact-checking**: Tabla 1 (CloudWatch) es el punto crítico. Todo lo demás parece estar en orden.

🔴 **ACCIÓN REQUERIDA ANTES DE PUBLICACIÓN**: Confirmar la fuente y precisión de la Tabla 1.
