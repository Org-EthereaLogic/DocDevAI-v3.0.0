import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

// Layouts
const AppLayout = () => import('../components/templates/AppLayout.vue')

// Views - Lazy loaded for performance
const HomeView = () => import('../views/HomeView.vue')
const DashboardView = () => import('../views/DashboardView.vue')
const DocumentsView = () => import('../views/DocumentsView.vue')
const DocumentDetailView = () => import('../views/DocumentDetailView.vue')
const DocumentGenerateView = () => import('../views/DocumentGenerateView.vue')
const TemplatesView = () => import('../views/TemplatesView.vue')
const TemplateDetailView = () => import('../views/TemplateDetailView.vue')
const TrackingView = () => import('../views/TrackingView.vue')
const ReviewView = () => import('../views/ReviewView.vue')
const BatchView = () => import('../views/BatchView.vue')
const VersionView = () => import('../views/VersionView.vue')
const SBOMView = () => import('../views/SBOMView.vue')
const SettingsView = () => import('../views/SettingsView.vue')
const APISettingsView = () => import('../views/APISettingsView.vue')
const OnboardingView = () => import('../views/OnboardingView.vue')
const PrivacyView = () => import('../views/PrivacyView.vue')
const HelpView = () => import('../views/HelpView.vue')

// Route configuration
const routes: RouteRecordRaw[] = [
  // Landing page
  {
    path: '/',
    name: 'home',
    component: HomeView,
    meta: {
      title: 'DevDocAI - AI-Powered Documentation Generator',
      description: 'Generate professional documentation with AI assistance',
      requiresAuth: false
    }
  },

  // Onboarding & Setup
  {
    path: '/onboarding',
    name: 'onboarding',
    component: OnboardingView,
    meta: {
      title: 'Get Started - DevDocAI',
      description: 'Welcome to DevDocAI - Let\'s get you set up',
      requiresAuth: false,
      hideNavigation: true
    }
  },
  {
    path: '/privacy',
    name: 'privacy',
    component: PrivacyView,
    meta: {
      title: 'Privacy Settings - DevDocAI',
      description: 'Configure your privacy and data preferences',
      requiresAuth: false
    }
  },

  // Main application routes with layout
  {
    path: '/app',
    component: AppLayout,
    meta: {
      requiresAuth: true
    },
    children: [
      // Dashboard
      {
        path: '',
        redirect: '/app/dashboard'
      },
      {
        path: 'dashboard',
        name: 'dashboard',
        component: DashboardView,
        meta: {
          title: 'Dashboard - DevDocAI',
          description: 'Project overview and quick actions',
          breadcrumb: 'Dashboard'
        }
      },

      // Documents
      {
        path: 'documents',
        name: 'documents',
        component: DocumentsView,
        meta: {
          title: 'Documents - DevDocAI',
          description: 'Manage and organize your documentation',
          breadcrumb: 'Documents'
        }
      },
      {
        path: 'documents/generate',
        name: 'documents-generate',
        component: DocumentGenerateView,
        meta: {
          title: 'Generate Document - DevDocAI',
          description: 'Create new documentation with AI assistance',
          breadcrumb: 'Generate Document',
          parentRoute: 'documents'
        }
      },
      {
        path: 'documents/:id',
        name: 'document-detail',
        component: DocumentDetailView,
        meta: {
          title: 'Document Details - DevDocAI',
          description: 'View and edit document details',
          breadcrumb: 'Document Details',
          parentRoute: 'documents'
        },
        props: true
      },

      // Templates
      {
        path: 'templates',
        name: 'templates',
        component: TemplatesView,
        meta: {
          title: 'Templates - DevDocAI',
          description: 'Browse and manage documentation templates',
          breadcrumb: 'Templates'
        }
      },
      {
        path: 'templates/:id',
        name: 'template-detail',
        component: TemplateDetailView,
        meta: {
          title: 'Template Details - DevDocAI',
          description: 'View template details and usage',
          breadcrumb: 'Template Details',
          parentRoute: 'templates'
        },
        props: true
      },

      // Tracking & Analysis
      {
        path: 'tracking',
        name: 'tracking',
        component: TrackingView,
        meta: {
          title: 'Tracking Matrix - DevDocAI',
          description: 'Visualize document dependencies and relationships',
          breadcrumb: 'Tracking Matrix'
        }
      },
      {
        path: 'review',
        name: 'review',
        component: ReviewView,
        meta: {
          title: 'Document Review - DevDocAI',
          description: 'Quality analysis and improvement recommendations',
          breadcrumb: 'Review'
        }
      },

      // Operations
      {
        path: 'batch',
        name: 'batch',
        component: BatchView,
        meta: {
          title: 'Batch Operations - DevDocAI',
          description: 'Manage bulk document operations',
          breadcrumb: 'Batch Operations'
        }
      },
      {
        path: 'version',
        name: 'version',
        component: VersionView,
        meta: {
          title: 'Version Control - DevDocAI',
          description: 'Git integration and version management',
          breadcrumb: 'Version Control'
        }
      },
      {
        path: 'sbom',
        name: 'sbom',
        component: SBOMView,
        meta: {
          title: 'SBOM Management - DevDocAI',
          description: 'Software Bill of Materials generation and security',
          breadcrumb: 'SBOM'
        }
      },

      // Settings
      {
        path: 'settings',
        name: 'settings',
        component: SettingsView,
        meta: {
          title: 'Settings - DevDocAI',
          description: 'Configure application preferences',
          breadcrumb: 'Settings'
        }
      },
      {
        path: 'settings/api',
        name: 'api-settings',
        component: APISettingsView,
        meta: {
          title: 'API Settings - DevDocAI',
          description: 'Configure AI providers and API keys',
          breadcrumb: 'API Settings',
          parentRoute: 'settings'
        }
      },

      // Help
      {
        path: 'help',
        name: 'help',
        component: HelpView,
        meta: {
          title: 'Help & Documentation - DevDocAI',
          description: 'Get help and learn about DevDocAI features',
          breadcrumb: 'Help'
        }
      }
    ]
  },

  // Redirects for backward compatibility
  {
    path: '/dashboard',
    redirect: '/app/dashboard'
  },
  {
    path: '/documents',
    redirect: '/app/documents'
  },
  {
    path: '/templates',
    redirect: '/app/templates'
  },
  {
    path: '/tracking',
    redirect: '/app/tracking'
  },
  {
    path: '/settings',
    redirect: '/app/settings'
  },

  // Catch all 404
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: {
      title: 'Page Not Found - DevDocAI',
      description: 'The page you are looking for does not exist'
    }
  }
]

// Router instance
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// Global navigation guards
router.beforeEach((to, from, next) => {
  // Set page title
  if (to.meta.title) {
    document.title = to.meta.title as string
  }

  // Set page description
  if (to.meta.description) {
    const metaDescription = document.querySelector('meta[name="description"]')
    if (metaDescription) {
      metaDescription.setAttribute('content', to.meta.description as string)
    }
  }

  // Auth check (placeholder for future implementation)
  if (to.meta.requiresAuth) {
    // TODO: Implement authentication check
    // For now, allow all routes
    next()
  } else {
    next()
  }
})

// Error handling
router.onError((error) => {
  console.error('Router error:', error)
})

export default router
