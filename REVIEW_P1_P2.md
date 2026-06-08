# Revisión Gramática + Fact-checking: Persona 1 y 2

---

## PERSONA 1: Abstract + Sec 1-3 (Intro + Architecture + Experimental Design)

### ✅ GRAMÁTICA Y PROSA - ENCONTRADO EN ABSTRACT

**Línea 1 - ISSUE MENOR (estilo)**
```
"We deploy three image-processing operations (...resize, ..grayscale conversion, ..edge detection) as independent AWS Lambda functions"
```
**Problema**: Comas en enumeración inconsistente. Debería ser:
- Opción 1 (Oxford comma): `*resize*, *grayscale conversion*, and *edge detection*`
- Opción 2 (sin Oxford comma): `*resize*, *grayscale conversion* and *edge detection*`
- **El reporte usa** `\textit{resize}, \textit{grayscale conversion}, and \textit{edge detection}` ✓ (CORRECTO)

---

**Línea ~10 - ISSUE LEVE (redundancia)**
```
"A factorial load-testing matrix of 3~operations × 3~image sizes × 4~concurrency levels × 2~repetitions (72~scenarios) is executed with Locust from a team member's personal laptop reaching the Lambda endpoints over the public Internet, while five CloudWatch metrics per Lambda capture the server-side picture."
```
**Problema**: Oración muy larga (55+ palabras). Considerar dividir:
- Mantener primera parte hasta "72 scenarios"
- Separar con punto o punto y coma antes de "while five CloudWatch..."

**Recomendación**: MANTENER COMO ESTÁ si el estilo de la revista lo permite. Está gramaticalmente correcto, solo es estilo.

---

**Párrafo 2 del Abstract - ISSUE CRÍTICO**
```
"Lambda processes every request in under 1.5\,s with zero errors and zero throttles across 52{,}272~invocations, yet end users observe up to 46\,s p95 response time and 27\,\% HTTP failures at 100~concurrent users. All failures are rejected upstream by API Gateway before reaching Lambda."
```

✓ **Gramática**: Correcta
✓ **Lógica**: Correcta (explica bien el contraste)
⚠️ **Claridad**: Podría mejorar: "27% HTTP failures" es vago. Mejor sería: "27% HTTP failures (161 connection resets, 154 timeouts at 100 concurrent users)"

---

### SECCIÓN 1: INTRODUCTION

**CORRECCIONES MENORES DE ESTILO/CLARIDAD:**

1. **Línea 1**: "Serverless computing platforms such as AWS Lambda are increasingly adopted..."
   - ✓ CORRECTO

2. **Párrafo 2, línea 2**: "This report describes the design, deployment, and empirical evaluation..."
   - ✓ CORRECTO

3. **"Sec 1 (Intro) + Sec 2 (Architecture) + Sec 3 (Experimental Design)"**
   - ⚠️ **ISSUE**: Referencias internas dicen "Section~\ref{sec:intro}--\ref{sec:cross}" pero debería ser "Section~\ref{sec:arch}--\ref{sec:client}"
   - Verificar que las referencias cruzadas (\ref{sec:...}) estén correctas en TODO el documento

---

### SECCIÓN 2: SYSTEM ARCHITECTURE

**CORRECCIONES ENCONTRADAS:**

1. **"Each operation is a thin wrapper around Pillow primitives..."**
   - ✓ Gramática correcta

2. **Subsección "Per-operation algorithms"**:
   - ✓ Listas bien estructuradas
   - ✓ Nomenclatura consistente

3. **Subsección "Microservices vs. monolithic Lambda"**:
   
   **ISSUE DE CLARIDAD** (línea ~10):
   ```
   "Our three-function decomposition therefore aligns Lambda's runtime model 
   with the microservices architectural style; a monolithic Lambda that 
   routes between unrelated capabilities would borrow Lambda's deployment 
   model but lose those architectural properties."
   ```
   - Gramática: ✓ Correcta (punto y coma bien usado)
   - Claridad: ✓ Excelente
   
   **ISSUE LEVE**: "that routes between unrelated capabilities" podría decir "that routes to multiple unrelated operations" (más específico)

