# DevDocAI v3.6.0 Frontend Architecture

## Overview

DevDocAI v3.6.0 frontend is built with Vue 3, using a modern, scalable architecture designed for maintainability and performance. This document outlines the complete routing, state management, and component architecture.

## Technology Stack

- **Framework**: Vue 3 (Composition API)
- **State Management**: Pinia (recommended over Vuex for Vue 3)
- **Router**: Vue Router 4
- **HTTP Client**: Axios
- **UI Framework**: Tailwind CSS
- **Build Tool**: Vite
- **Language**: JavaScript (with optional TypeScript support)

## Architecture Decisions

### 1. State Management: Pinia vs Vuex

**Decision: Pinia** ✅

**Rationale:**
- **Vue 3 Native**: Designed specifically for Vue 3 with Composition API
- **Better TypeScript Support**: Full TypeScript support out of the box
- **Simpler API**: No mutations, direct state modification in actions
- **DevTools Integration**: Excellent Vue DevTools support
- **Modular by Design**: Each store is a separate module
- **Built-in Persistence**: Easy plugin system for state persistence
- **Performance**: Lighter weight than Vuex (~2kb vs ~10kb)

### 2. Routing Architecture

**Hierarchical Route Structure** with:
- **Lazy Loading**: All route components are lazy loaded for performance
- **Route Guards**: Authentication and onboarding checks
- **Nested Routes**: For complex views like Settings and Document Generation
- **Meta Properties**: For breadcrumbs, titles, and permissions

### 3. API Layer Architecture

**Service-Based Pattern** with:
- **Centralized Error Handling**: All API errors handled in interceptors
- **Automatic Token Management**: Auth tokens added automatically
- **Request/Response Logging**: Development environment logging
- **Progress Tracking**: Support for long-running operations
- **Retry Logic**: Automatic token refresh on 401 errors

## Folder Structure

```
devdocai-frontend/
├── src/
│   ├── assets/               # Static assets (images, fonts, etc.)
│   │   ├── images/
│   │   ├── fonts/
│   │   └── styles/
│   │       └── main.css     # Global styles
│   │
│   ├── components/           # Reusable components
│   │   ├── common/          # Generic components
│   │   │   ├── AppButton.vue
│   │   │   ├── AppModal.vue
│   │   │   ├── AppTooltip.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   └── ErrorBoundary.vue
│   │   │
│   │   ├── document/        # Document-related components
│   │   │   ├── DocumentCard.vue
│   │   │   ├── DocumentView.vue
│   │   │   ├── DocumentEditor.vue
│   │   │   └── HealthScore.vue
│   │   │
│   │   ├── forms/           # Form components
│   │   │   ├── ReadmeForm.vue
│   │   │   ├── ApiDocForm.vue
│   │   │   ├── ChangelogForm.vue
│   │   │   └── FormField.vue
│   │   │
│   │   ├── layout/          # Layout components
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   ├── AppFooter.vue
│   │   │   └── Breadcrumbs.vue
│   │   │
│   │   └── charts/          # Data visualization
│   │       ├── DependencyGraph.vue
│   │       ├── HealthChart.vue
│   │       └── StatsChart.vue
│   │
│   ├── composables/         # Vue 3 composables (shared logic)
│   │   ├── useApi.js
│   │   ├── useAuth.js
│   │   ├── useDocument.js
│   │   ├── useNotification.js
│   │   ├── useWebSocket.js
│   │   └── useTheme.js
│   │
│   ├── layouts/             # Page layouts
│   │   ├── DefaultLayout.vue
│   │   ├── AuthLayout.vue
│   │   └── OnboardingLayout.vue
│   │
│   ├── router/              # Routing configuration
│   │   ├── index.js         # Main router config
│   │   ├── guards.js        # Route guards
│   │   └── routes.js        # Route definitions
│   │
│   ├── services/            # External services
│   │   ├── api/            # API service layer
│   │   │   ├── index.js    # Axios configuration
│   │   │   ├── auth.js
│   │   │   ├── document.js
│   │   │   ├── template.js
│   │   │   ├── project.js
│   │   │   ├── review.js
│   │   │   ├── tracking.js
│   │   │   └── settings.js
│   │   │
│   │   ├── websocket.js    # WebSocket for real-time
│   │   └── storage.js      # Local storage service
│   │
│   ├── stores/              # Pinia stores
│   │   ├── index.js        # Store configuration
│   │   ├── auth.js         # Authentication state
│   │   ├── document.js     # Document management
│   │   ├── template.js     # Template marketplace
│   │   ├── project.js      # Project management
│   │   ├── settings.js     # User settings
│   │   ├── onboarding.js   # Onboarding state
│   │   ├── notification.js # Notifications/toasts
│   │   └── review.js       # Review/health metrics
│   │
│   ├── utils/               # Utility functions
│   │   ├── constants.js    # App constants
│   │   ├── validators.js   # Form validators
│   │   ├── formatters.js   # Data formatters
│   │   ├── helpers.js      # Helper functions
│   │   └── markdown.js     # Markdown utilities
│   │
│   ├── views/               # Page components
│   │   ├── Dashboard.vue
│   │   ├── DocumentWizard.vue
│   │   ├── TemplateMarketplace.vue
│   │   ├── TrackingMatrix.vue
│   │   ├── ReviewDashboard.vue
│   │   ├── Settings.vue
│   │   ├── Onboarding.vue
│   │   ├── NotFound.vue
│   │   │
│   │   ├── generate/       # Document generation views
│   │   │   ├── DocumentTypeSelect.vue
│   │   │   ├── GenerateReadme.vue
│   │   │   ├── GenerateApiDoc.vue
│   │   │   ├── GenerateChangelog.vue
│   │   │   └── GenerateSuite.vue
│   │   │
│   │   └── settings/       # Settings sub-views
│   │       ├── GeneralSettings.vue
│   │       ├── PrivacySettings.vue
│   │       ├── ApiSettings.vue
│   │       └── TemplateSettings.vue
│   │
│   ├── App.vue             # Root component
│   └── main.js             # Application entry point
│
├── public/                  # Static public assets
├── tests/                   # Test files
│   ├── unit/
│   └── e2e/
│
├── .env                    # Environment variables
├── .env.example           # Environment template
├── vite.config.js         # Vite configuration
├── tailwind.config.js     # Tailwind configuration
├── package.json           # Dependencies
└── README.md             # Frontend documentation
```

