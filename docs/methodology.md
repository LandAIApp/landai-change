# Metodología

## Resumen

1. Se agrupan observaciones Sentinel-2 sin nubes alrededor de dos fechas (A y B), ±30 días cada una.
2. Una **mediana** por píxel representa cada periodo.
3. Se comparan seis bandas (Blue, Green, Red, NIR=B8A, SWIR1=B11, SWIR2=B12) a **20 m**.
4. **Magnitud espectral** (CVA): `‖B − A‖ / √6`. Mide cuánto cambió la superficie.
5. **Ángulo espectral**: `acos(clamp(A·B / (‖A‖‖B‖ + ε)))`. Mide cuánto cambió la *forma* de la firma espectral.
6. Los **percentiles P50/P90/P95** de la magnitud, calculados *dentro del área seleccionada*, clasifican el cambio:
   1 = estable (< P50), 2 = moderado (P50–P90), 3 = alto (≥ P90).
7. **Limpieza espacial**: de la clase 3 solo se conservan parches con ≥ 7 píxeles conectados (8-conectividad), ≈ 2 800 m².
8. Se reportan áreas en hectáreas (`pixelArea`, 20 m) y porcentajes del área.

## Datos y máscaras

- `COPERNICUS/S2_SR_HARMONIZED` enlazado con `GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`.
- Se conservan píxeles con `cs_cdf ≥ 0.55` y se excluyen las clases SCL 1, 3, 7, 8, 9, 10, 11.
- Prefiltro de escena: `CLOUDY_PIXEL_PERCENTAGE < 85`. Reflectancia = DN / 10 000.
- Fechas admitidas desde 2018-03-01 (cobertura SR + Cloud Score+ con la ventana de −30 días).

## Índices

NDVI, NBR, NDWI, NDBI en ambos periodos y sus diferencias **B − A** (ΔNDVI, ΔNBR, ΔNDWI, ΔNDBI), disponibles como capas avanzadas.

## Cómo leer el resultado (importante)

- **Los umbrales son relativos al área.** Por construcción, ≈ 10 % de los píxeles válidos cae siempre en
  "cambio alto" (≥ P90) y ≈ 5 % por encima de P95. Un municipio sin cambios reales también mostrará
  "cambio alto". Usa el resultado para **priorizar** zonas dentro del área, no para medir cambio absoluto ni
  comparar áreas distintas. Los valores de P50/P90/P95 (sección *Detalles técnicos*) permiten juzgar la magnitud real.
- **Estacionalidad.** Comparar épocas distintas del año (seca vs. lluviosa) produce cambio espectral que no
  es cambio del territorio. Prefiere fechas A y B en la misma época.
- **Nubes.** Si el porcentaje de datos válidos es bajo (< 70 %) se muestra una advertencia.
- **Causa.** El método no identifica la causa del cambio (deforestación, minería, urbanización, cultivos,
  inundación, etc.). Requiere interpretación con contexto y verificación.

## Lo que NO hace

Sin aprendizaje automático (Random Forest, deep learning), sin exportación a Drive, sin vectorización, sin base de datos ni autenticación de usuarios.
