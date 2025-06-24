<template>
  <div class="container mx-auto px-4 py-8 max-w-3xl">
    <div class="mb-6">
      <router-link 
        :to="isCurrentUser ? '/profile' : `/profile/${userId}`"
        class="inline-flex items-center text-blue-700 hover:text-blue-800 transition-colors"
      >
        <svg class="mr-1" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        Back to Profile
      </router-link>
    </div>
    
    <h1 class="text-3xl font-bold mb-6">Edit Your Profile</h1>
    
    <div class="bg-white rounded-lg shadow-md overflow-hidden">
      <form @submit.prevent="handleSubmit" novalidate>
        <div class="grid md:grid-cols-2 gap-6 p-6">
          <!-- Profile Photo -->
          <div>
            <h2 class="text-xl font-semibold mb-4">Profile Photo</h2>
            <div class="mb-4">
              <div class="h-40 w-40 relative mx-auto md:mx-0">
                <div class="h-40 w-40 rounded-full overflow-hidden border-2 bg-gray-100 border-blue-500 relative">
                  <img 
                    v-if="profile_picture" 
                    :src="profile_picture" 
                    alt="Profile" 
                    class="absolute top-0 left-0 h-full w-full object-cover object-center bg-white"
                  />
                  <div v-else class="text-5xl text-gray-400 flex items-center justify-center h-full">
                    <span class="text-4xl" aria-hidden="true">👤</span>
                  </div>
                </div>
                <input
                  type="file"
                  id="profile-photo"
                  ref="fileInput"
                  class="hidden"
                  name="profile_picture"
                  accept="image/*"
                  @change="handlePhotoChange"
                  aria-label="Choose profile photo"
                />
              </div>
              <button 
                v-if="isCurrentUser"
                type="button"
                @click="$refs.fileInput.click()"
                class="text-sm text-blue-700 hover:text-blue-800"
              >
                Edit Photo
              </button>
              <button 
                v-if="profile_picture && isCurrentUser"
                type="button"
                @click="removePhoto"
                class="text-sm text-red-600 hover:text-red-700"
              >
                Remove Photo
              </button>
            </div>
          </div>
          
          <!-- Activity Stats -->
          <div class="bg-gray-50 p-4 rounded-lg">
            <h2 class="text-xl font-semibold mb-4">Activity Stats</h2>
            <div class="grid grid-cols-3 gap-2">
              <div v-for="(stat, index) in activityStats" :key="index" class="text-center">
                <p class="text-2xl font-bold text-blue-700">{{ stat.value }}</p>
                <p class="text-sm text-gray-600">{{ stat.label }}</p>
              </div>
            </div>
          </div>
        </div>
        
        <div class="border-t border-gray-200 p-6">
          <h2 class="text-xl font-semibold mb-4">Personal Information</h2>
          
          <!-- Display Name -->
          <div class="mb-6">
            <label for="displayName" class="block text-sm font-medium text-gray-700 mb-1">
              Display Name
              <span v-if="isAdmin && !isCurrentUser" class="text-xs text-yellow-600 ml-1">(Admin Edit)</span>
            </label>
            <input
              id="displayName"
              type="text"
              name="name"
              v-model.trim="name"
              :readonly="!(isCurrentUser || isAdmin)"
              placeholder="Enter your display name"
              class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          
          <!-- Bio -->
          <div class="mb-6">
            <label for="bio" class="block text-sm font-medium text-gray-700 mb-2">
              Bio (250 characters max)
            </label>
            <textarea
              id="bio"
              v-model="description"
              name="description"
              :readonly="!isCurrentUser && !isAdmin"
              placeholder="Tell us about your interests in biodiversity"
              maxlength="250"
              class="w-full p-3 border border-gray-300 rounded-lg h-32 resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            ></textarea>
            <p class="text-sm text-gray-500 mt-1">
              {{ description.length }}/250 characters
            </p>
          </div>
        </div>
        
        <div class="border-t border-gray-200 p-6 flex flex-wrap gap-4">
          <button 
            v-if="isCurrentUser || isAdmin"
            type="submit"
            class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            :title="isAdmin && !isCurrentUser ? 'Admin editing user profile' : 'Edit your profile'"
          >
            {{ isAdmin && !isCurrentUser ? 'Save User Changes' : 'Save Changes' }}
          </button>
          <button 
            v-if="isCurrentUser || isAdmin"
            type="button"
            @click="showDeleteConfirmation = true"
            class="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center"
            :title="isAdmin && !isCurrentUser ? 'Admin deleting user account' : 'Delete your account'"
          >
            <svg class="mr-1" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            {{ isAdmin && !isCurrentUser ? 'Delete User Account' : 'Delete Account' }}
          </button>
        </div>
      </form>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="showDeleteConfirmation" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" role="dialog" aria-modal="true" aria-labelledby="delete-title" aria-describedby="delete-desc">
      <div class="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
        <h3 id="delete-title" class="text-xl font-bold mb-4">Confirm Account Deletion</h3>
        <p id="delete-desc" class="mb-6">Are you sure you want to delete your account? This action cannot be undone.</p>
        <div class="flex justify-end space-x-4">
          <button 
            @click="showDeleteConfirmation = false"
            class="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button 
            @click="deleteAccount"
            class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Delete Account
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EditProfile',
  data() {
    return {
      userId: null,
      name: '',
      description: '',
      profile_picture: '',
      activityStats: [
        { label: 'Observations', value: 0 },
        { label: 'Species', value: 0 },
        { label: 'Locations', value: 0 }
      ],
      showDeleteConfirmation: false,
      isCurrentUser: false,
      originalProfile: {},  
      photoChanged: false,  
      isAdmin: false,
    };
  },
  created() {
    // Gets user ID from route params if editing another user
    this.userId = this.$route.params.userId || null;
    
    this.loadUserProfile();
  },
  methods: {
    /**
     * Loads user profile data from API
     */
    async loadUserProfile() {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found');
        }

        // Determines endpoint based on whether editing own profile or another user
        const endpoint = this.userId
          ? `http://localhost:8000/api/editprofile/${this.userId}/`
          : 'http://localhost:8000/api/editprofile/';

        const response = await fetch(endpoint, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          credentials: 'include'
        });

        if (!response.ok) {
          throw new Error(`Failed to load profile: ${response.statusText}`);
        }

        const data = await response.json();

        // Assigns fetched data to component state
        this.name = data.name || '';
        this.description = data.description || '';
        this.profile_picture = data.profile_picture || '';
        this.isCurrentUser = data.is_current_user || false;
        this.isAdmin = data.is_admin || false;

        // Updates activity stats
        this.activityStats = [
          { label: 'Observations', value: data.observations_count || 0 },
          { label: 'Species', value: data.species_count || 0 },
          { label: 'Locations', value: data.locations_count || 0 }
        ];

        // Stores original values for change detection
        this.originalProfile = {
          name: this.name,
          description: this.description,
          profile_picture: this.profile_picture,
        };
        this.photoChanged = false;

        this.isCurrentUser = data.is_current_user || false;
      } catch (error) {
        console.error('Error loading profile:', error);
        alert('Could not load profile information.');
      }
    },

    /**
     * Handles form submission for profile updates
     */
    async handleSubmit() {
      // Prevents editing someone else's profile without admin rights
      if (!(this.isCurrentUser || this.isAdmin)) {
        alert("You can't edit someone else's profile.");
        return;
      }

      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found');
        }

        const formData = new FormData();
        let hasChanges = false;

        // Checks for changes in name
        if (this.name !== this.originalProfile.name) {
          formData.append('name', this.name);
          hasChanges = true;
        }

        // Checks for changes in description
        if (this.description !== this.originalProfile.description) {
          formData.append('description', this.description);
          hasChanges = true;
        }

        // Handles photo changes
        if (this.photoChanged) {
          const fileInput = this.$refs.fileInput;
          if (fileInput && fileInput.files.length > 0) {
            // New photo uploaded
            formData.append('profile_picture', fileInput.files[0]);
          } else if (this.profile_picture === '') {
            // Photo was removed
            formData.append('profile_picture', 'true');
          }
          hasChanges = true;
        }

        // Don't proceed if no changes were made
        if (!hasChanges) {
          alert('No changes were made.');
          return;
        }
        
        console.log('Submitting with changes:');
        for (let [key, value] of formData.entries()) {
          console.log(key, value);
        }

        // Determines endpoint based on whether editing own profile or another user
        const endpoint = this.userId
          ? `http://localhost:8000/api/editprofile/${this.userId}/`
          : `http://localhost:8000/api/editprofile/`;

        // Sends PATCH request with form data
        const response = await fetch(endpoint, {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData?.message || 'Failed to update profile');
        }

        const result = await response.json();
        alert(result.message || 'Profile updated successfully');
        
        // Reloads profile to get updated data
        this.loadUserProfile();
      } catch (error) {
        console.error('Error updating profile:', error);
        alert(error.message);
      }
    },

    /**
     * Handles account deletion
     */
    async deleteAccount() {
      // Prevents deleting someone else's account without admin rights
      if (!(this.isCurrentUser || this.isAdmin)) {
        alert("You can't delete someone else's account.");
        this.showDeleteConfirmation = false;
        return;
      }

      // Extra confirmation
      if (!confirm('Are you absolutely sure you want to delete your account? This cannot be undone.')) {
        return;
      }

      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found');
        }

        // Determines endpoint based on whether deleting own account or another user
        const endpoint = this.userId
          ? `http://localhost:8000/api/editprofile/${this.userId}/`
          : `http://localhost:8000/api/editprofile/`;

        const response = await fetch(endpoint, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed to delete account');
        }

        // Cleans up and redirects if successful
        localStorage.removeItem('token');
        alert('Account deleted successfully.');
        this.showDeleteConfirmation = false;
    
        this.$router.push('/');
      } catch (error) {
        console.error('Error deleting account:', error);
        alert(error.message);
      }
    },

    /**
     * Handles profile photo file selection
     * @param {Event} event - File input change event
     */
    handlePhotoChange(event) {
      const file = event.target.files[0];
      if (!file) return;

      // Validates file type
      if (!file.type.startsWith('image/')) {
        alert('Please upload a valid image file.');
        return;
      }

      // Previews the selected image
      const reader = new FileReader();
      reader.onload = e => {
        this.profile_picture = e.target.result;
        this.photoChanged = true; 
      };
      reader.readAsDataURL(file);
    },

    /**
     * Removes the current profile photo
     */
    removePhoto() {
      this.profile_picture = '';
      this.photoChanged = true;
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = '';  // 
      }
    }
  }
};
</script>

