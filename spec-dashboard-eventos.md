# Spec — Dashboard de reacciones sectoriales a eventos políticos y económicos

> Nombre del proyecto: **[POR DEFINIR]** · Web en inglés · Hosting: GitHub Pages + GitHub Actions
> Objetivo de entrega del MVP: **antes del 15 de diciembre de 2026**

---

## 1. Qué es

Una web de una sola página que muestra **cómo reaccionaron 8 sectores en 3 mercados (EE.UU., Europa, China)** a eventos políticos, comerciales, geopolíticos, monetarios y crisis económicas, desde el año más antiguo con datos disponibles.

La web es simple a propósito. La profundidad está en la metodología (footer), no en la interfaz.

**Fuera del alcance:** cuentas de usuario, backend, datos en tiempo real, sección "About".

---

## 2. Datos de mercado

### 2.1 Fuente
- **Yahoo Finance vía `yfinance`**, descarga con `period="max"`.
- Precios ajustados (`auto_adjust=True`), para que dividendos y splits no distorsionen los retornos.
- Retornos en **moneda local** (cada serie se compara contra su propio mercado, así que no hace falta convertir divisas).
- La web **nunca** llama a Yahoo: los datos se descargan en un batch diario y se guardan como JSON.

### 2.2 Sectores y tickers (8 sectores × 3 mercados = 24 series)

| Sector | 🇺🇸 USA | 🇪🇺 Europa | 🇨🇳 China |
|---|---|---|---|
| Tech | XLK | EXV3.DE | Canasta: 0700.HK, 9988.HK, 3690.HK, 1810.HK, **0992.HK** (Lenovo) |
| Energy (Oil & Gas) | XLE | EXH1.DE | Canasta: 0857.HK, 0883.HK, 0386.HK |
| Industrials | XLI | EXH4.DE | Canasta: 1766.HK, 0390.HK, 1800.HK |
| Auto | Canasta: TSLA, GM, F | EXV5.DE | Canasta: 1211.HK, 0175.HK, 2015.HK, 9868.HK, **0489.HK** (Dongfeng) |
| Banks | XLF ¹ | EXV1.DE | Canasta: 1398.HK, 0939.HK, 3988.HK, 1288.HK |
| Consumer Staples | XLP | EXH3.DE | Canasta: 0291.HK, 0322.HK, 2319.HK, 1876.HK |
| Defense | ITA | Canasta: RHM.DE, BA.L, LDO.MI, SAF.PA, HO.PA | Canasta A-shares: 600760.SS, 600893.SS, 600150.SS, 000768.SZ ² |
| Metals & Mining | XME | EXV6.DE | Canasta: 2899.HK, 3993.HK, 2600.HK, 0358.HK, **600111.SS** (tierras raras) |
| **Benchmark** | **SPY** | **EXSA.DE** | **^HSI** (Defense China: **000300.SS**) |

¹ XLF es "Financials", no solo bancos. Se usa porque tiene historia desde 1998 (KBE recién desde 2005). Va indicado en la metodología.
² La defensa china casi no cotiza en Hong Kong. Esa fila se compara contra el CSI 300.

**Tarea antes de construir:** verificar cada ticker en Yahoo (los sufijos cambian a veces) y registrar la primera fecha con datos.

### 2.3 Canastas dinámicas
- Las canastas son **equal-weighted**: el retorno diario es el promedio de los retornos de las empresas que **ya cotizaban ese día**.
- **Mínimo 2 empresas** con datos. Si no se llega, la celda sale gris ("insufficient data").
- Las canastas se rebalancean a diario (promedio simple de retornos diarios).

### 2.4 Cobertura esperada
- **1998–2005:** EE.UU. completo; Europa desde ~2001; China casi todo en gris.
- **2006 en adelante:** cobertura casi completa.
- **2019 en adelante:** cobertura total.

---

## 3. Modelo de eventos

### 3.1 Unidad
**La unidad es el evento.** Cada columna del heatmap es un evento. Las noticias son contexto que se ve al abrir el evento; no son columnas propias.

