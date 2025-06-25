<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import Plotly from 'plotly.js-dist-min'
import type { Observation } from '../types'

const props = defineProps<{
  observations: Observation[]
}>()

const chartContainer = ref<HTMLElement | null>(null)
let chartEl: HTMLElement | null = null

/**
 * Extracts month/year from timestamp for grouping
 * Returns formatted string like "Jan 2023" or "Invalid Date" if parsing fails
 */
const getMonth = (timestamp: string): string => {
  const date = new Date(timestamp)
  return isNaN(date.getTime())
    ? 'Invalid Date'
    : date.toLocaleString('en-GB', { month: 'short', year: 'numeric' })
}

/**
 * Main chart rendering function
 * Groups data by month and taxonomy level, then creates stacked bar chart
 */
const renderChart = () => {
  if (!chartContainer.value || typeof Plotly === 'undefined') return
  if (props.observations.length === 0) return

  // Determines the most specific taxonomy level available in the data
  // (species > genus > family > unknown)
  const taxonomyLevel = (() => {
    const sample = props.observations.find(obs => obs.properties.species !== 'All') || {
      properties: { species: '', genus: '', family: '' }
    }
    const { species, genus, family } = sample?.properties || {}
    if (species && species !== 'All') return 'species'
    if (genus && genus !== 'All') return 'genus'
    if (family && family !== 'All') return 'family'
    return 'unknown'
  })()

  // Groups observations by month and taxon
  const grouped: Record<string, Record<string, number>> = {}
  props.observations.forEach(obs => {
    const month = getMonth(obs.properties.timestamp)
    const key = taxonomyLevel === 'species' ? obs.properties.species
              : taxonomyLevel === 'genus' ? obs.properties.genus
              : obs.properties.family

    if (!grouped[month]) grouped[month] = {}
    grouped[month][key] = (grouped[month][key] || 0) + 1
  })

  const allMonths = Object.keys(grouped).sort((a, b) => new Date(a).getTime() - new Date(b).getTime())
  const allGroups = Array.from(new Set(
    props.observations.map(obs => {
      return taxonomyLevel === 'species' ? obs.properties.species
           : taxonomyLevel === 'genus' ? obs.properties.genus
           : obs.properties.family
    })
  ))

  // Colour palette for chart
  const colorPalette = [
    '#59a14f', '#4e79a7', '#f28e2b', '#e15759', '#76b7b2',
    '#edc949', '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab'
  ]
  const colorMap: Record<string, string> = {}
  allGroups.forEach((group, i) => {
    colorMap[group] = colorPalette[i % colorPalette.length]
  })

  // Prepares stacked traces
  const data: Plotly.Data[] = allGroups.map(group => {
    const counts = allMonths.map(month => grouped[month]?.[group] || 0)
    return {
      x: allMonths,
      y: counts,
      type: 'bar',
      name: group,
      marker: { color: colorMap[group] },
    }
  })

  // Chart layout configuration
  const layout: Partial<Plotly.Layout> = {
    barmode: 'stack',
    xaxis: {
      title: { text: 'Time' },
      tickangle: -45,
      type: 'category'
    },
    yaxis: {
      title: { text: 'Number of Observations' },
      rangemode: 'tozero'
    },
    margin: { t: 40, l: 50, r: 20, b: 100 },
    plot_bgcolor: '#f9f9f9',
    paper_bgcolor: '#fff',
    bargap: 0.1
  }

  const config = {
    responsive: true,
    displayModeBar: true
  }

  // Creates or updates the chart
  chartEl = chartContainer.value
  Plotly.newPlot(chartEl, data, layout, config)
}

onMounted(renderChart)

watch(() => props.observations, renderChart, { deep: true })

onUnmounted(() => {
  if (chartEl && typeof Plotly !== 'undefined') {
    Plotly.purge(chartEl)
    chartEl = null
  }
})
</script>

<template>
  <div ref="chartContainer" class="histogram-container"></div>
</template>

<style scoped>
.histogram-container {
  width: 100%;
  min-height: 400px;
  padding: 1rem;
  background-color: var(--color-surface, #ffffff);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.3s ease;
  overflow-x: auto;
}
.histogram-container:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
}
@media (max-width: 768px) {
  .histogram-container {
    padding: 0.5rem;
    min-height: 350px;
  }
}
</style>