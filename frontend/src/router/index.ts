import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '@/views/HomeView.vue'
import SpeciesList from '@/views/SpeciesList.vue'
import MapView from '@/components/MapView.vue'
import VisualizationsView from '@/views/VisualizationsView.vue'
import ImageGallery from '@/components/ImageGallery.vue'
import CommentSection from '@/components/CommentSection.vue'
import ObservationsView from '@/views/ObservationsView.vue'
import PieChartView from '@/components/PieChartView.vue'
import LineChart from '@/components/LineChart.vue'
import UploadForm from '@/views/UploadForm.vue'
import UserProfile from '@/views/UserProfile.vue'
import EditProfile from '@/views/EditProfile.vue'
import AdminDashboard from '@/views/AdminDashboard.vue'
import LoginPage from '@/views/LoginPage.vue'
import RegisterPage from '@/views/RegisterPage.vue'
import SuccessBanner from '@/components/SuccessBanner.vue'
import ForgotPassword from '@/components/ForgotPassword.vue'
import ResetPassword from '@/components/ResetPassword.vue'

const routes = [
  { path: '/', name: 'Home', component: HomeView },
  { path: '/auth/login', component: LoginPage },
  { path: '/auth/register', component: RegisterPage },
  { path: '/auth/forgot-password', component: ForgotPassword },
  { path: '/auth/reset-password', component: ResetPassword },
  { path: '/succesbanner', component: SuccessBanner },
  { path: '/species/:species_name', component: SpeciesList },
  { path: '/observations/:source_id', component: ObservationsView },
  { path: '/map', component: MapView },
  { path: '/piechart', component: PieChartView },
  { path: '/linechart', component: LineChart},
  { path: '/visualizations', name: 'Visualizations', component: VisualizationsView },
  { path: '/imagegallery', component: ImageGallery},
  { path: '/commentsection', component: CommentSection},
  { path: '/upload', component: UploadForm},

  { path: '/editprofile/:userId?', name: 'EditOtherProfile', component: EditProfile },
  { path: '/profile/:userId?', name: 'UserProfile', component: UserProfile },
  { path: '/admin/dashboard', component: AdminDashboard, meta: { requiresAuth: true, requiresAdmin: true }}
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const isLoggedIn = localStorage.getItem('token') !== null
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  if (to.meta.requiresAuth && !isLoggedIn) {
    return next('/auth/login')
  }

  if (to.meta.requiresAdmin && (!user.roles || !user.roles.includes('admin'))) {
    return next('/') // redirects to home page
  }

  next()
})

export default router