```
Evento (columna)
 ├─ reacción por sector y mercado (2 modos × 3 horizontes)
 ├─ contexto: resumen con IA de lo que decía la prensa en las semanas previas
 ├─ 3–5 titulares (NYT / Guardian) como links
 └─ análisis con IA de la reacción + disclaimer
```

### 3.2 Categorías
1. **Elections**
2. **Trade**
3. **Geopolitics**
4. **Central Banks**
5. **Crises & Bubbles**: los hitos de los episodios y las crisis sueltas

### 3.3 Episodios (bandas)
- Un episodio es una **etiqueta de grupo** con nombre, fecha de inicio y fecha de fin (o `in_progress`).
- En el heatmap se dibuja como **una banda encima de las columnas** de sus eventos:

```
              |  ── Global Financial Crisis ── |        |  ──── COVID-19 ──── |
              | BNP 07 | Bear 08 | Lehman 08   | Brexit | Wuhan | Italy | WHO |
Tech      US  |   ▓▓   |   ░░    |    ██       |   ░░   |  ░░   |  ▓▓   | ██  |
          EU  |   ...
```

- Un evento tiene **una categoría** y un **`episode_id` opcional**.
- La banda agrupa solo los eventos con su `episode_id`. Si cae un evento ajeno en medio (por ejemplo, una elección), la banda se corta en esa columna.
- **Al hacer clic en la banda** se abre la vista larga del episodio: la línea de tiempo con los 8 sectores, los hitos marcados y el **drawdown máximo por sector** (de pico a mínimo dentro del episodio).

### 3.4 Regla del día del evento (husos horarios)
Cada evento se guarda con `announced_at_utc`. Para cada mercado:
- **Precio base (t−1):** el último cierre **antes** del anuncio.
- **Día 0:** la sesión en curso si el mercado estaba abierto en el momento del anuncio; si no, la primera sesión que abre después.

Ejemplos:
- **9/11:** Europa estaba abierta, así que el día 0 europeo es el 11-sep. En EE.UU. el día 0 es el 17-sep, cuando reabrió.
- **Anuncio después del cierre de EE.UU.:** el día 0 es el día siguiente para los tres mercados.
- **Anuncio en fin de semana:** el día 0 es el lunes.

---

## 4. Lista de eventos (v1)

> **Todas las fechas deben verificarse contra una fuente primaria antes de publicar** (fase de verificación, sección 11). Las marcadas con ⚠ son las que más necesitan revisión.
> Notas de timing: **WE** = fin de semana · **AC** = después del cierre de EE.UU. · **ID** = durante el día.

### 4.1 Episodios

| `episode_id` | Nombre | Inicio | Fin |
|---|---|---|---|
| `dotcom` | Dot-com Bubble | 1999-01-01 | 2002-10-09 |
| `gfc` | Global Financial Crisis | 2007-02-27 | 2009-03-09 |
| `euro_crisis` | Euro Debt Crisis | 2009-10-20 | 2012-09-06 |
| `china_2015` | China Stock Market Crash | 2015-06-12 | 2016-02-29 |
| `covid` | COVID-19 | 2019-12-31 | 2020-11-09 |
| `inflation` | Inflation & Rate Shock | 2021-05-12 | 2022-12-31 |
| `ai_boom` | AI Boom | 2022-11-30 | *in progress* |

### 4.2 Hitos de los episodios (categoría Crises & Bubbles, salvo que se indique otra)

