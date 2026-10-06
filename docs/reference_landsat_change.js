// ============================================================
// DETECCIÓN DE CAMBIOS LANDSAT 8 - 2020 vs 2025
// Región: projects/ee-maikolzaraza07/assets/Area
// Método: magnitud espectral multibanda + percentiles
// ============================================================


// ------------------------------------------------------------
// 1. REGIÓN DE ESTUDIO
// ------------------------------------------------------------

var area = ee.FeatureCollection('projects/ee-maikolzaraza07/assets/Area');

Map.centerObject(area, 10);
Map.addLayer(area, {color: 'red'}, 'Área de estudio', false);


// ------------------------------------------------------------
// 2. COLECCIÓN LANDSAT 8 C2 L2
// ------------------------------------------------------------

var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2');

var srBands = [
  'SR_B2',
  'SR_B3',
  'SR_B4',
  'SR_B5',
  'SR_B6',
  'SR_B7'
];

var outBands = [
  'Blue',
  'Green',
  'Red',
  'NIR',
  'SWIR1',
  'SWIR2'
];


// ------------------------------------------------------------
// 3. FUNCIÓN DE MÁSCARA Y ESCALAMIENTO
// ------------------------------------------------------------

function maskScaleL8(image) {
  var qa = image.select('QA_PIXEL');

  // Bits QA_PIXEL Collection 2 Level 2:
  // bit 0 = Fill
  // bit 1 = Dilated Cloud
  // bit 2 = Cirrus
  // bit 3 = Cloud
  // bit 4 = Cloud Shadow
  // bit 5 = Snow

  var fill = qa.bitwiseAnd(1 << 0).eq(0);
  var dilatedCloud = qa.bitwiseAnd(1 << 1).eq(0);
  var cirrus = qa.bitwiseAnd(1 << 2).eq(0);
  var cloud = qa.bitwiseAnd(1 << 3).eq(0);
  var cloudShadow = qa.bitwiseAnd(1 << 4).eq(0);
  var snow = qa.bitwiseAnd(1 << 5).eq(0);

  var mask = fill
    .and(dilatedCloud)
    .and(cirrus)
    .and(cloud)
    .and(cloudShadow)
    .and(snow);

  // Escalamiento oficial Landsat Collection 2 L2:
  // Reflectancia = DN * 0.0000275 - 0.2
  var sr = image
    .select(srBands)
    .multiply(0.0000275)
    .add(-0.2)
    .rename(outBands);

  return sr
    .updateMask(mask)
    .copyProperties(image, image.propertyNames());
}


// ------------------------------------------------------------
// 4. CREAR COMPUESTOS ANUALES
// ------------------------------------------------------------

function annualComposite(year) {
  var start = ee.Date.fromYMD(year, 1, 1);
  var end = ee.Date.fromYMD(year, 12, 31);

  var collection = l8
    .filterBounds(area)
    .filterDate(start, end)
    .map(maskScaleL8);

  print('Número de imágenes Landsat 8 año ' + year, collection.size());

  var composite = collection
    .median()
    .clip(area)
    .set('year', year);

  return composite;
}

var composite2020 = annualComposite(2015);
var composite2025 = annualComposite(2020);


// ------------------------------------------------------------
// 5. VISUALIZACIÓN RGB Y FALSO COLOR
// ------------------------------------------------------------

var rgbVis = {
  bands: ['Red', 'Green', 'Blue'],
  min: 0.02,
  max: 0.35,
  gamma: 1.2
};

var falseColorVis = {
  bands: ['NIR', 'Red', 'Green'],
  min: 0.02,
  max: 0.45,
  gamma: 1.2
};

Map.addLayer(composite2020, rgbVis, 'Landsat 8 RGB 2020');
Map.addLayer(composite2025, rgbVis, 'Landsat 8 RGB 2025');
Map.addLayer(composite2020, falseColorVis, 'Landsat 8 Falso color 2020', false);
Map.addLayer(composite2025, falseColorVis, 'Landsat 8 Falso color 2025', false);


// ------------------------------------------------------------
// 6. ÍNDICES ESPECTRALES
// ------------------------------------------------------------

