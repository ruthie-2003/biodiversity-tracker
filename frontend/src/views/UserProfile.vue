<template>
  <div class="container mx-auto px-4 py-8" v-if="user">
    <!-- User Profile Header -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <div class="flex flex-wrap items-center">
        <!-- Profile Picture -->
        <div class="h-32 w-32 sm:h-40 sm:w-40 rounded-full overflow-hidden border-2 border-blue-500 mr-6 flex-shrink-0">
          <img 
            v-if="user.profile_picture" 
            :src="user.profile_picture" 
            alt="User profile picture"
            class="h-full w-full object-cover"
            loading="lazy"
            decoding="async"
            width="160" height="160"
          >
          <div v-else class="h-full w-full bg-gray-200 flex items-center justify-center text-gray-400 text-4xl rounded-full">
            👤
          </div>
        </div>
        
        <div class="flex-1 min-w-0">
          <div class="flex flex-wrap items-center justify-between">
            <div>
              <h1 class="text-2xl font-bold">{{ user.name || user.username }}</h1>
              <p class="text-gray-600">Member since {{ formatDate(user.created_at) }}</p>
            </div>
            <router-link 
              v-if="isCurrentUser || isAdmin"
              :to="editProfileLink"
              class="mt-2 sm:mt-0 px-4 py-2 bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors flex items-center"
            >
              <svg class="mr-1" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
                {{ isAdmin && !isCurrentUser ? 'Edit User Profile' : 'Edit Profile' }}
            </router-link>

            <!-- Export Data Buttons -->
            <div v-if="isCurrentUser || isAdmin" class="flex" style="gap: 1rem;">
              <button 
                @click="exportData('json')" 
                :disabled="isExporting"
                class="export-json-btn px-4 py-2 rounded-md flex items-center"
              >
                <svg class="mr-1" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                {{ isExporting ? 'Exporting...' : 'Export as JSON' }}
              </button>
              <button 
                @click="exportData('csv')" 
                :disabled="isExporting"
                class="export-csv-btn px-4 py-2 rounded-md flex items-center"
              >
                <svg class="mr-1" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                {{ isExporting ? 'Exporting...' : 'Export as CSV' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Submitted Observations -->
    <div class="bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 class="text-xl font-semibold mb-4">Submitted Observations</h2>
      
      <div v-if="observations.length > 0">
        <div
          v-if="!showAllObservations"
          class="overflow-x-auto"
        >
          <table class="min-w-full">
            <thead>
              <tr class="border-b border-gray-200">
                <th class="py-3 px-4 text-left">Date</th>
                <th class="py-3 px-4 text-left">Species</th>
                <th class="py-3 px-4 text-left">Location</th>
                <th class="py-3 px-4 text-left">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <template v-for="obs in observations.slice(0,3)" :key="obs._id">
                <tr class="hover:bg-gray-50 cursor-pointer" @click="goToObservation(obs.source_id)">
                <td class="py-3 px-4">
                    {{ formatDate(obs.timestamp) }}
                </td>
                <td class="py-3 px-4">
                  <div v-if="obs.common_name">{{ obs.common_name }} ({{ obs.species }})</div>
                  <div v-else>{{ obs.species }}</div>
                </td>
                <td class="py-3 px-4">{{ obs.location_name || obs.region || obs.country || 'Unknown location' }}</td>
                <td class="py-3 px-4">
                  <span :class="statusClass(obs.status)">
                    {{ obs.status === 'verified' ? 'Verified' : 'Pending' }}
                  </span>
                </td>
                </tr>
              </template>
            </tbody>
          </table>

          <div class="mt-4 text-center">
            <button
              v-if="observations.length > 3"
              @click="showAllObservations = true"
              class="px-4 py-2 rounded transition-colors"
              style="background-color: var(--color-primary-600); color: white;"
            >
              Show More
            </button>
          </div>
        </div>

        <!-- Scrollable full observation list -->
        <div v-else class="max-h-96 overflow-y-auto border rounded-md">
          <table class="min-w-full">
            <thead class="sticky top-0 bg-white shadow">
              <tr class="border-b border-gray-200">
                <th class="py-3 px-4 text-left">Date</th>
                <th class="py-3 px-4 text-left">Species</th>
                <th class="py-3 px-4 text-left">Location</th>
                <th class="py-3 px-4 text-left">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <template v-for="obs in observations" :key="obs._id">
                <tr class="hover:bg-gray-50 cursor-pointer" @click="goToObservation(obs.source_id)">
                <td class="py-3 px-4">{{ formatDate(obs.timestamp) }}</td>
                <td class="py-3 px-4">
                  <div v-if="obs.common_name">{{ obs.common_name }} ({{ obs.species }})</div>
                  <div v-else>{{ obs.species }}</div>
                </td>
                <td class="py-3 px-4">{{ obs.location_name || 'Unknown location' }}</td>
                <td class="py-3 px-4">
                  <span :class="statusClass(obs.status)">
                    {{ obs.status === 'verified' ? 'Verified' : 'Pending' }}
                  </span>
                </td>
                </tr>
              </template>
            </tbody>
          </table>
          <div class="text-center my-4">
            <button
              @click="showAllObservations = false"
              class="px-4 py-2 rounded transition-colors"
              style="background-color: var(--color-neutral-300); color: var(--color-neutral-800);"
            >
              Show Less
            </button>
          </div>
        </div>
      </div>
      <div v-else class="text-gray-500 py-4">No observations submitted yet.</div>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Statistics -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-xl font-semibold mb-4">Statistics</h2>
        <div class="space-y-4">
          <div class="flex justify-between items-center">
            <span class="text-gray-600">Total Observations</span>
            <span class="font-medium">{{ stats.total_observations }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">Verified Entries</span>
            <span class="font-medium">{{ stats.verified_entries }}</span>
          </div>
          <div class="flex justify-between items-center">
            <span class="text-gray-600">Comments</span>
            <span class="font-medium">{{ stats.comments_count }}</span>
          </div>
        </div>
      </div>
      
      <!-- Recent Activity -->
      <div class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-xl font-semibold mb-4">Recent Activity</h2>
        <div class="space-y-4">
          <div v-for="activity in recentActivity" :key="activity._id" class="border-l-2 border-blue-500 pl-4 py-1">
            <div class="flex items-start">
              <svg class="mr-2 text-blue-500 flex-shrink-0" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path :d="activity.icon"></path>
              </svg>
              <div>
                <p class="text-gray-800">{{ activity.text }}</p>
                <p class="text-xs text-gray-500">{{ formatTimeAgo(activity.timestamp) }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="flex justify-center items-center h-screen">
    <div class="text-gray-500">Loading profile...</div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

export default {
  name: 'UserProfile',
  props: {
    userId: {
      type: String,
      default: null
    }
  },
  setup(props) {
    const route = useRoute()
    const router = useRouter()
    const showSidebar = ref(false)
    const showAllObservations = ref(false)

    // User data
    const user = ref(null)
    const observations = ref([])
    const stats = ref({
      total_observations: 0,
      verified_entries: 0,
      comments_count: 0
    })
    const recentActivity = ref([])

    const loading = ref(true)
    const isExporting = ref(false)

    // Computes whether we're viewing our own profile or someone else's
    const userId = computed(() => props.userId || route.params.userId)

    const isCurrentUser = computed(() => user.value?.is_current_user === true)

    const isAdmin = computed(() => user.value?.is_admin === true)

    // Generates proper edit link based on context
    const editProfileLink = computed(() => {
      const id = [null, undefined, ''].includes(userId.value) 
        ? null 
        : userId.value;
      
      return id && id !== 'undefined' 
        ? `/editprofile/${id}` 
        : `/editprofile/`;
    });

    // Fetches user profile and observation data
    const fetchProfile = async () => {
      try {
        // Uses different endpoints for viewing own profile vs others'
        const url = userId.value 
          ? `http://localhost:8000/api/profile/${userId.value}` 
          : 'http://localhost:8000/api/profile'
        
        const response = await axios.get(url, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        })

        user.value = response.data.user
        observations.value = response.data.observations
        stats.value = response.data.stats

        // Generates activity feed from observations and comments
        generateRecentActivity(response.data.observations, response.data.recent_activity)

      } catch (error) {
        console.error('Error fetching profile:', error)
      } finally {
        loading.value = false
      }
    }

    // Handles data export in different formats
    async function exportData(formatType) {
      let downloadUrl = null;
      let link = null;
      
      try {
        isExporting.value = true;
        const token = localStorage.getItem('token');
        
        if (!token) {
          throw new Error('Authentication error. Please log in again.');
        }

        let url = `http://localhost:8000/api/export/${formatType}/`;
        let fileName = `${user.value?.username || 'user'}_export.${formatType === 'csv' ? 'zip' : 'json'}`;

        // Admins can export other users' data by including target_user_id
        if (isAdmin.value && !isCurrentUser.value && userId.value) {
          url += `?target_user_id=${encodeURIComponent(userId.value)}`;
        }

        const response = await fetch(url, {
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
          const errorJson = await response.json().catch(() => ({}));
          throw new Error(errorJson.error || `Export failed: ${response.statusText}`);
        }

        // Creates download link and trigger click
        const blob = await response.blob();
        downloadUrl = window.URL.createObjectURL(blob);
        link = document.createElement('a');
        link.href = downloadUrl;
        link.setAttribute('download', fileName);
        document.body.appendChild(link);
        link.click();

        // Cleans up after short delay to ensure download starts
        setTimeout(() => {
          if (link && link.parentNode) {
            document.body.removeChild(link);
          }
          if (downloadUrl) {
            window.URL.revokeObjectURL(downloadUrl);
          }
        }, 100);
        
      } catch (error) {
        console.error('Export failed:', error);
        alert(`Export failed: ${error.message}`);
      } finally {
        isExporting.value = false;
      }
    }

    // Generates activity feed from observations and comments
    const generateRecentActivity = (userObservations, commentActivity) => {
      const activities = [];

      // Adds the latest observation if available
      if (userObservations && userObservations.length > 0) {
        const latestObs = userObservations[0]; 
        activities.push({
          _id: `obs-${latestObs._id}`,
          text: `Added a new observation of ${latestObs.common_name || latestObs.species}`,
          timestamp: new Date(latestObs.timestamp),
          source_id: latestObs.source_id,
          icon: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8z' 
        });
      }

      // Adds the latest comment activity if available
      if (commentActivity) {
        activities.push({
          _id: `comment-${commentActivity.timestamp}`,
          text: commentActivity.text,
          timestamp: new Date(commentActivity.timestamp),
          icon: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' 
        });
      }
      
      // Sorts by timestamp (newest first)
      activities.sort((a, b) => b.timestamp - a.timestamp);

      recentActivity.value = activities;
    }

    // Formats date
    const formatDate = (date) => {
      return dayjs(date).format('MMM D, YYYY')
    }

    // Formats as relative time
    const formatTimeAgo = (date) => {
      return dayjs(date).fromNow()
    }

    // Status badge styling
    const statusClass = (status) => {
      return {
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium': true,
        'bg-green-100 text-green-800': status === 'verified',
        'bg-yellow-100 text-yellow-800': status !== 'verified'
      }
    }

    // Navigates to observation detail
    const goToObservation = (sourceId) => {
      router.push({ path: `/observations/${sourceId}` })
    }

    onMounted(() => {
      const token = localStorage.getItem('token')
      if (!token) {
        router.push('/auth/login')
        return
      }
      fetchProfile()
    })

    return {
      // Exposes to template
      user,
      observations,
      stats,
      recentActivity,
      loading,
      isCurrentUser,
      formatDate,
      formatTimeAgo,
      statusClass,
      showSidebar,
      showAllObservations,
      router,
      goToObservation,
      editProfileLink,
      isAdmin,
      exportData,
      isExporting,
    }
  }
}
</script>

<style scoped>

.export-csv-btn {
  background-color: var(--color-secondary-600) !important;
  color: white !important;
  border: none !important;
  transition: background-color var(--transition-fast) !important;
}

.export-csv-btn:hover:not(:disabled) {
  background-color: var(--color-secondary-700) !important;
}

.export-csv-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.export-json-btn {
  background-color: var(--color-primary-600);
  color: white;
  border: none;
  transition: background-color var(--transition-fast);
}

.export-json-btn:hover:not(:disabled) {
  background-color: var(--color-primary-700);
}

.export-json-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

button:hover {
  transition: background-color var(--transition-fast);
}

button[style*="--color-primary-600"]:hover {
  background-color: var(--color-primary-700) !important;
}

button[style*="--color-neutral-300"]:hover {
  background-color: var(--color-neutral-400) !important;
}

.container {
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
}

.container img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain; 
  display: block; 
}

.cursor-pointer {
  cursor: pointer;
}

tr:hover {
  background-color: #f7fafc;
}

.bg-white {
  background-color: #ffffff;
}

.rounded-lg {
  border-radius: 0.5rem;
}

.shadow-md {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.p-6 {
  padding: 1.5rem;
}

.mb-6 {
  margin-bottom: 1.5rem;
}

.flex {
  display: flex;
}

.flex-wrap {
  flex-wrap: wrap;
}

.items-center {
  align-items: center;
}

.h-24 {
  height: 6rem;
}

.w-24 {
  width: 6rem;
}

.bg-gray-200 {
  background-color: #edf2f7;
}

.text-gray-400 {
  color: #cbd5e0;
}

.text-4xl {
  font-size: 2.25rem;
}

.mr-6 {
  margin-right: 1.5rem;
}

.flex-1 {
  flex: 1 1 0%;
}

.min-w-0 {
  min-width: 0;
}

.justify-between {
  justify-content: space-between;
}

.text-2xl {
  font-size: 1.5rem;
}

.font-bold {
  font-weight: 700;
}

.text-gray-600 {
  color: #718096;
}

.mt-2 {
  margin-top: 0.5rem;
}

.sm\:mt-0 {
  @media (min-width: 640px) {
    margin-top: 0;
  }
}

.px-4 {
  padding-left: 1rem;
  padding-right: 1rem;
}

.py-2 {
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
}

.bg-blue-50 {
  background-color: #ebf8ff;
}

.text-blue-700 {
  color: #2b6cb0;
}

.hover\:bg-blue-100:hover {
  background-color: #bee3f8;
}

.transition-colors {
  transition-property: background-color, border-color, color, fill, stroke;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

.rounded-md {
  border-radius: 0.375rem;
}

.text-xl {
  font-size: 1.25rem;
}

.font-semibold {
  font-weight: 600;
}

.overflow-x-auto {
  overflow-x: auto;
}

.min-w-full {
  min-width: 100%;
}

.border-b {
  border-bottom-width: 1px;
}

.border-gray-200 {
  border-color: #edf2f7;
}

.py-3 {
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

.px-4 {
  padding-left: 1rem;
  padding-right: 1rem;
}

.text-left {
  text-align: left;
}

.divide-y > :not([hidden]) ~ :not([hidden]) {
  --tw-divide-y-reverse: 0;
  border-top-width: calc(1px * calc(1 - var(--tw-divide-y-reverse)));
  border-bottom-width: calc(1px * var(--tw-divide-y-reverse));
}

.divide-gray-200 > :not([hidden]) ~ :not([hidden]) {
  --tw-divide-opacity: 1;
  border-color: rgba(237, 242, 247, var(--tw-divide-opacity));
}

.hover\:bg-gray-50:hover {
  background-color: #f7fafc;
}

.inline-flex {
  display: inline-flex;
}

.items-center {
  align-items: center;
}

.px-2\.5 {
  padding-left: 0.625rem;
  padding-right: 0.625rem;
}

.py-0\.5 {
  padding-top: 0.125rem;
  padding-bottom: 0.125rem;
}

.rounded-full {
  border-radius: 9999px;
}

.text-xs {
  font-size: 0.75rem;
}

.font-medium {
  font-weight: 500;
}

.bg-green-100 {
  background-color: #f0fff4;
}

.text-green-800 {
  color: #276749;
}

.bg-yellow-100 {
  background-color: #fffff0;
}

.text-yellow-800 {
  color: #975a16;
}

.grid {
  display: grid;
}

.grid-cols-1 {
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

.md\:grid-cols-2 {
  @media (min-width: 768px) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.gap-6 {
  gap: 1.5rem;
}

.space-y-4 > :not([hidden]) ~ :not([hidden]) {
  --tw-space-y-reverse: 0;
  margin-top: calc(1rem * calc(1 - var(--tw-space-y-reverse)));
  margin-bottom: calc(1rem * var(--tw-space-y-reverse));
}

.justify-between {
  justify-content: space-between;
}

.border-l-2 {
  border-left-width: 2px;
}

.border-blue-500 {
  border-color: #4299e1;
}

.pl-4 {
  padding-left: 1rem;
}

.py-1 {
  padding-top: 0.25rem;
  padding-bottom: 0.25rem;
}

.items-start {
  align-items: flex-start;
}

.text-blue-500 {
  color: #4299e1;
}

.flex-shrink-0 {
  flex-shrink: 0;
}

.text-gray-800 {
  color: #2d3748;
}

.text-xs {
  font-size: 0.75rem;
}

.text-gray-500 {
  color: #a0aec0;
}
</style>