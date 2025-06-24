<template>
  <div ref="mapContainer" class="map-view">
    <div v-if="showEmptyState" class="empty-state-message">
      Select at least a family to view observations
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, nextTick } from 'vue'
import type { Observation } from '../types'
import * as L from 'leaflet'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'

L.Icon.Default.imagePath = '/leaflet/images/';

// Customizes the default marker icon
const defaultIcon = L.icon({
  iconUrl: '/leaflet/images/marker-icon.png',
  iconRetinaUrl: '/leaflet/images/marker-icon-2x.png',
  shadowUrl: '/leaflet/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const props = defineProps<{
  observations: Observation[]
  showEmptyState?: boolean
  enableLocationPicker?: boolean
  pickedLocation?: { lat: number, lng: number }
}>()

const emit = defineEmits(["location-picked"]);

// Map references
const mapContainer = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let markerCluster: L.MarkerClusterGroup | null = null
let pinMarker: L.Marker | null = null

/**
 * Places or moves the location pin marker
 * @param lat - Latitude
 * @param lng - Longitude
 */
const addOrMovePin = (lat: number, lng: number) => {
  if (!map) return;
  if (pinMarker) {
    // Moves existing pin
    pinMarker.setLatLng([lat, lng]);
  } else {
    // Creates new pin
    pinMarker = L.marker([lat, lng], { icon: defaultIcon }).addTo(map);
  }

  // Smoothly centers map on the pin
  map?.flyTo([lat, lng], 13, {
  animate: true,
  duration: 2  
});

}

/**
 * Initializes the Leaflet map with base layers
 */
const initializeMap = () => {
  if (map || !mapContainer.value) return;

  map = L.map(mapContainer.value).setView([20, 0], 2)

  // Defines map layers
  const baseLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)

  const terrainLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenTopoMap contributors'
  })

  const satelliteLayer = L.layerGroup([
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Imagery &copy; Esri'
    }),
    L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Labels &copy; Esri'
    })
  ]);

  L.control.layers({
    'Street Map': baseLayer,
    'Terrain Map': terrainLayer,
    'Satellite Map': satelliteLayer
  }).addTo(map)

  // Enables location picking if prop is set
  if (props.enableLocationPicker) {
    map.on("click", (e: L.LeafletMouseEvent) => {
      const { lat, lng } = e.latlng;
      emit("location-picked", { lat, lng });
      addOrMovePin(lat, lng);
    });
  }

  updateMarkers();

  // Adds initial pin if provided
  if (props.pickedLocation) {
    addOrMovePin(props.pickedLocation.lat, props.pickedLocation.lng);
  }
}

/**
 * Sanitizes HTML strings to prevent XSS
 * @param str - Input string
 * @returns Sanitized string
 */
function sanitizeHTML(str: string): string {
  const temp = document.createElement('div');
  temp.textContent = str;
  return temp.innerHTML;
}

/**
 * Updates all markers on the map based on current observations
 */
const updateMarkers = () => {
  if (!map) return;

  // Clears existing markers
  if (markerCluster) {
    markerCluster.clearLayers()
    map.removeLayer(markerCluster);
  }

  // Creates new cluster group
  markerCluster = L.markerClusterGroup({
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true
  });
  
  // Handles empty observations
  if (!props.observations?.length) {
    map.flyTo([20, 0], 2, {
      animate: true,
      duration: 1.5
    });
    return;
  }
  
  // Adds markers for each observation
  props.observations.forEach(obs => {
    const coords = obs.location?.coordinates
    if (!coords || coords.length !== 2) return

    const [lon, lat] = coords;
    const p = obs.properties || {};

    const species = sanitizeHTML(p.species || 'Unknown');
    const family = sanitizeHTML(p.family || 'Unknown');
    const genus = sanitizeHTML(p.genus || 'Unknown');
    const locationName = sanitizeHTML(p.location_name || p.region || p.country || 'Unknown');
    const date = sanitizeHTML(p.timestamp ? new Date(p.timestamp).toLocaleDateString() : 'Unknown');
    const imageUrl =
      p.photo?.[0] && /^https?:\/\//.test(p.photo[0]) ? sanitizeHTML(p.photo[0]) : null;
    const externalLink = p.external_link ? sanitizeHTML(p.external_link) : null;

    // Builds popup HTML content
    const popupContent = `
      <div class="popup-content">
        <h3>${species}</h3>
        <p><strong>Family:</strong> ${family}</p>
        <p><strong>Genus:</strong> ${genus}</p>
        <p><strong>Location:</strong> ${locationName}</p>
        <p><strong>Date:</strong> ${date}</p>
        ${
          externalLink
            ? `<a href="${externalLink}" target="_blank" rel="noopener noreferrer">View Details</a>`
            : ''
        }
      </div>
    `;

    const marker = L.marker([lat, lon], { icon: defaultIcon });
    marker.bindPopup(popupContent);
    markerCluster!.addLayer(marker);
  });

  map.addLayer(markerCluster);

  // Auto-fit bounds if we have markers
  if (markerCluster.getLayers().length > 0) {
    map.fitBounds(markerCluster.getBounds(), { padding: [50, 50], maxZoom: 12 });
  }
};

onMounted(async () => {
  await nextTick();
  initializeMap();

  setTimeout(() => {
    map?.invalidateSize();

    setTimeout(() => {
      map?.invalidateSize();
    }, 300);
  }, 100);
});

watch(() => props.observations, updateMarkers, { deep: true })
watch(() => props.showEmptyState, updateMarkers)
onUnmounted(() => {
  if (markerCluster) {
    markerCluster.clearLayers(); 
    markerCluster = null;
  }
  if (map) {
    map.remove();
    map = null;
  }
});

defineExpose({
  addOrMovePin
});

</script>

<style scoped>

.empty-state-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(255, 255, 255, 0.9);
  padding: 1rem;
  border-radius: 4px;
  z-index: 1000;
  text-align: center;
}

.map-view {
  height: 500px;
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.popup-content {
  max-width: 300px;
}
.popup-content img {
  margin-top: 10px;
  display: block;
  max-height: 200px;
}
</style>