function addIndices(image) {
  var ndvi = image.normalizedDifference(['NIR', 'Red']).rename('NDVI');
  var nbr = image.normalizedDifference(['NIR', 'SWIR2']).rename('NBR');
  var ndwi = image.normalizedDifference(['Green', 'NIR']).rename('NDWI');
  var ndbi = image.normalizedDifference(['SWIR1', 'NIR']).rename('NDBI');

  return image.addBands([ndvi, nbr, ndwi, ndbi]);
}

var img2020 = addIndices(composite2020);
var img2025 = addIndices(composite2025);

var ndvi2020 = img2020.select('NDVI');
var ndvi2025 = img2025.select('NDVI');
var dNDVI = ndvi2025.subtract(ndvi2020).rename('dNDVI');

var nbr2020 = img2020.select('NBR');
var nbr2025 = img2025.select('NBR');
var dNBR = nbr2025.subtract(nbr2020).rename('dNBR');

Map.addLayer(ndvi2020, {min: -0.2, max: 0.8, palette: ['brown', 'yellow', 'green']}, 'NDVI 2020', false);
Map.addLayer(ndvi2025, {min: -0.2, max: 0.8, palette: ['brown', 'yellow', 'green']}, 'NDVI 2025', false);
Map.addLayer(dNDVI, {min: -0.5, max: 0.5, palette: ['red', 'white', 'green']}, 'ΔNDVI 2025-2020');

Map.addLayer(dNBR, {min: -0.5, max: 0.5, palette: ['red', 'white', 'blue']}, 'ΔNBR 2025-2020', false);


// ------------------------------------------------------------
// 7. MAGNITUD DE CAMBIO MULTIBANDA
// Change Vector Analysis - distancia espectral
// ------------------------------------------------------------

var changeBands = ['Blue', 'Green', 'Red', 'NIR', 'SWIR1', 'SWIR2'];

function magnitude(image) {
  return image
    .pow(2)
    .reduce(ee.Reducer.sum())
    .sqrt();
}

var difference = composite2025
  .select(changeBands)
  .subtract(composite2020.select(changeBands));

var spectralMagnitude = magnitude(difference)
  .divide(Math.sqrt(changeBands.length))
  .rename('Cambio_Magnitud')
  .clip(area);

Map.addLayer(
  spectralMagnitude,
  {"min":0,"max":0.09,"palette":["ffffff","cac859","f10808"]},
  'Magnitud cambio espectral'
);


// ------------------------------------------------------------
// 8. ÁNGULO ESPECTRAL
// Complementario a la magnitud
// ------------------------------------------------------------

var dot = composite2025
  .select(changeBands)
  .multiply(composite2020.select(changeBands))
  .reduce(ee.Reducer.sum());

var norm2025 = magnitude(composite2025.select(changeBands));
var norm2020 = magnitude(composite2020.select(changeBands));

var spectralAngle = dot
  .divide(norm2025)
  .divide(norm2020)
  .clamp(-1, 1)
  .acos()
  .rename('Angulo_Espectral')
  .clip(area);

Map.addLayer(
  spectralAngle,
  {min: 0, max: 1, palette: ['white', 'cyan', 'blue', 'purple']},
  'Ángulo espectral',
  false
);


// ------------------------------------------------------------
// 9. CÁLCULO DE PERCENTILES P50, P90 Y P95
// ------------------------------------------------------------

var percentiles = spectralMagnitude.reduceRegion({
  reducer: ee.Reducer.percentile([50, 90, 95]),
  geometry: area.geometry(),
  scale: 30,
  maxPixels: 1e13,
  tileScale: 4,
  bestEffort: true
});

print('Percentiles magnitud cambio', percentiles);

var p50 = ee.Number(percentiles.get('Cambio_Magnitud_p50'));
var p90 = ee.Number(percentiles.get('Cambio_Magnitud_p90'));
var p95 = ee.Number(percentiles.get('Cambio_Magnitud_p95'));

print('P50', p50);
print('P90', p90);
print('P95', p95);