| Fecha | Evento | Episodio | Categoría | Timing |
|---|---|---|---|---|
| 2000-03-10 | Nasdaq peaks | dotcom | Crises | ID |
| 2000-03-20 | Barron's "Burning Up" on dot-com cash burn | dotcom | Crises | WE (edición del lunes) |
| 2000-04-14 | Nasdaq falls ~10% in a day | dotcom | Crises | ID |
| 2001-01-03 | Fed surprise inter-meeting rate cut | dotcom | Central Banks | ID |
| 2001-12-02 | Enron files for bankruptcy | dotcom | Crises | WE |
| 2002-06-25 | WorldCom accounting fraud disclosed | dotcom | Crises | AC |
| 2002-07-30 | Sarbanes-Oxley Act signed | dotcom | Crises | ID |
| 2002-10-09 | Nasdaq bottoms | dotcom | Crises | ID |
| 2007-02-27 | Shanghai sell-off spreads globally | gfc | Crises | ID |
| 2007-08-09 | BNP Paribas freezes three funds | gfc | Crises | ID |
| 2008-03-16 | Bear Stearns rescued by JPMorgan | gfc | Crises | WE |
| 2008-09-07 | Fannie Mae & Freddie Mac taken over | gfc | Crises | WE |
| 2008-09-15 | Lehman Brothers bankruptcy | gfc | Crises | WE/pre-market |
| 2008-09-29 | US House rejects TARP | gfc | Crises | ID |
| 2008-11-09 | China announces 4-trillion-yuan stimulus | gfc | Central Banks | WE |
| 2008-11-25 | Fed announces QE1 | gfc | Central Banks | ID |
| 2009-03-09 | Global equities bottom | gfc | Crises | ID |
| 2009-10-20 ⚠ | Greece revises its deficit sharply upward | euro_crisis | Crises | ID |
| 2010-05-02 | First Greek bailout agreed | euro_crisis | Crises | WE |
| 2011-08-05 | S&P downgrades US credit rating | euro_crisis | Crises | AC |
| 2012-07-26 | Draghi: "whatever it takes" | euro_crisis | Central Banks | ID |
| 2012-09-06 | ECB announces OMT | euro_crisis | Central Banks | ID |
| 2015-06-12 | Shanghai Composite peaks | china_2015 | Crises | ID |
| 2015-07-27 | Shanghai falls ~8.5% | china_2015 | Crises | ID |
| 2015-08-11 | PBoC devalues the yuan | china_2015 | Central Banks | ID |
| 2015-08-24 | "Black Monday": China-led global sell-off | china_2015 | Crises | ID |
| 2016-01-07 | China suspends circuit breaker after second halt | china_2015 | Crises | ID |
| 2019-12-31 | Wuhan reports pneumonia cluster to WHO | covid | Crises | ID |
| 2020-01-23 | Wuhan lockdown | covid | Crises | ID |
| 2020-02-23 | Italy quarantines northern towns | covid | Crises | WE |
| 2020-03-11 | WHO declares a pandemic | covid | Crises | ID |
| 2020-03-15 | Fed cuts rates to zero | covid | Central Banks | WE |
| 2020-03-23 | Fed announces unlimited QE; market bottom | covid | Central Banks | pre-market |
| 2020-11-09 | Pfizer announces vaccine efficacy | covid | Crises | pre-market |
| 2021-05-12 | US CPI jumps to 4.2% | inflation | Crises | pre-market |
| 2021-11-30 | Powell retires "transitory" | inflation | Central Banks | ID |
| 2022-03-16 | Fed's first hike of the cycle | inflation | Central Banks | ID |
| 2022-06-15 | Fed hikes 75 bp | inflation | Central Banks | ID |
| 2022-07-21 | ECB's first hike in 11 years | inflation | Central Banks | ID |
| 2022-09-23 | UK "mini-budget" gilt crisis | inflation | Crises | ID |
| 2022-11-30 | ChatGPT launches | ai_boom | Crises | ID |
| 2023-05-24 | Nvidia's guidance blowout | ai_boom | Crises | AC |
| 2023-10-17 | US expands chip export controls | ai_boom | Trade | ID |
| 2024-06-18 | Nvidia becomes the world's most valuable company | ai_boom | Crises | ID |
| 2025-01-27 | DeepSeek sell-off | ai_boom | Crises | WE (reacción el lunes) |
| 2025-10-29 ⚠ | Nvidia reaches a $5T market cap | ai_boom | Crises | ID |

### 4.3 Eventos sueltos (sin episodio)

