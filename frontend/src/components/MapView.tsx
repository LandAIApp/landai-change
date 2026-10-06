import { useEffect, useRef } from 'react';
import L from 'leaflet';
import { BASEMAP_ATTRIBUTION, BASEMAP_URL } from '../config/env';
import type { AreaLevel } from '../services/geometry';
import type { LayerInfo, LngLat, Ring } from '../types/api';

export type DrawTool = 'polygon' | 'rectangle';
type Bounds = [[number, number], [number, number]];

interface Props {
  layers: LayerInfo[];
  visible: Record<string, boolean>;
  opacity: Record<string, number>;
  boundary: GeoJSON.Feature | null;
  bounds: Bounds | null;
  drawTool: DrawTool | null;           // active drawing tool (null = not drawing)
  draft: LngLat[];                     // vertices placed so far
  ring: Ring | null;                   // finished drawn ring (closed)
  previewBoundary: GeoJSON.Feature | null;
  previewBounds: Bounds | null;
  level: AreaLevel;
  limitChip: string;
  onPoint: (p: LngLat) => void;
  onFinish: () => void;
  onRingChange: (ring: Ring) => void;
}

const COLORS: Record<AreaLevel, string> = {
  none: '#22d8b4', ok: '#22d8b4', warn: '#f5c451', over: '#ff7b7b', small: '#ff7b7b',
};
const toLatLng = (p: LngLat): L.LatLngTuple => [p[1], p[0]];
const toLngLat = (ll: L.LatLng): LngLat => [ll.lng, ll.lat];

export default function MapView(props: Props) {
  const { layers, visible, opacity, boundary, bounds } = props;
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileRefs = useRef<Record<string, L.TileLayer>>({});
  const boundaryRef = useRef<L.GeoJSON | null>(null);
  const aoiGroup = useRef<L.LayerGroup | null>(null);
  const handlers = useRef(props);
  handlers.current = props;
  const hasResult = layers.length > 0;

  // Create the map once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, { zoomControl: true, doubleClickZoom: true }).setView([4.6, -74.1], 6);
    L.tileLayer(BASEMAP_URL, { maxZoom: 19, attribution: BASEMAP_ATTRIBUTION }).addTo(map);
    aoiGroup.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  // Rebuild EE tile layers when a new analysis arrives.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    Object.values(tileRefs.current).forEach((t) => map.removeLayer(t));
    tileRefs.current = {};
    layers.forEach((l, i) => {
      tileRefs.current[l.id] = L.tileLayer(l.tile_url, { zIndex: 300 + i, maxZoom: 19, opacity: 0.8 });
    });
  }, [layers]);

  // Result boundary and viewport.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    boundaryRef.current?.remove();
    boundaryRef.current = null;
    if (boundary) {
      boundaryRef.current = L.geoJSON(boundary, {
        style: { color: '#ffffff', weight: 3, fill: false, opacity: 1 }, interactive: false,
      }).addTo(map);
      boundaryRef.current.bringToFront();
    }
    if (bounds) map.fitBounds(bounds, { padding: [30, 30] });
  }, [boundary, bounds]);

  // Visibility and opacity.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    Object.entries(tileRefs.current).forEach(([id, tile]) => {
      tile.setOpacity(opacity[id] ?? 0.8);
      const on = !!visible[id];
      if (on && !map.hasLayer(tile)) tile.addTo(map);
      if (!on && map.hasLayer(tile)) map.removeLayer(tile);
    });
  }, [layers, visible, opacity]);

  // Fit the municipality preview.
  useEffect(() => {
    if (props.previewBounds && mapRef.current && !hasResult) {
      mapRef.current.fitBounds(props.previewBounds, { padding: [30, 30] });
    }
  }, [props.previewBounds, hasResult]);

  // Clicks while a drawing tool is active.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const el = map.getContainer();
    if (!props.drawTool) { el.style.cursor = ''; return; }
    el.style.cursor = 'crosshair';
    map.doubleClickZoom.disable();
    const onClick = (e: L.LeafletMouseEvent) => handlers.current.onPoint(toLngLat(e.latlng));
    const onDbl = () => { if (handlers.current.drawTool === 'polygon') handlers.current.onFinish(); };
    map.on('click', onClick);
    map.on('dblclick', onDbl);
    return () => {
      map.off('click', onClick);
      map.off('dblclick', onDbl);
      map.doubleClickZoom.enable();
      el.style.cursor = '';
    };
  }, [props.drawTool]);

  // Draw the AOI: municipality preview, draft vertices, finished ring (draggable vertices).
  useEffect(() => {
    const map = mapRef.current;
    const group = aoiGroup.current;
    if (!map || !group) return;
    group.clearLayers();
    if (hasResult) return;
    const color = COLORS[props.level];

    if (props.previewBoundary) {
      L.geoJSON(props.previewBoundary, {
        style: { color, weight: 3, fillColor: color, fillOpacity: 0.12 }, interactive: false,
      }).addTo(group);
    }

    if (props.drawTool && props.draft.length > 0) {
      const pts = props.draft.map(toLatLng);
      L.polyline(pts, { color, weight: 3, dashArray: '6 6' }).addTo(group);
      pts.forEach((pt, i) => {
        const marker = L.circleMarker(pt, {
          radius: i === 0 ? 7 : 5, color: '#071110', weight: 2, fillColor: color, fillOpacity: 1,
        }).addTo(group);
        if (i === 0 && props.drawTool === 'polygon' && props.draft.length >= 3) {
          marker.on('click', (ev) => { L.DomEvent.stopPropagation(ev); handlers.current.onFinish(); });
        }
      });
      const rubber = L.polyline([], { color, weight: 2, dashArray: '2 8', opacity: 0.8 }).addTo(group);
      const rect = L.rectangle([pts[0], pts[0]], { color, weight: 3, fillOpacity: 0.1 });
      const onMove = (e: L.LeafletMouseEvent) => {
        if (handlers.current.drawTool === 'rectangle') {
          if (!group.hasLayer(rect)) rect.addTo(group);
          rect.setBounds(L.latLngBounds(pts[0], e.latlng));
        } else {
          rubber.setLatLngs([pts[pts.length - 1], e.latlng]);
        }
      };
      map.on('mousemove', onMove);
      return () => { map.off('mousemove', onMove); };
    }

    if (!props.drawTool && props.ring && props.ring.length >= 4) {
      const open = props.ring.slice(0, -1);
      const polygon = L.polygon(open.map(toLatLng), {
        color, weight: 3, fillColor: color, fillOpacity: 0.15,
      }).addTo(group);
      const current: L.LatLng[] = open.map((p) => L.latLng(p[1], p[0]));
      open.forEach((p, i) => {
        const marker = L.marker(toLatLng(p), {
          draggable: true, keyboard: false,
          icon: L.divIcon({ className: 'vertex-handle', iconSize: [14, 14] }),
        }).addTo(group);
        marker.on('drag', () => {
          current[i] = marker.getLatLng();
          polygon.setLatLngs(current);
        });
        marker.on('dragend', () => {
          const next = current.map(toLngLat);
          handlers.current.onRingChange([...next, next[0]]);
        });
      });
    }
    return undefined;
  }, [props.draft, props.ring, props.drawTool, props.previewBoundary, props.level, hasResult]);

  return (
    <>
      <div ref={containerRef} className="map" data-testid="map" />
      {!hasResult && <div className="map-chip">{props.limitChip}</div>}
    </>
  );
}
