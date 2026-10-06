import { translateOptional, type Language } from '../i18n';
import type { LayerInfo } from '../types/api';

export function splitLayers(layers: LayerInfo[]): { main: LayerInfo[]; advanced: LayerInfo[] } {
  return {
    main: layers.filter((l) => l.group === 'main'),
    advanced: layers.filter((l) => l.group === 'advanced'),
  };
}

export const layerLabel = (lang: Language, layer: LayerInfo) =>
  translateOptional(lang, `layers.${layer.id}.label`) ?? layer.id;
export const layerDescription = (lang: Language, layer: LayerInfo) =>
  translateOptional(lang, `layers.${layer.id}.desc`) ?? '';