| Fecha | Evento | Categoría | Timing |
|---|---|---|---|
| 2000-11-07 | US presidential election (Bush v. Gore, disputed) | Elections | AC |
| 2001-09-11 | 9/11 attacks | Geopolitics | ID (EE.UU. cerrado hasta el 17-sep) |
| 2001-12-11 | China joins the WTO | Trade | ID |
| 2003-03-20 | US invades Iraq | Geopolitics | ID |
| 2008-11-04 | US presidential election (Obama) | Elections | AC |
| 2013-05-22 | Taper tantrum (Bernanke testimony) | Central Banks | ID |
| 2014-03-01 | Russia authorizes force in Crimea | Geopolitics | WE |
| 2014-06-05 | ECB introduces negative rates | Central Banks | ID |
| 2015-01-15 | SNB scraps the franc cap | Central Banks | ID |
| 2015-07-05 | Greek bailout referendum | Elections | WE |
| 2015-12-16 | Fed's first hike since 2006 | Central Banks | ID |
| 2016-06-23 | Brexit referendum | Elections | AC (resultado de noche) |
| 2016-11-08 | US presidential election (Trump) | Elections | AC |
| 2017-05-07 | French presidential runoff (Macron) | Elections | WE |
| 2018-03-01 | US steel & aluminum tariffs announced | Trade | ID |
| 2018-07-06 | First US tariffs on Chinese goods take effect | Trade | pre-market |
| 2018-11-06 | US midterm elections | Elections | AC |
| 2019-05-05 | US escalates China tariffs | Trade | WE |
| 2019-09-14 | Attack on Saudi Abqaiq oil facility | Geopolitics | WE |
| 2020-01-03 | US kills Soleimani | Geopolitics | pre-market |
| 2020-01-15 | US–China Phase One deal signed | Trade | ID |
| 2020-11-03 | US presidential election (Biden) | Elections | AC |
| 2022-02-24 | Russia invades Ukraine | Geopolitics | pre-market (Europa ID) |
| 2022-10-07 | US chip export controls on China | Trade | ID |
| 2022-11-08 | US midterm elections | Elections | AC |
| 2023-03-10 | Silicon Valley Bank collapses | Crises | ID |
| 2023-03-19 | UBS takes over Credit Suisse | Crises | WE |
| 2023-07-03 | China restricts gallium & germanium exports | Trade | ID |
| 2023-10-07 | Hamas attack on Israel | Geopolitics | WE |
| 2024-06-09 | EU Parliament elections; Macron dissolves Assembly | Elections | WE |
| 2024-08-05 | Yen carry-trade unwind | Crises | ID |
| 2024-09-18 | Fed's first cut of the cycle (50 bp) | Central Banks | ID |
| 2024-11-05 | US presidential election (Trump) | Elections | AC |
| 2025-02-23 | German federal election | Elections | WE |
| 2025-04-02 | "Liberation Day" tariffs | Trade | AC |
| 2025-04-09 | 90-day tariff pause | Trade | ID |
| 2025-06-13 | Israel strikes Iran | Geopolitics | pre-market |
| 2025-10-09 ⚠ | China expands rare-earth export controls | Trade | ID |
| 2026-11-03 | US midterm elections | Elections | AC |

**Total: ~85 eventos (46 hitos + 39 sueltos).** Los eventos de 2026 posteriores a junio se agregan después de verificarlos.

**Prioridad si falta tiempo:** lanzar primero con los 7 episodios y las elecciones de EE.UU.; el resto se agrega en la semana siguiente. Como el pipeline es automático, sumar eventos solo cuesta revisar sus textos.

---

## 5. Cálculo

### 5.1 Dos modos
- **Absolute:** `R = P(t_h) / P(t−1) − 1`, la caída o subida del sector contra su propio precio previo.
- **vs. market:** `R_rel = R_sector − R_benchmark`, en la misma ventana. Es *market-adjusted* y no requiere estimar betas.

### 5.2 Tres horizontes
| Horizonte | Sesiones después del día 0 | Escala de color (saturación) |
|---|---|---|
| 1 week | 5 | ±10% |
| 1 month | 21 | ±20% |
| 3 months | 63 | ±30% |

- **Default:** Absolute + 1 week.
- La base siempre es el cierre t−1 (sección 3.4).
- Se cuentan las sesiones del calendario de cada mercado.

### 5.3 Estados de celda
- **Normal:** escala divergente centrada en 0 (rojo negativo, verde positivo).
- **Insufficient data:** gris, cuando la serie no existe o la canasta tiene menos de 2 empresas.
- **In progress:** borde punteado y retorno "hasta hoy", cuando aún no pasó el horizonte completo.