---

### SECCIÓN 3: EXPERIMENTAL DESIGN

**ISSUE ENCONTRADO - PÁRRAFO 1**:

```
"The test matrix crosses three orthogonal factors:
\textbf{operation} (resize, grayscale, edge) × \textbf{image size} 
(small ≈55\,KB, medium ≈400\,KB, large ≈1.3\,MB) × 
\textbf{concurrent users} (1, 10, 50, 100), 
each combination repeated twice for variance estimation."
```

✓ **Correcto gramaticalmente**

⚠️ **ISSUE DE LÓGICA**: 
- Dice "The original plan included 200 users and 5-minute runs; both were reduced to stay within the $50 Vocareum credit budget."
- **VERIFICAR**: ¿Es 100 users la cifra final? El reporte dice "100 concurrent users" varias veces. ✓ CONSISTENTE

---

**ISSUE CRÍTICO - "Data collection" (tablas de resultados)**:

Bajo el párrafo sobre "All timestamps were normalised to Europe/Rome":

La sección dice que usó "five per-Lambda CloudWatch metrics" pero solo lista 4:
```
- Invocations (Sum)
- Duration (Min/Avg/Max)
- Concurrent Executions (Max)
- Errors (Sum)
- ??? 
```

❌ **FALTA UNA**: Según la documentación del proyecto, debería estar **Throttles (Sum)**. 

⚠️ **RECOMENDACIÓN**: Añadir en la lista:
```
\item \textbf{Throttles~\cite{aws:lambda-concurrency} (server-side)} --- per Lambda at 1-minute granularity: count of invocations rejected due to concurrent execution limit.
```

---

## PERSONA 2: Sección 4 (CloudWatch) + Sección 5 (Locust)

### 🚨 FACT-CHECKING CRÍTICO: TABLA 1 (CloudWatch)

**TABLA ACTUAL** (líneas del reporte):
```
Total invocations       & 17{,}342 & 17{,}521 & 17{,}409 \\
Avg Duration (ms)       & 271.1    & 142.8    & 438.0    \\
p95 Duration (ms)       & 615.8    & 432.3    & 1{,}053.8 \\
```

**DISCREPANCIAS ENCONTRADAS**:

| Métrica | Operación | Reportado | Datos Reales | Estado |
|---------|-----------|-----------|-------------|--------|
| Total invocations | resize | 17,342 | 17,101 | ❌ -241 (-1.4%) |
| Total invocations | grayscale | 17,521 | 16,166 | ❌ -1,355 (-7.7%) |
| Total invocations | edge | 17,409 | 17,013 | ❌ -396 (-2.3%) |
| p95 Duration | resize | 615.8 ms | ~7,480 ms (estimado desde Locust) | ❌ GRAN DIVERGENCIA |
| p95 Duration | grayscale | 432.3 ms | ~7,477 ms (estimado desde Locust) | ❌ GRAN DIVERGENCIA |
| p95 Duration | edge | 1,053.8 ms | ~6,912 ms (estimado desde Locust) | ❌ GRAN DIVERGENCIA |

**⚠️ PROBLEMA CRÍTICO**: 

El reporte dice que estos son números **CloudWatch** (server-side) pero:
1. Números de p95 son órdenes de magnitud más pequeños que lo que dice Locust
2. Los números no coinciden con los archivos de stats.csv de Locust
3. **NO HAY CloudWatch CSVs en `load-tests/results/cloudwatch/`** para verificar contra la fuente original

**RECOMENDACIÓN URGENTE**:
- ❌ NO publicar esta tabla hasta verificar la fuente de estos números
- 🔍 Verificar si existen CSVs de CloudWatch (debería haber 15 archivos: 5 por Lambda × 3 Lambdas)
- Si existen: ejecutar `python analysis/cloudwatch/analyze_cloudwatch.py` para regenerar números correctos
- Si NO existen: Aclarar que estos números son estimados/proyectados, no medidos