// ------------------------------------------------------------
// 10. CLASIFICACIÓN POR PERCENTILES
// 1 = estable / baja variación
// 2 = cambio medio
// 3 = cambio alto
// ------------------------------------------------------------

var cambioClasificado = ee.Image(0)
  .where(spectralMagnitude.lt(p50), 1)
  .where(spectralMagnitude.gte(p50).and(spectralMagnitude.lt(p90)), 2)
  .where(spectralMagnitude.gte(p90), 3)
  .rename('Cambio_Clasificado_P50_P90')
  .updateMask(spectralMagnitude.mask())
  .clip(area);

var classVis = {
  min: 1,
  max: 3,
  palette: [
    '2ca25f', // estable / baja variación
    'fee08b', // cambio medio
    'd73027'  // cambio alto
  ]
};

Map.addLayer(cambioClasificado, classVis, 'Cambio clasificado P50-P90');


// ------------------------------------------------------------
// 11. CAMBIO BINARIO P95
// 0 = no priorizado
// 1 = cambio alto
// ------------------------------------------------------------

var cambioBinarioP95 = spectralMagnitude
  .gte(p95)
  .rename('Cambio_Binario_P95')
  .selfMask()
  .clip(area);

Map.addLayer(
  cambioBinarioP95,
  {palette: ['red']},
  'Cambio binario > P95',
  false
);


// ------------------------------------------------------------
// 12. LIMPIEZA ESPACIAL BÁSICA
// Elimina grupos pequeños en la clase alta.
// Landsat 30 m: 1 píxel = 900 m2.
// ------------------------------------------------------------

var minPixels = 3; // 3 pixeles = 2700 m2 aproximadamente

var cambioAlto = cambioClasificado.eq(3);

var connected = cambioAlto.connectedPixelCount({
  maxSize: 100,
  eightConnected: true
});

var cambioAltoLimpio = cambioAlto
  .updateMask(connected.gte(minPixels))
  .rename('Cambio_Alto_Limpio')
  .clip(area);

Map.addLayer(
  cambioAltoLimpio.selfMask(),
  {palette: ['red']},
  'Cambio alto limpio',
  true
);


// ------------------------------------------------------------
// 13. PRODUCTO MULTIBANDA FINAL
// ------------------------------------------------------------

var resultado = spectralMagnitude
  .addBands(spectralAngle)
  .addBands(dNDVI.rename('dNDVI'))
  .addBands(dNBR.rename('dNBR'))
  .addBands(cambioClasificado)
  .addBands(cambioBinarioP95.unmask(0))
  .addBands(cambioAltoLimpio.unmask(0))
  .clip(area);

print('Resultado multibanda', resultado);


// ------------------------------------------------------------
// 14. EXPORTAR RESULTADOS A GOOGLE DRIVE
// ------------------------------------------------------------

Export.image.toDrive({
  image: spectralMagnitude,
  description: 'L8_2020_2025_Cambio_Magnitud',
  folder: 'GEE_Cambios',
  fileNamePrefix: 'L8_2020_2025_Cambio_Magnitud',
  region: area.geometry(),
  scale: 30,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

Export.image.toDrive({
  image: cambioClasificado.toInt16(),
  description: 'L8_2020_2025_Cambio_Clasificado_P50_P90',
  folder: 'GEE_Cambios',
  fileNamePrefix: 'L8_2020_2025_Cambio_Clasificado_P50_P90',
  region: area.geometry(),
  scale: 30,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

Export.image.toDrive({
  image: cambioAltoLimpio.toInt16(),
  description: 'L8_2020_2025_Cambio_Alto_Limpio',
  folder: 'GEE_Cambios',
  fileNamePrefix: 'L8_2020_2025_Cambio_Alto_Limpio',
  region: area.geometry(),
  scale: 30,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

Export.image.toDrive({
  image: resultado.toFloat(),
  description: 'L8_2020_2025_Resultados_Cambio_Multibanda',
  folder: 'GEE_Cambios',
  fileNamePrefix: 'L8_2020_2025_Resultados_Cambio_Multibanda',
  region: area.geometry(),
  scale: 30,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});
