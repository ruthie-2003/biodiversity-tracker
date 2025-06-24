<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import Plotly from 'plotly.js-dist-min'
import type { Data, Layout, Config } from 'plotly.js-dist-min'
import type { Observation } from '../types'

const props = defineProps<{
  observations: Observation[]
}>()

const chartContainer = ref<HTMLElement | null>(null)
let chartEl: HTMLElement | null = null

/**
 * Creates/updates the horizontal bar chart showing species observation counts
 */
const renderChart = () => {
  if (!chartContainer.value || typeof Plotly === 'undefined') return

  // Counts observations per species
  const speciesCount: Record<string, number> = {}
  props.observations.forEach(obs => {
    const species = obs.properties.species || 'Unknown species'
    speciesCount[species] = (speciesCount[species] || 0) + 1
  })

  const labels = Object.keys(speciesCount)
  const values = Object.values(speciesCount)

  // Colour palette for bars
  const colors = [
    '#2ca02c', '#1f77b4', '#ff7f0e', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
  ]
  const colorCycle = (index: number) => colors[index % colors.length]

  // Chart data configuration
  const data: Data[] = [{
    type: 'bar',
    orientation: 'h',
    y: labels,
    x: values,
    marker: {
      color: labels.map((_, i) => colorCycle(i))
    },
    hoverinfo: 'x+y',
    text: values.map(v => `${v} obs`),
    textposition: 'auto'
  }]

  // Chart layout configuration
  const layout: Partial<Layout> = {
    height: Math.max(300, labels.length * 25),
    margin: { t: 20, b: 40, l: 120, r: 20 },
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      family: 'Inter, system-ui, sans-serif',
      size: 12
    },
    xaxis: {
      title: { text: 'Number of Observations' },
      showgrid: true,
      zeroline: true
    },
    yaxis: {
      automargin: true
    }
  }

  // Chart display settings
  const config: Partial<Config> = {
    responsive: true,
    displayModeBar: false
  }

  chartEl = chartContainer.value
  Plotly.react(chartEl, data, layout, config)
}

onMounted(() => {
  renderChart()
})

watch(() => props.observations, () => {
  renderChart()
}, { deep: true })

onUnmounted(() => {
  if (chartEl && typeof Plotly !== 'undefined') {
    Plotly.purge(chartEl)
    chartEl = null
  }
})
</script>

<template>
  <div class="chart-view">
    <div 
      ref="chartContainer" 
      class="chart-container"
      v-if="observations.length > 0"
    ></div>
    <div 
      v-else 
      class="no-data"
    >
      No species data available for the selected filters
    </div>
  </div>
</template>

<style scoped>
.chart-view {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow-x: auto;
}

.chart-container {
  width: 100%;
  min-height: 300px;
}

.no-data {
  color: var(--color-text-secondary);
  font-style: italic;
  text-align: center;
  width: 100%;
}
</style>