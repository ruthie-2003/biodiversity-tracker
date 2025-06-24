  <template>
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-3xl font-bold mb-8">Admin Dashboard</h1>
      
      <!-- Summary Statistics -->
      <section class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Summary Statistics</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div 
            v-for="stat in stats" 
            :key="stat.id"
            class="bg-white p-6 rounded-lg shadow-md border-b-4 border-blue-600 hover:transform hover:-translate-y-1 transition-transform duration-200"
          >
            <div class="flex items-start justify-between">
              <div>
                <p class="text-3xl font-bold text-blue-700">
                  {{ stat.label.includes('Completeness') ? `${stat.value}%` : stat.value }}
                </p>
                <p class="text-gray-600">{{ stat.label }}</p>
              </div>
              <div class="ml-4">
                <component :is="stat.icon" class="w-8 h-8 text-blue-600" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- User Management -->
      <section class="mb-8">
        <h2 class="text-xl font-semibold mb-4">User Management</h2>
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="mb-4 relative">
            <input
              type="text"
              placeholder="Search users"
              v-model="userSearch"
              class="w-full p-3 pl-10 border border-gray-300 rounded-md"
            />
            <svg class="absolute left-3 top-1/2 transform -translate-y-1/2 -mt-1 text-gray-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>
          
            <table class="min-w-full">
              <tbody class="divide-y divide-gray-200 overflow-y-auto max-h-[300px] min-h-[300px] scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100 block">
                <tr v-for="user in displayedUsers" :key="user.id" class="hover:bg-gray-50 table-row">
                  <td class="py-4 pl-4 pr-2">
                    <div class="flex items-center">
                      <div class="h-10 w-10 rounded-full overflow-hidden mr-3">
                        <img 
                          v-if="user.profile_picture"
                          :src="user.profile_picture" 
                          :alt="user.name"
                          class="h-full w-full object-cover"
                        />
                        <div v-else class="emoji-fallback text-xl">👤</div>
                      </div>
                      <div>
                        <p class="font-medium">{{ user.name }}</p>
                        <p class="text-sm text-gray-500">{{ user.role }} • Joined {{ user.activeDate }}</p>
                      </div>
                    </div>
                  </td>
                  <td class="py-4 px-2 text-right">
                    <button @click="goToEditProfile(user.id)" class="text-blue-600 hover:text-blue-800 mx-1 bg-transparent">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                      </svg>
                    </button>
                    <button 
                      @click="toggleBlockUser(user.id, !user.isBlocked)" 
                      :class="[
                        'mx-1 px-2 py-1 rounded transition-colors duration-200',
                        user.isBlocked 
                          ? 'bg-yellow-600 text-yellow-600 hover:bg-yellow-800' 
                          : 'bg-red-100 text-red-600 hover:bg-red-800'
                      ]" 
                      class="mx-1 bg-transparent"
                    >
                      <svg v-if="!user.isBlocked" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <!-- Block icon -->
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="4" y1="4" x2="20" y2="20"></line>
                      </svg>
                      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <!-- Unblock icon (checkmark) -->
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                      </svg>
                    </button>
                  </td>
                </tr>
                <tr v-if="displayedUsers.length === 0">
                  <td colspan="2" class="py-4 text-center text-gray-500">No users found</td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <div class="mt-4"></div>
      </section>
      
      <!-- Content Review -->
      <section class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Observation Review</h2>
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="mb-4 relative">
            <input
              type="text"
              placeholder="Search content"
              v-model="contentSearch"
              class="w-full p-3 pl-10 border border-gray-300 rounded-md"
            />
            <svg class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>
          <div class="overflow-x-auto max-h-[500px]" :class="{'overflow-y-auto': showAllContent}">
            <table class="min-w-full">
              <thead>
                <tr class="border-b border-gray-200">
                  <th class="py-3 px-4 text-left font-medium">Species</th>
                  <th class="py-3 px-4 text-left font-medium">Submitted by</th>
                  <th class="py-3 px-4 text-left font-medium">Location</th>
                  <th class="py-3 px-4 text-left font-medium">Date</th>
                  <th class="py-3 px-4 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200">
                <tr v-for="item in displayedContent" :key="item.id" class="hover:bg-gray-50">
                  <td class="py-3 px-4">
                    <router-link :to="`/observations/${item.source_id}`" class="flex items-center text-gray-800 hover:text-gray-900">
                      <div class="flex-shrink-0">
                      <div class="h-10 w-10 rounded-full overflow-hidden mr-3">
                        <template v-if="item.thumbnail">
                          <img 
                            :src="item.thumbnail" 
                            :alt="item.species"
                            class="h-10 w-10 object-cover"
                          />
                        </template>
                        <template v-else>
                          <div class="h-10 w-10 rounded-full flex items-center justify-center bg-gray-200 text-gray-500 text-xs">
                            No image
                          </div>
                        </template>
                      </div>
                        <span>{{ item.species }}</span>
                      </div>
                  </router-link>
                  </td>
                  <td class="py-3 px-4 text-gray-800 hover:text-gray-900"><router-link :to="`/observations/${item.source_id}`" class="contents">{{ item.submitter }}</router-link></td>
                  <td class="py-3 px-4 text-gray-800 hover:text-gray-900"><router-link :to="`/observations/${item.source_id}`" class="contents">{{ item.location }}</router-link></td>
                  <td class="py-3 px-4 text-gray-800 hover:text-gray-900"><router-link :to="`/observations/${item.source_id}`" class="contents">{{ item.date }}</router-link></td>
                  <td class="py-3 px-4 text-right">
                    <button @click.stop="reviewContent(item.id, 'verified')" class="text-green-600 hover:text-green-800 mx-1 bg-transparent">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                      </svg>
                    </button>
                    <button @click.stop="reviewContent(item.id, 'rejected')" class="text-red-600 hover:text-red-800 mx-1 bg-transparent">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="15" y1="9" x2="9" y2="15"></line>
                        <line x1="9" y1="9" x2="15" y2="15"></line>
                      </svg>
                    </button>
                  </td>
                </tr>
                <tr v-if="displayedContent.length === 0">
                  <td colspan="5" class="py-4 text-center text-gray-500">No pending reviews</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
      
      <!-- Quick Actions -->
      <section>
        <h2 class="text-xl font-semibold mb-4">Quick Actions</h2>
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="flex items-center mb-2">
            <svg class="w-6 h-6 text-blue-600 mr-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <div>
              <h3 class="font-medium">Export Data</h3>
              <p class="text-sm text-gray-500">CSV or JSON format</p>
            </div>
          </div>
          <button 
            @click="exportData('csv')"
            class="mt-2 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
            :disabled="exportLoading"
          >
            <span v-if="exportLoading">Exporting...</span>
            <span v-else>Export as CSV</span>
          </button>
            <button 
              @click="exportData('json')"
              class="mt-2 ml-2 px-4 py-2 rounded-md transition-colors"
              style="
                background-color: var(--color-primary-600) !important;
                color: white !important;
                margin-left: 0.5rem !important;
              "
              :style="{
                'background-color': exportLoading ? 'var(--color-primary-400)' : 'var(--color-primary-600)'
              }"
              :disabled="exportLoading"
            >
              <span v-if="exportLoading">Exporting...</span>
              <span v-else>Export as JSON</span>
            </button>
        </div>
      </section>
    </div>
  </template>

  <script>

  export default {
    name: 'AdminDashboard',
    data() {
      return {
        userSearch: '',
        contentSearch: '',
        stats: [],
        users: [],
        contentItems: [],
        showAllContent: false,
        exportLoading: false,
        loading: {
          stats: true,
          users: true,
          content: true
        }
      }
    },
    computed: {
      // Filtered and sorted users
      filteredUsers() {
        if (!Array.isArray(this.users)) return [];
        return this.users
          .filter(user => user.name.toLowerCase().includes(this.searchQuery.toLowerCase()))
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      },
      // Users to display with search filtering
      displayedUsers() {
        return this.users.filter(user =>
          user.name.toLowerCase().includes(this.userSearch.toLowerCase())
        ).slice(0,4); 
      },
      // Content to display with search filtering
      displayedContent() {
        let filtered = this.contentItems;

        if (this.contentSearch) {
          const query = this.contentSearch.toLowerCase();
          filtered = filtered.filter(item =>
            item.species.toLowerCase().includes(query) ||
            item.submitter.toLowerCase().includes(query) ||
            item.location.toLowerCase().includes(query)
          );
        }

        return this.showAllContent ? filtered : filtered.slice(0, 4);
      },
      isLoading() {
        return this.loading.stats || this.loading.users || this.loading.content
      }
    },
    methods: {
      // Fetches summary statistics
      async fetchStats() {
        try {
          this.loading.stats = true
          const token = localStorage.getItem('token')
          const response = await fetch('http://localhost:8000/api/admin/stats/', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
          
          if (!response.ok) throw new Error('Failed to fetch stats')
          const data = await response.json()
          this.stats = data?.stats || []
        } catch (error) {
          console.error('Error fetching stats:', error)
          this.stats = []
        } finally {
          this.loading.stats = false
        }
      },
      // Fetches user data
      async fetchUsers() {
        try {
          this.loading.users = true
          const token = localStorage.getItem('token')
          const response = await fetch('http://localhost:8000/api/admin/recent-users/', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
          
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'Failed to fetch users');
          }

          const data = await response.json();
          console.log('Users API response:', data)
          this.users = data.users || [];
        } catch (error) {
          console.error('Error fetching users:', error)
          this.users = []
        } finally {
          this.loading.users = false
        }
      },
      // Navigates to user edit page
      goToEditProfile(userId) {
        this.$router.push(`/editprofile/${userId}`);
      },
      // Fetches observations for review
      async fetchContent() {
        try {
          this.loading.content = true
          const token = localStorage.getItem('token')
          const response = await fetch('http://localhost:8000/api/admin/pending-content/', {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          })
          
          if (!response.ok) throw new Error('Failed to fetch content')
          const data = await response.json()
          console.log('Users API response:', data)
          this.contentItems = (data?.content || []).map(item => ({
            ...item,
            thumbnail: item.thumbnail || 'https://placehold.co/150x150?text=No+Image'
          }))
        } catch (error) {
          console.error('Error fetching content:', error)
          this.contentItems = []
        } finally {
          this.loading.content = false
        }
      },
      // Reviews observations (approve/reject)
      async reviewContent(observationId, newStatus) {
        try {
          const token = localStorage.getItem('token');
          const response = await fetch('http://localhost:8000/api/admin/pending-content/', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              observation_id: observationId,
              status: newStatus,
            })
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Failed to update status`);
          }

          // On approval, removes the item from the local list to update the UI instantly
          this.contentItems = this.contentItems.filter(item => item.id !== observationId);

          alert(`Observation successfully ${newStatus}!`);

        } catch (error) {
          console.error('Error reviewing content:', error);
          alert(`Error: ${error.message}`);
        }
      },
      // Exports data in specified format
      async exportData(format) {
        this.exportLoading = true;
        try {
          const token = localStorage.getItem('token');
          const response = await fetch(`http://localhost:8000/api/export/${format}/`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          });

          if (!response.ok) throw new Error(`Export failed with status ${response.status}`);

          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;

          // Uses appropriate extension for downloaded file:
          const fileExtension = format === 'csv' ? 'zip' : 'json'; 
          link.setAttribute('download', `biodiversity_export.${fileExtension}`);

          document.body.appendChild(link);
          link.click();

          // Cleanup:
          link.remove();
          window.URL.revokeObjectURL(url);
        } catch (error) {
          console.error('Export failed:', error);
          alert('Export failed. Please try again.');
        } finally {
          this.exportLoading = false;
        }
      },
      // Toggles showing all users
      toggleAllUsers() {
        this.showAllUsers = !this.showAllUsers
      },
      // Toggles showing all observations
      toggleAllContent() {
        this.showAllContent = !this.showAllContent
      },
      // Toggles user block status
      async toggleBlockUser(userId) {
        try {
          const token = localStorage.getItem('token');
          if (!token) {
            throw new Error('No authentication token found');
          }

          const response = await fetch('http://localhost:8000/api/admin/recent-users/', {
            method: 'POST',
            credentials: 'include',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              user_id: userId
            })
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'Failed to toggle block status.');
          }

          const data = await response.json();
          console.log('User block toggled:', data);

          // Updates local user state without full refetch
          this.users = this.users.map(user => 
            user.id === userId ? { ...user, isBlocked: data.isBlocked } : user
          );
        } catch (error) {
          console.error('Error toggling user block:', error);
          alert('Unable to change user block status. Please try again.');
        }
      }
    },
    async created() {
      await Promise.all([
        this.fetchStats(),
        this.fetchUsers(),
        this.fetchContent()
      ])
    },
    // Icon components used in the stats cards
    components: {
      ClipboardListIcon: {
        template: `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
            <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
          </svg>
        `
      },
      UsersIcon: {
        template: `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
        `
      },
      CheckCircleIcon: {
        template: `
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        `
      }
    }
  }
  </script>

  <style scoped>

  button:disabled {
    opacity: 0.7 !important;
    cursor: not-allowed !important;
    background-color: var(--color-green-500) !important;
  }
  
  .container {
    max-width: 1200px;
    margin-left: auto;
    margin-right: auto;
  }

  .mx-auto {
    margin-left: auto;
    margin-right: auto;
  }

  .px-4 {
    padding-left: 3rem;
    padding-right: 3rem;
  }

  .py-8 {
    padding-top: 2rem;
    padding-bottom: 2rem;
  }

  .text-3xl {
    font-size: 1.875rem;
  }

  .font-bold {
    font-weight: 700;
  }

  .mb-8 {
    margin-bottom: 2rem;
  }

  .grid {
    display: grid;
  }

  .grid-cols-1 {
    grid-template-columns: repeat(1, minmax(0, 1fr));
  }

  @media (min-width: 768px) {
    .md\:grid-cols-2 {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (min-width: 1024px) {
    .lg\:grid-cols-4 {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
  }

  .gap-4 {
    gap: 1rem;
  }

  .bg-white {
    background-color: #ffffff;
  }

  .p-6 {
    padding: 1.5rem;
  }

  .rounded-lg {
    border-radius: 0.5rem;
  }

  .shadow-md {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }

  .border-b-4 {
    border-bottom-width: 4px;
  }

  .border-blue-600 {
    border-color: #3182ce;
  }

  .hover\:transform:hover {
    transform: translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y));
  }

  .hover\:-translate-y-1:hover {
    --tw-translate-y: -0.25rem;
  }

  .transition-transform {
    transition-property: transform;
    transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
    transition-duration: 200ms;
  }

  .flex {
    display: flex;
  }

  .items-start {
    align-items: flex-start;
  }

  .justify-between {
    justify-content: space-between;
  }

  .text-blue-700 {
    color: #2b6cb0;
  }

  .text-gray-600 {
    color: #718096;
  }

  .ml-4 {
    margin-left: 1rem;
  }

  .w-8 {
    width: 2rem;
  }

  .h-8 {
    height: 2rem;
  }

  .text-blue-600 {
    color: #3182ce;
  }

  .text-xl {
    font-size: 1.25rem;
  }

  .font-semibold {
    font-weight: 600;
  }

  .mb-4 {
    margin-bottom: 1rem;
  }

  .relative {
    position: relative;
  }

  .w-full {
    width: 100%;
  }

  .p-3 {
    padding: 0.75rem;
  }

  .pl-10 {
    padding-left: 2.5rem;
  }

  .border {
    border-width: 1px;
  }

  .border-gray-300 {
    border-color: #e2e8f0;
  }

  .rounded-md {
    border-radius: 0.375rem;
  }

  .absolute {
    position: absolute;
  }

  .left-3 {
    left: 0.75rem;
  }

  .top-1\/2 {
    top: 50%;
  }

  .transform {
    transform: translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y));
  }

  .-translate-y-1\/2 {
    --tw-translate-y: -50%;
  }

  .text-gray-400 {
    color: #cbd5e0;
  }

  .overflow-x-auto {
    overflow-x: auto;
  }

  .min-w-full {
    min-width: 100%;
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

  .py-4 {
    padding-top: 1rem;
    padding-bottom: 1rem;
  }

  .pl-4 {
    padding-left: 1rem;
  }

  .pr-2 {
    padding-right: 0.5rem;
  }

  .items-center {
    align-items: center;
  }

  .h-10 {
    height: 2.5rem;
  }

  .w-10 {
    width: 2.5rem;
  }

  .rounded-full {
    border-radius: 9999px;
  }

  .bg-blue-100 {
    background-color: #ebf8ff;
  }

  .text-blue-700 {
    color: #2b6cb0;
  }

  .font-semibold {
    font-weight: 600;
  }

  .mr-3 {
    margin-right: 0.75rem;
  }

  .font-medium {
    font-weight: 500;
  }

  .text-sm {
    font-size: 0.875rem;
  }

  .text-gray-500 {
    color: #a0aec0;
  }

  .text-right {
    text-align: right;
  }

  .px-2 {
    padding-left: 0.5rem;
    padding-right: 0.5rem;
  }

  .hover\:text-blue-600:hover {
    color: #3182ce;
  }

  .mx-1 {
    margin-left: 0.25rem;
    margin-right: 0.25rem;
  }

  .hover\:text-red-600:hover {
    color: #e53e3e;
  }

  .mt-4 {
    margin-top: 1rem;
  }

  .text-blue-700 {
    color: #2b6cb0;
  }

  .border-blue-700 {
    border-color: #2b6cb0;
  }

  .px-4 {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .py-2 {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
  }

  .hover\:bg-blue-50:hover {
    background-color: #ebf8ff;
  }

  .border-b {
    border-bottom-width: 1px;
  }

  .py-3 {
    padding-top: 0.75rem;
    padding-bottom: 0.75rem;
  }

  .text-left {
    text-align: left;
  }

  .rounded-md {
    border-radius: 0.375rem;
  }

  .bg-gray-200 {
    background-color: #edf2f7;
  }

  .overflow-hidden {
    overflow: hidden;
  }

  .object-cover {
    object-fit: cover;
  }

  .text-green-600 {
    color: #38a169;
  }

  .hover\:text-green-800:hover {
    color: #276749;
  }

  .text-red-600 {
    color: #e53e3e;
  }

  .hover\:text-red-800:hover {
    color: #9b2c2c;
  }

  .w-6 {
    width: 1.5rem;
  }

  .h-6 {
    height: 1.5rem;
  }

  .mr-3 {
    margin-right: 0.75rem;
  }

  .mt-2 {
    margin-top: 0.5rem;
  }

  .bg-blue-600 {
    background-color: #3182ce;
  }

  .text-white {
    color: #ffffff;
  }

  .hover\:bg-blue-700:hover {
    background-color: #2b6cb0;
  }

  .contents {
    display: contents;
    color: inherit;
  }

  .text-gray-800 {
    color: var(--color-neutral-800);
  }

  .hover\:text-gray-900:hover {
    color: var(--color-neutral-900);
  }
  </style>