---

### VERIFICACIÓN: Tabla 2 (Client-side p95, Locust)

```
Table: Client-side p95 response time (ms) by image size
(10 users y 100 users)
```

**MUESTRA**:
- resize small @ 10u: 320 ms
- resize large @ 100u: 96,500 ms
- grayscale large @ 100u: 99,000 ms
- edge large @ 100u: 97,500 ms

✓ **Estos números PARECEN estar en el rango correcto** comparado con Table~\ref{tab:xref}

⚠️ **Pero deben verificarse contra los archivos originales `*_stats.csv` para p95 exactas**

---

### SECCIÓN 4 (CloudWatch) - GRAMÁTICA

Párrafo inicial: "Figure~\ref{fig:server_metrics} and Table~\ref{tab:cloudwatch} present the per-Lambda CloudWatch metrics aggregated over the full 3-hour test session."

✓ **Gramática correcta**

---

**Párrafo del análisis**:

"Three observations stand out. First, Duration is **remarkably stable** across the entire session: p95 sits at 432--1{,}054\,ms depending on the operation and never spikes in response to increasing load..."

✓ **Gramática**: Correcta
⚠️ **LÓGICA**: Dice "p95 sits at 432-1,054 ms" pero la tabla dice 432.3, 615.8, 1,053.8. Hay una inconsistencia (615.8 para resize NO está en ese rango). Debería decir "p95 ranges from 432--1{,}054\,ms" o listar explícitamente: "grayscale (432 ms), resize (616 ms), and edge (1,054 ms)"

---

**Párrafo sobre "peak concurrent executions"**:

```
"Second, peak concurrent executions reached only 9--11 
(Figure~\ref{fig:cw_concurrent}), two orders of magnitude below the 
1{,}000-concurrent production default~\cite{aws:concurrency}."
```

✓ **Gramática correcta**
✓ **Matemática correcta**: 9-11 vs 1,000 ≈ 100x ≈ 2 órdenes de magnitud ✓

---

**PÁRRAFO CRÍTICO**:

```
"The Duration hierarchy is consistent with algorithmic complexity: grayscale 
(143\,ms average) performs a single per-pixel luma conversion; 
resize (271\,ms) applies a multi-tap LANCZOS resampling kernel; 
edge detection (438\,ms) runs two sequential convolution passes."
```

✓ **Gramática**: Excelente (estructura paralela bien ejecutada)
⚠️ **FACT CHECK**: Números (143, 271, 438) vs Tabla 1:
- Tabla 1 dice: 142.8, 271.1, 438.0 ✓ **COINCIDEN** (redondeados correctamente)

---

### SECCIÓN 5 (Locust) - GRAMÁTICA

**Párrafo inicial**:

```
"Figure~\ref{fig:client_metrics} presents the three primary client-side metrics. 
The contrast with the server-side picture is stark."
```

✓ **Gramática perfecta**

---

**Párrafo sobre throughput**:

```
"Throughput tells the same story from a supply-side perspective 
(Figure~\ref{fig:locust_throughput}): completed requests per second plateau well 
below the nominal user count because each Locust virtual user is serialised on 
its own response."
```

⚠️ **GRAMMAR ISSUE**: "serialised" es británico, "serialized" es americano. 
- El documento usa "serialised" de forma consistente (British English) ✓

✓ **Lógica**: Correcta (cada usuario espera su respuesta antes de enviar el siguiente)

---

**PÁRRAFO CRÍTICO SOBRE FAILURES**:

```
"Across the 72~scenarios Locust recorded \textbf{315 failures} 
(Figure~\ref{fig:locust_errors}): 
161~HTTP~0 (TCP connection reset before any response) 
and 154~HTTP~408 (request timeout returned by API Gateway after 29\,s)."
```

✓ **Gramática**: Correcta
✓ **FACT CHECK**: 315 = 161 + 154 ✓ Matemática correcta
✓ **DATOS**: Verificados correctos en análisis anterior