### 5.4 Tooltip
Retorno del sector · retorno del benchmark · diferencia · fechas exactas usadas (t−1 y t_h) · número de empresas en la canasta.

### 5.5 Episodios
- **Drawdown máximo por sector:** `min(P_t / max(P_s, s ≤ t)) − 1`, dentro del rango del episodio.
- También se muestra el retorno total del episodio (de inicio a fin).

---

## 6. Noticias: qué se decía en ese momento

### 6.1 Fuentes
| Fuente | Qué da | Cobertura | Notas |
|---|---|---|---|
| **The Guardian Open Platform** | Texto completo, metadata, tags | 1999 → hoy | Key de desarrollador gratuita, límites diarios |
| **NYT Article Search / Archive API** | Titular, abstract, lead paragraph, URL | 1851 → hoy | Gratis, **solo uso no comercial** |
| **Fuentes primarias** | Comunicados de la Fed y del BCE, discursos, actas del FOMC, comunicados de gobiernos | Desde los 90 | Se enlazan a mano en `events.yaml` |

### 6.2 Proceso por evento
1. Buscar artículos de **las 4 semanas previas** a `announced_at_utc`, con las `news_keywords` del evento, filtrando por secciones de negocios, economía o mundo.
2. Guardar 10 a 20 candidatos (titular, abstract, fecha, URL, fuente).
3. Elegir automáticamente los 3 a 5 titulares más relevantes, que se muestran como links.
4. Generar con IA el **contexto**: 2 a 3 frases sobre "qué decía la prensa antes", basadas solo en esos titulares y abstracts.

### 6.3 Reglas
- **No se publica texto de artículos.** Solo el resumen propio y los titulares como links.
- **Atribución visible:** "Data provided by The New York Times" y "Powered by The Guardian", según los términos de cada API.
- **Tarea:** revisar los términos de NYT y Guardian sobre pasar su contenido a un LLM. Si alguno lo restringe, la IA resume solo con la otra fuente y con los comunicados oficiales.
- Para China no hay una API propia: se usa la cobertura de NYT y Guardian sobre China más los comunicados oficiales.

---

## 7. Indicadores de "tono" (línea encima del heatmap)

| Indicador | Qué mide | Fuente | Frecuencia |
|---|---|---|---|
| **Economic Policy Uncertainty (EPU), US** | Frecuencia de artículos de prensa sobre incertidumbre de política económica | FRED: `USEPUINDXD` | Diaria, desde 1985 |
| **Geopolitical Risk Index (GPR)** | Riesgo geopolítico según la prensa (Caldara & Iacoviello) | Sitio de los autores | Diaria |
| **VIX** | Volatilidad implícita: el miedo del mercado | Yahoo: `^VIX` | Diaria, desde 1990 |

- El selector de indicador va junto a la línea.
- La línea se alinea con las columnas del heatmap y marca los eventos con ticks.
- En la vista de episodio, el indicador aparece debajo del gráfico de sectores.

---

## 8. Textos con IA

### 8.1 Dos textos por evento
| Texto | Contenido | Entrada |
|---|---|---|
| **Context** | Qué pasó y qué se decía en las semanas previas (2–3 frases) | Descripción del evento + titulares y abstracts |
| **Analysis** | Por qué los sectores reaccionaron así (3–4 frases) | Descripción del evento + **los números reales** de reacción por sector, mercado, modo y horizonte |

### 8.2 Reglas de generación
- **Offline**, con un workflow manual (`workflow_dispatch`), nunca en el navegador.
- El prompt exige: explicar solo mecanismos plausibles, no inventar hechos, citar solo lo que está en la entrada y señalar la incertidumbre.
- Se guarda en JSON con `generated_at`, `model` y `reviewed: false`.
- **Revisión manual obligatoria.** Solo se publican los textos con `reviewed: true`; los demás muestran "Analysis coming soon".
- **Eventos in progress:** el texto lleva "as of [fecha]" y se regenera cuando cierra el horizonte.
- **Disclaimer bajo cada análisis:** *"AI-generated · may be inaccurate · not financial advice."*