<style scoped>

.container {
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
}

.max-w-3xl {
  max-width: 48rem;
}

.mx-auto {
  margin-left: auto;
  margin-right: auto;
}

.px-4 {
  padding-left: 1rem;
  padding-right: 1rem;
}

.py-8 {
  padding-top: 2rem;
  padding-bottom: 2rem;
}

.mb-6 {
  margin-bottom: 1.5rem;
}

.inline-flex {
  display: inline-flex;
}

.items-center {
  align-items: center;
}

.text-blue-700 {
  color: #2b6cb0;
}

.hover\:text-blue-800:hover {
  color: #2c5282;
}

.transition-colors {
  transition-property: background-color, border-color, color, fill, stroke;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 150ms;
}

.text-3xl {
  font-size: 1.875rem;
}

.font-bold {
  font-weight: 700;
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

.overflow-hidden {
  overflow: hidden;
}

.grid {
  display: grid;
}

.md\:grid-cols-2 {
  @media (min-width: 768px) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.gap-6 {
  gap: 1.5rem;
}

.p-6 {
  padding: 1.5rem;
}

.text-xl {
  font-size: 1.25rem;
}

.font-semibold {
  font-weight: 600;
}

.flex {
  display: flex;
}

.h-40 {
  height: 10rem;
}

.w-40 {
  width: 10rem;
}

.relative {
  position: relative;
}

.mx-auto {
  margin-left: auto;
  margin-right: auto;
}

.md\:mx-0 {
  @media (min-width: 768px) {
    margin-left: 0;
    margin-right: 0;
  }
}

.rounded-full {
  border-radius: 9999px;
}

.overflow-hidden {
  overflow: hidden;
}

.border-2 {
  border-width: 2px;
}

.border-blue-500 {
  border-color: #4299e1;
}

.border-gray-200 {
  border-color: #edf2f7;
}

.bg-gray-100 {
  background-color: #f7fafc;
}

.items-center {
  align-items: center;
}

.justify-center {
  justify-content: center;
}

.text-5xl {
  font-size: 3rem;
}

.text-gray-400 {
  color: #cbd5e0;
}

.hidden {
  display: none;
}

.absolute {
  position: absolute;
}

.bottom-0 {
  bottom: 0;
}

.right-0 {
  right: 0;
}

.bg-blue-500 {
  background-color: #4299e1;
}

.text-white {
  color: #ffffff;
}

.p-2 {
  padding: 0.5rem;
}

.cursor-pointer {
  cursor: pointer;
}

.shadow-md {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.hover\:bg-blue-600:hover {
  background-color: #3182ce;
}

.justify-center {
  justify-content: center;
}

.md\:justify-start {
  @media (min-width: 768px) {
    justify-content: flex-start;
  }
}

.mt-2 {
  margin-top: 0.5rem;
}

.space-x-2 > * + * {
  margin-left: 0.5rem;
}

.text-sm {
  font-size: 0.875rem;
}

.text-blue-700 {
  color: #2b6cb0;
}

.hover\:text-blue-800:hover {
  color: #2c5282;
}

.text-red-600 {
  color: #e53e3e;
}

.hover\:text-red-700:hover {
  color: #c53030;
}

.bg-gray-50 {
  background-color: #f9fafb;
}

.grid-cols-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.gap-2 {
  gap: 0.5rem;
}

.text-center {
  text-align: center;
}

.text-2xl {
  font-size: 1.5rem;
}

.text-gray-600 {
  color: #718096;
}

.border-t {
  border-top-width: 1px;
}

.border-gray-200 {
  border-color: #edf2f7;
}

.block {
  display: block;
}

.font-medium {
  font-weight: 500;
}

.mb-2 {
  margin-bottom: 0.5rem;
}

.w-full {
  width: 100%;
}

.p-3 {
  padding: 0.75rem;
}

.border {
  border-width: 1px;
}

.border-gray-300 {
  border-color: #e2e8f0;
}

.focus\:ring-2:focus {
  --tw-ring-offset-shadow: var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);
  --tw-ring-shadow: var(--tw-ring-inset) 0 0 0 calc(2px + var(--tw-ring-offset-width)) var(--tw-ring-color);
  box-shadow: var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow, 0 0 #0000);
}

.focus\:ring-blue-500:focus {
  --tw-ring-color: #4299e1;
}

.focus\:border-blue-500:focus {
  border-color: #4299e1;
}

.h-32 {
  height: 8rem;
}

.resize-none {
  resize: none;
}

.mt-1 {
  margin-top: 0.25rem;
}

.flex-wrap {
  flex-wrap: wrap;
}

.gap-4 {
  gap: 1rem;
}

.px-6 {
  padding-left: 1.5rem;
  padding-right: 1.5rem;
}

.py-2 {
  padding-top: 0.5rem;
  padding-bottom: 0.5rem;
}

.bg-blue-600 {
  background-color: #3182ce;
}

.hover\:bg-blue-700:hover {
  background-color: #2b6cb0;
}

.rounded-lg {
  border-radius: 0.5rem;
}

.bg-red-600 {
  background-color: #e53e3e;
}

.hover\:bg-red-700:hover {
  background-color: #c53030;
}

.object-cover {
  object-fit: cover;
}

/* Modal styles */
.fixed {
  position: fixed;
}

.inset-0 {
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
}

.bg-black {
  background-color: #000;
}

.bg-opacity-50 {
  --tw-bg-opacity: 0.5;
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

.justify-center {
  justify-content: center;
}

.p-4 {
  padding: 1rem;
}

.z-50 {
  z-index: 50;
}

.shadow-xl {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.max-w-md {
  max-width: 28rem;
}

.w-full {
  width: 100%;
}

.space-x-4 > * + * {
  margin-left: 1rem;
}

.border-gray-300 {
  border-color: #e2e8f0;
}

.hover\:bg-gray-50:hover {
  background-color: #f9fafb;
}
</style>