## Component Hierarchy

```
App.vue
├── Layout (Default/Auth/Onboarding)
│   ├── AppHeader
│   ├── AppSidebar (navigation)
│   ├── RouterView (page content)
│   │   ├── Dashboard
│   │   │   └── DocumentCard (multiple)
│   │   ├── DocumentWizard
│   │   │   ├── StepIndicator
│   │   │   ├── DocumentTypeSelect
│   │   │   └── [DocumentForm]
│   │   ├── TemplateMarketplace
│   │   │   ├── TemplateFilter
│   │   │   └── TemplateCard (multiple)
│   │   ├── TrackingMatrix
│   │   │   └── DependencyGraph
│   │   ├── ReviewDashboard
│   │   │   ├── HealthScore
│   │   │   └── ReviewMetrics
│   │   └── Settings
│   │       └── [SettingsSubView]
│   └── AppFooter
└── NotificationContainer (global)
```

## Data Flow Architecture

### 1. Unidirectional Data Flow

```
User Action → Component → Store Action → API Call → Store Mutation → Component Update
```

### 2. Store Responsibilities

- **Auth Store**: User authentication, session management
- **Document Store**: Document CRUD, generation, health metrics
- **Template Store**: Template marketplace, downloads, ratings
- **Project Store**: Project selection, configuration
- **Settings Store**: User preferences, privacy settings
- **Onboarding Store**: Tutorial progress, first-run experience
- **Notification Store**: Toast messages, alerts
- **Review Store**: Document quality metrics, review results

### 3. API Integration Pattern

```javascript
// Component
const { generateDocument } = useDocumentStore();
await generateDocument('readme', formData);

// Store
async generateDocument(type, data) {
  const response = await documentAPI.generate({ type, ...data });
  this.documents.push(response.document);
  return response;
}

// API Service
generate(data) {
  return apiClient.post('/documents/generate', data);
}
```

## Implementation Instructions

### Phase 1: Core Setup (Current)
1. ✅ Install dependencies (Vue Router, Pinia)
2. ✅ Create router configuration
3. ✅ Setup Pinia stores structure
4. ✅ Implement API service layer
5. Create layout components

### Phase 2: Page Implementation
1. Implement Onboarding flow
2. Create Dashboard with project cards
3. Build Document Generation Wizard
4. Implement Template Marketplace
5. Create Tracking Matrix visualization
6. Build Review Dashboard
7. Implement Settings pages

### Phase 3: Component Library
1. Create common UI components
2. Build form components with validation
3. Implement data visualization components
4. Create document viewing/editing components

### Phase 4: Integration
1. Connect to backend API
2. Implement real-time updates (WebSocket)
3. Add error handling and recovery
4. Implement progress tracking for long operations

### Phase 5: Polish
1. Add animations and transitions
2. Implement keyboard navigation
3. Add accessibility features (ARIA)
4. Optimize performance (lazy loading, caching)
5. Add comprehensive error states

## Next Steps

1. **Install Required Dependencies**:
```bash
npm install vue-router@4 pinia pinia-plugin-persistedstate
```

2. **Update main.js** to include router and stores:
```javascript
import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import pinia from './stores';

const app = createApp(App);
app.use(router);
app.use(pinia);
app.mount('#app');
```

3. **Create Layout Components** following the structure above

4. **Implement Views** based on mockup specifications

## Security Considerations

- **Token Storage**: Use httpOnly cookies or secure localStorage
- **API Rate Limiting**: Implement client-side throttling
- **Input Validation**: Validate all forms before submission
- **XSS Prevention**: Sanitize user-generated content
- **CORS**: Configure proper CORS headers

## Performance Optimizations

- **Code Splitting**: Lazy load routes and heavy components
- **Image Optimization**: Use WebP format, lazy loading
- **Caching Strategy**: Cache API responses where appropriate
- **Bundle Size**: Monitor and optimize bundle size
- **Virtual Scrolling**: For large lists (template marketplace)

## Testing Strategy

- **Unit Tests**: Components, stores, utilities
- **Integration Tests**: API services, store actions
- **E2E Tests**: Critical user flows (onboarding, generation)
- **Accessibility Tests**: WCAG 2.1 AA compliance

## Monitoring & Analytics

- **Error Tracking**: Sentry or similar
- **Performance Monitoring**: Web Vitals tracking
- **User Analytics**: Privacy-respecting analytics
- **API Monitoring**: Track API response times and errors