---

## 9. Interfaz

Una sola página, fondo claro, una sola tipografía. Rojo y verde solo para los datos.

1. **Header:** nombre del proyecto + controles:
   - Modo: Absolute / vs. market
   - Horizonte: 1W / 1M / 3M
   - Filtros por categoría (chips)
   - Filtro por mercado: All / US / EU / CN
2. **Línea de tono:** EPU / GPR / VIX, con un selector.
3. **Heatmap:**
   - Filas agrupadas por sector, con 3 sub-filas (US, EU, CN) cada una: 24 filas.
   - Columnas: los eventos en orden cronológico, con scroll horizontal.
   - Bandas de episodios encima de las columnas.
   - Clic en una celda o columna abre el detalle del evento; clic en una banda abre la vista del episodio.
4. **Panel de detalle del evento:**
   - Título, fecha, categoría y episodio.
   - Gráfico de líneas de los sectores desde t−5 hasta el horizonte elegido, con el día 0 marcado.
   - *Context* + titulares.
   - *Analysis* + disclaimer.
   - Links a las fuentes oficiales.
5. **Vista de episodio:** línea de tiempo larga con los 8 sectores, los hitos marcados, la tabla de drawdown máximo por sector y el indicador de tono debajo.
6. **Footer:** "How it's calculated" (desplegable) + advertencias + atribuciones de datos.

### 9.1 Texto del footer ("How it's calculated")
- Data: Yahoo Finance (adjusted close), daily. Returns in local currency.
- Base price: last close before the announcement. Day 0: session in progress at the announcement, or the next session to open.
- Absolute = sector return. vs. market = sector return minus benchmark return (SPY, STOXX Europe 600, Hang Seng; CSI 300 for China Defense).
- China and several other sectors use equal-weighted baskets of large caps; days with fewer than two constituents are shown as insufficient data.
- US "Banks" uses XLF (Financials) for its longer history.
- Baskets use current large caps; historical results may carry survivorship bias.
- Longer horizons include other news; reactions are not attributable to a single event.
- Context and analysis texts are AI-generated and reviewed, but may be inaccurate. Not financial advice.
- News data provided by The New York Times and The Guardian. Uncertainty indices: Baker, Bloom & Davis (EPU); Caldara & Iacoviello (GPR).

---

## 10. Arquitectura y stack

### 10.1 Stack
- **Pipeline:** Python 3.12 · `yfinance` · `pandas` · `pyyaml` · `requests` (NYT, Guardian, FRED) · SDK del LLM.
- **Frontend:** Vite + React + TypeScript + **ECharts**.
- **Hosting:** **GitHub Pages**.
- **Automatización:** **GitHub Actions**.
- **Secrets en GitHub:** `NYT_API_KEY`, `GUARDIAN_API_KEY`, `FRED_API_KEY`, `LLM_API_KEY`. Nunca van en el frontend.

### 10.2 Estructura del repo
```
/
├─ config/
│  ├─ sectors.yaml        # tickers, canastas y benchmarks por sector y mercado
│  ├─ events.yaml         # eventos curados
│  └─ episodes.yaml       # episodios
├─ pipeline/
│  ├─ fetch_prices.py     # yfinance → data/raw/prices.parquet
│  ├─ build_series.py     # canastas dinámicas + benchmarks
│  ├─ compute_reactions.py# 2 modos × 3 horizontes, drawdowns
│  ├─ fetch_indicators.py # EPU, GPR, VIX
│  ├─ fetch_news.py       # NYT + Guardian → candidatos por evento
│  ├─ generate_texts.py   # contexto + análisis con IA (manual)
│  └─ export.py           # → web/public/data/*.json
├─ web/                   # app Vite + React
│  └─ public/data/        # JSON publicados
├─ .github/workflows/
│  ├─ daily.yml           # cron diario: precios, indicadores, reacciones, export, deploy
│  ├─ texts.yml           # workflow_dispatch: noticias + textos IA
│  └─ deploy.yml          # build del frontend → GitHub Pages
└─ README.md
```

