import { createRouter, createWebHistory } from 'vue-router';

// Import layouts
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import OnboardingLayout from '@/layouts/OnboardingLayout.vue';

// Lazy load route components for better performance
const Dashboard = () => import('@/views/Dashboard.vue');
const DocumentGeneration = () => import('@/views/DocumentGeneration.vue');
const TemplateMarketplace = () => import('@/views/TemplateMarketplace.vue');
const TrackingMatrix = () => import('@/views/TrackingMatrix.vue');
const ReviewDashboard = () => import('@/views/ReviewDashboard.vue');
const Settings = () => import('@/views/Settings.vue');
const Onboarding = () => import('@/views/Onboarding.vue');


const routes = [
  {
    path: '/',
    name: 'root',
    redirect: '/dashboard'
  },
  {
    path: '/onboarding',
    name: 'onboarding',
    component: OnboardingLayout,
    meta: {
      requiresAuth: false,
      skipOnboarding: true,
      title: 'Welcome to DevDocAI'
    },
    children: [
      {
        path: '',
        component: Onboarding
      }
    ]
  },
  {
    path: '/',
    component: DefaultLayout,
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: Dashboard,
        meta: {
          requiresAuth: false,
          requiresOnboarding: true,
          title: 'Dashboard',
          breadcrumb: 'Dashboard'
        }
      },
      {
        path: 'generate',
        name: 'generate',
        component: DocumentGeneration,
        meta: {
          requiresOnboarding: true,
          title: 'Generate Documentation',
          breadcrumb: 'Generate'
        }
      },
      {
        path: 'studio',
        name: 'studio',
        component: DocumentGeneration,
        meta: {
          requiresOnboarding: true,
          title: 'Documentation Studio',
          breadcrumb: 'Studio'
        }
      },
      {
        path: 'templates',
        name: 'templates',
        component: TemplateMarketplace,
        meta: {
          requiresOnboarding: true,
          title: 'Template Marketplace',
          breadcrumb: 'Templates'
        }
      },
      {
        path: 'tracking',
        name: 'tracking',
        component: TrackingMatrix,
        meta: {
          requiresOnboarding: true,
          title: 'Tracking Matrix',
          breadcrumb: 'Tracking'
        }
      },
      {
        path: 'review',
        name: 'review',
        component: ReviewDashboard,
        meta: {
          requiresOnboarding: true,
          title: 'Review Dashboard',
          breadcrumb: 'Review'
        }
      },
      {
        path: 'settings',
        name: 'settings',
        component: Settings,
        meta: {
          requiresOnboarding: true,
          title: 'Settings',
          breadcrumb: 'Settings'
        }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: 'Page Not Found'
    }
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    } else if (to.hash) {
      return {
        el: to.hash,
        behavior: 'smooth'
      };
    } else {
      return { top: 0 };
    }
  }
});

// Navigation guards
router.beforeEach(async (to, from, next) => {
  // Set page title
  if (to.meta.title) {
    document.title = `${to.meta.title} | DevDocAI v3.6.0`;
  }

  // For now, just proceed with navigation
  // TODO: Add authentication and onboarding checks later
  next();
});

// Handle errors
router.onError((error) => {
  console.error('Router error:', error);
  // Could dispatch to error store here
});

export default router;
