# Adaptación Landsat 8 → Sentinel-2

Referencia: [`reference_landsat_change.js`](reference_landsat_change.js) (Code Editor, Landsat 8 C2 L2).
Se conservó la lógica conceptual (CVA + ángulo + percentiles + limpieza) y se cambió lo que Sentinel-2 y una app pública exigen.

| Tema | Script Landsat | Esta app (Sentinel-2) | Motivo |
|---|---|---|---|
| Colección | `LANDSAT/LC08/C02/T1_L2` | `COPERNICUS/S2_SR_HARMONIZED` + Cloud Score+ | 10–20 m, revisita 5 días, máscara de nubes superior |
| Máscara | bits de `QA_PIXEL` (relleno, nube, sombra, cirro, nieve) | `cs_cdf ≥ 0.55` + SCL ∉ {1,3,7,8,9,10,11} | Equivalente funcional para S2 |
| Escala | `DN·0.0000275 − 0.2` | `DN / 10000` | Escalado oficial de S2 SR |
| Bandas | SR_B2…SR_B7 | B2, B3, B4, **B8A**, B11, B12 | B8A (20 m) es la NIR espectralmente comparable con B11/B12; evita remuestreos |
| Periodo | Año calendario completo | Fecha de referencia ±30 días | Permite comparar fechas concretas y acota la cuota |
| Región | Asset privado `Area` | Municipio de la colección municipal **o** polígono dibujado | App pública |
| Escala de análisis | 30 m | 20 m | Resolución nativa de B8A/B11/B12 |
| Percentiles | `bestEffort: true`, `maxPixels: 1e13`, escala 30 | **sin** `bestEffort`, `maxPixels: 1e9`, `tileScale: 4`, escala 20 | Resultados exactos y reproducibles; el límite de área protege la cuota |
| Parche mínimo | 3 px × 900 m² = 2 700 m² | 7 px × 400 m² = 2 800 m² | Misma área mínima física |
| Limpieza | `connectedPixelCount` sobre imagen 0/1 | `selfMask()` **antes** de `connectedPixelCount` | Ver "Discrepancias" |
| Ángulo espectral | sin protección | denominador + ε (1e‑6) | Evita NaN con píxeles de reflectancia ≈ 0 |
| Exportación | 4 × `Export.image.toDrive` | ninguna | Sin Drive; los resultados se ven como teselas |
| Estadísticas | solo `print` de percentiles | áreas (ha) y % por clase con un único `reduceRegion` | Resultados comprensibles para no especialistas |

## Discrepancias detectadas en el script de referencia

1. **Años desfasados.** Los nombres y títulos dicen 2020 vs 2025, pero `annualComposite(2015)` y `annualComposite(2020)`
   se usan para `composite2020` y `composite2025`. Esta app no depende de esos años: el usuario elige las fechas.
2. **Limpieza de parches.** `cambioClasificado.eq(3)` es una imagen 0/1; `connectedPixelCount` cuenta también los
   píxeles con valor 0, que quedan "conectados" entre sí y no se eliminan. Aquí la clase 3 se enmascara antes de contar,
   de modo que solo se evalúan píxeles de cambio alto.
3. **Producto final con bandas heterogéneas.** Se conserva el producto de 9 bandas (`ChangeMagnitude`, `SpectralAngle`,
   `dNDVI`, `dNBR`, `dNDWI`, `dNDBI`, `ChangeClass`, `HighChangeP95`, `HighChangeClean`) listo para un futuro endpoint de exportación.
4. **Percentiles relativos.** El script (y esta app) clasifican con percentiles del propio AOI; ver `methodology.md`.

## Decisiones propias de la app (no están en el script)

- Percentiles evaluados **una vez** (`getInfo`) y pasados como números a la segunda etapa del grafo, para que las teselas no
  vuelvan a calcular el percentil.
- `getInfo` solo en el borde de la API: conteo de escenas, percentiles, áreas y metadatos del municipio.
- Límites de área y de uso (beta gratuita); ver `deployment.md`.

## Pendiente de validar

- No existe un caso de demostración Sentinel-2 validado: el ejemplo (Tolima / San Luis, 2021‑02‑15 vs 2025‑02‑15)
  está centralizado en `frontend/src/config/example.ts` para cambiarlo fácilmente.
- Este paquete se probó con Earth Engine **simulado** (pruebas automáticas) y con el frontend contra un backend simulado.
  La primera ejecución real debe hacerse con `python backend/scripts/smoke_test.py` y un análisis de un área pequeña.