### 10.3 Esquemas

**`events.yaml`**
```yaml
- id: lehman_2008
  title: Lehman Brothers bankruptcy
  announced_at_utc: 2008-09-15T05:45:00Z   # verificar
  category: crises        # elections | trade | geopolitics | central_banks | crises
  episode_id: gfc         # opcional
  news_keywords: ["Lehman", "investment bank", "credit crisis"]
  official_sources:
    - label: Federal Reserve press release
      url: https://...
```

**`episodes.yaml`**
```yaml
- id: gfc
  title: Global Financial Crisis
  start: 2007-02-27
  end: 2009-03-09         # o null si está en curso
```

**`sectors.yaml`**
```yaml
- id: tech
  name: Tech
  markets:
    us: { type: etf, tickers: [XLK], benchmark: SPY }
    eu: { type: etf, tickers: [EXV3.DE], benchmark: EXSA.DE }
    cn: { type: basket, tickers: [0700.HK, 9988.HK, 3690.HK, 1810.HK, 0992.HK], benchmark: ^HSI, min_constituents: 2 }
```

**`reactions.json`** (salida)
```json
{
  "lehman_2008": {
    "tech": {
      "us": {
        "base_date": "2008-09-12",
        "day0": "2008-09-15",
        "absolute": { "1w": -0.071, "1m": -0.152, "3m": -0.304 },
        "vs_market": { "1w": -0.012, "1m": -0.020, "3m": -0.041 },
        "benchmark": { "1w": -0.059, "1m": -0.132, "3m": -0.263 },
        "constituents": 1,
        "status": { "1w": "ok", "1m": "ok", "3m": "ok" }
      }
    }
  }
}
```
(`status`: `ok` | `insufficient` | `in_progress`)

**`texts.json`** (salida)
```json
{
  "lehman_2008": {
    "context": { "text": "...", "generated_at": "...", "model": "...", "reviewed": true },
    "analysis": { "text": "...", "generated_at": "...", "model": "...", "reviewed": true },
    "headlines": [ { "title": "...", "source": "NYT", "date": "2008-09-10", "url": "..." } ]
  }
}
```

Otros: `episodes.json` (drawdowns y series del episodio), `indicators.json` (EPU, GPR, VIX), `series.json` (series diarias de precio normalizadas para los gráficos).

### 10.4 Workflows
- **`daily.yml`:** cron diario después del cierre de EE.UU. Corre `fetch_prices`, `build_series`, `compute_reactions`, `fetch_indicators` y `export`; hace commit de los JSON y despliega.
- **`texts.yml`:** manual. Corre `fetch_news` y `generate_texts` y abre un PR con los textos nuevos (`reviewed: false`). Revisas, marcas `reviewed: true` y haces merge.
- **`deploy.yml`:** en cada push a `main`, build de Vite y publicación en GitHub Pages.

---

## 11. Plan hasta el 15 de diciembre

| Fechas | Entregable |
|---|---|
| 26–28 nov | Verificar tickers y fechas de inicio · `sectors.yaml` · `fetch_prices` + `build_series` |
| 29 nov – 1 dic | `events.yaml` y `episodes.yaml` con fechas verificadas · `compute_reactions` + tests de la regla del día 0 |
| 2–5 dic | Frontend: heatmap, bandas, controles, panel de detalle |
| 6–8 dic | Indicadores de tono · vista de episodio · footer |
| 9–11 dic | Noticias + textos IA · revisión de todos los textos |
| 12–13 dic | Pulido visual, mobile básico, deploy final en GitHub Pages |
| 14–15 dic | Link en el one-pager de la aplicación |

---

## 12. Pendientes

- [ ] **Nombre del proyecto** (neutral y en inglés)
- [ ] Verificar todos los tickers en Yahoo y registrar la primera fecha con datos
- [ ] Verificar la fecha y hora UTC de cada evento, en especial los marcados con ⚠
- [ ] Revisar los términos de uso de NYT y Guardian (atribución y uso con LLM)
- [ ] Elegir el LLM y el modelo para los textos
- [ ] Agregar los eventos relevantes de 2026 una vez verificados