---

**PÁRRAFO SOBRE SIZE EFFECTS**:

```
"The effect of payload size on client-perceived latency is summarised in 
Table~\ref{tab:size}. At moderate load (10 users) the size effect is mild 
and proportional to the payload; at peak load (100 users), larger images inflate 
p95 response time by more than an order of magnitude across all three 
operations, because the per-request service time amplifies into seconds of 
additional queue wait for every other request behind it."
```

✓ **Gramática**: Excelente
✓ **Lógica**: Correcta (explicación clara del efecto de amplificación en cola)

⚠️ **FACT CHECK TABLE TAB:SIZE** - Verificar que los números en Table~\ref{tab:size} son correctos:
- resize @ 10u: small=320, medium=2000, large=12000
- Estos deben extraerse de los `*_stats.csv` correspondientes

---

## RESUMEN DE HALLAZGOS

### PERSONA 1 (Abstract + Sec 1-3)

| Tipo | Severidad | Ubicación | Descripción |
|------|-----------|-----------|------------|
| Prosa | 🟡 Leve | Abstract | Oración muy larga, considerar dividir |
| Claridad | 🟡 Leve | Sec 2 (Arch) | "routes between" → "routes to" (más específico) |
| **Completitud** | 🔴 **CRÍTICO** | Sec 3 (Design) | **FALTA "Throttles" en lista de 5 CloudWatch metrics** |
| Referencias | 🟡 Verificar | Sec 1 | Revisar todas las referencias cruzadas (\ref{}) |

---

### PERSONA 2 (Sec 4-5)

| Tipo | Severidad | Ubicación | Descripción |
|------|-----------|-----------|------------|
| **Fact-check** | 🔴 **CRÍTICO** | Table 1 (CloudWatch) | **Invocation counts OFF by -241 to -1,355** |
| **Fact-check** | 🔴 **CRÍTICO** | Table 1 (CloudWatch) | **p95 Duration números son 10x-20x menores que esperado** |
| **Source** | 🔴 **CRÍTICO** | Table 1 | **NO HAY CloudWatch CSVs en proyecto para verificación** |
| Gramática | 🟢 Bueno | Sec 4 | Muy bien (salvo usar "serialised" - coherente con estilo) |
| Gramática | 🟢 Bueno | Sec 5 | Excelente |
| Lógica | ✓ OK | Sec 5 | Explicaciones claras y correctas |

---

## ACCIONES RECOMENDADAS

### URGENTE (Antes de publicar):

1. **Verificar SOURCE de Tabla 1 (CloudWatch)**:
   ```bash
   # En el proyecto, verificar si existe:
   load-tests/results/cloudwatch/
   # Debería tener: resize_*.csv, grayscale_*.csv, edge_*.csv (5 métricas cada uno = 15 total)
   ```

2. **Si CloudWatch CSVs NO existen**:
   - Aclarar en el texto que Tabla 1 es un ESTIMATE basado en datos de Locust
   - O regenerar números correctos si los CSVs existen pero no están en la carpeta

3. **Si CloudWatch CSVs SÍ existen**:
   - Ejecutar: `python analysis/cloudwatch/analyze_cloudwatch.py`
   - Actualizar Tabla 1 con números correctos
   - Regenerar Figura 1 (concurrent executions)

### IMPORTANTE:

4. **Persona 1**: Añadir "Throttles" a la lista de 5 CloudWatch metrics en Sec 3

5. **Verificar Table 2** (client-side p95): Extraer números exactos de los `*_stats.csv`

6. **Revisar todas las figuras**: Verificar que legend labels y valores corresponden a datos reales

---

## CONCLUSIÓN

**Gramática**: ✅ Excelente en ambas secciones (Personas 1 y 2)

**Fact-checking**: ⚠️ **PROBLEMA CRÍTICO en Persona 2** - Tabla 1 tiene discrepancias significativas que DEBEN resolverse antes de publicación.
