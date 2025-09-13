# DevDocAI v3.6.0 Frontend

Vue 3 + TypeScript + Pinia frontend for DevDocAI - AI-powered documentation generation and analysis system.

## 🏗️ Architecture Overview

This frontend application is built with modern web technologies and follows atomic design principles for maximum scalability and maintainability.

### Technology Stack

- **Framework**: Vue 3 with Composition API
- **Language**: TypeScript with strict mode
- **State Management**: Pinia with persistence
- **Styling**: Tailwind CSS with custom design system
- **Build Tool**: Vite with hot module replacement
- **Router**: Vue Router 4 with type-safe routes
- **HTTP Client**: Axios with interceptors and error handling
- **UI Components**: Headless UI + Custom atomic design system
- **Icons**: Heroicons + Lucide Vue
- **Testing**: Vitest + Vue Test Utils (planned)

### Project Structure

```
src/
├── components/           # Atomic design component structure
│   ├── atoms/           # Basic building blocks
│   │   ├── buttons/     # Button variants
│   │   ├── inputs/      # Form inputs
│   │   ├── icons/       # Icon components
│   │   ├── layout/      # Layout primitives
│   │   ├── feedback/    # Status indicators
│   │   └── typography/  # Text components
│   ├── molecules/       # Simple component combinations
│   │   ├── forms/       # Form groups
│   │   ├── navigation/  # Nav items
│   │   ├── cards/       # Card components
│   │   └── modals/      # Modal dialogs
│   ├── organisms/       # Complex component assemblies
│   │   ├── headers/     # App headers
│   │   ├── sidebars/    # Navigation sidebars
│   │   ├── dashboards/  # Dashboard layouts
│   │   └── wizards/     # Multi-step forms
│   └── templates/       # Page-level layouts
├── views/               # Page components
├── stores/              # Pinia state management
├── services/            # API integration layer
├── composables/         # Vue composition functions
├── utils/               # Utility functions
└── types/               # TypeScript type definitions
```

## 🚀 Backend Integration

The frontend integrates with the production-ready DevDocAI Python backend through a comprehensive service layer.

### Supported Backend Modules

✅ **All 13 Backend Modules Supported**:

1. **M001**: Configuration Manager - App settings and preferences
2. **M002**: Local Storage System - Document management
3. **M003**: MIAIR Engine - AI-powered document optimization
4. **M004**: Document Generator - Template-based generation
5. **M005**: Tracking Matrix - Dependency visualization
6. **M006**: Suite Manager - Document suite operations
7. **M007**: Review Engine - Quality analysis and scoring
8. **M008**: LLM Adapter - Multi-provider AI integration
9. **M009**: Enhancement Pipeline - Document improvement workflows
10. **M010**: SBOM Generator - Software bill of materials
11. **M011**: Batch Operations - Bulk processing
12. **M012**: Version Control - Git integration
13. **M013**: Template Marketplace - Community templates

### API Integration Features

- **Type-Safe API Client**: Full TypeScript support with auto-generated types
- **Error Handling**: Comprehensive error recovery and user feedback
- **Loading States**: Progressive loading with skeleton screens
- **Caching Strategy**: Intelligent caching with TTL and invalidation
- **Real-time Updates**: WebSocket integration for live data
- **Offline Support**: Service worker with offline-first approach

## 🎨 Design System

Based on the comprehensive v3.6.0 mockups with:

- **Color Palette**: Professional blue/gray theme with dark mode
- **Typography**: Inter font family with code-optimized monospace
- **Spacing**: 8px base grid system
- **Animations**: Consistent timing with reduced motion support
- **Accessibility**: WCAG 2.1 AA compliance throughout

### Key Design Features

- **Responsive Design**: Mobile-first approach (375px, 768px, 1024px+ breakpoints)
- **Motion Design**: Carefully crafted animations with performance optimization
- **High Contrast**: Optional high contrast mode for accessibility
- **Keyboard Navigation**: Full keyboard accessibility with visible focus indicators
- **Screen Reader Support**: Comprehensive ARIA labels and semantic HTML

## 🛠️ Development Setup

### Prerequisites

- Node.js 20.19.0+ or 22.12.0+
- npm 9+ or yarn 3+
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd DevDocAI-v3.0.0/frontend

# Install dependencies
npm install

# Copy environment configuration
cp .env.example .env.local

# Start development server
npm run dev
```

### Available Scripts

```bash
# Development
npm run dev          # Start dev server with HMR
npm run build        # Build for production
npm run preview      # Preview production build

# Code Quality
npm run type-check   # TypeScript type checking
npm run lint         # ESLint with auto-fix
npm run format       # Prettier code formatting

# Testing (planned)
npm run test         # Run unit tests
npm run test:e2e     # Run end-to-end tests
npm run coverage     # Generate coverage report
```

## ⚙️ Configuration

### Environment Variables

Key configuration options (see `.env.example` for full list):

```bash
# Backend Integration
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Feature Flags
VITE_DEV_TOOLS=true
VITE_API_LOGGING=true
VITE_PWA_ENABLED=true

# UI Defaults
VITE_DEFAULT_THEME=auto
VITE_DEFAULT_LANGUAGE=en
VITE_ANIMATIONS_ENABLED=true
```

### Customization

The application supports extensive customization:

- **Themes**: Light, dark, or auto-detection
- **Languages**: Multi-language support (i18n ready)
- **Accessibility**: Reduced motion, high contrast, screen reader optimization
- **Layout**: Compact mode, sidebar preferences, keyboard shortcuts

## 🔧 State Management

### Pinia Stores

- **App Store**: Global application state, theme, layout preferences
- **Config Store**: Backend configuration settings (M001 integration)
- **Documents Store**: Document and template management (M004 integration)
- **Notifications Store**: Global notification system with actions

### Store Features

- **Persistence**: Automatic localStorage sync for user preferences
- **Type Safety**: Full TypeScript support with IntelliSense
- **Devtools**: Vue devtools integration for debugging
- **Performance**: Optimized with computed properties and lazy loading

## 🌐 Routing

Type-safe routing with:

- **Route Guards**: Authentication and authorization checks
- **Meta Data**: Page titles, breadcrumbs, permissions
- **Lazy Loading**: Code splitting for optimal performance
- **Transitions**: Smooth page transitions with reduced motion support

## 🔐 Security

### Security Features

- **CSP Headers**: Content Security Policy implementation
- **XSS Protection**: Input sanitization and output encoding
- **CSRF Protection**: Token-based request validation
- **Secure Storage**: Encrypted local storage for sensitive data

### Privacy

- **Local-First**: All sensitive data stays on user's machine
- **No Telemetry**: Privacy-first approach with opt-in analytics
- **Minimal Tracking**: Only essential functionality tracking

## 📱 Progressive Web App

PWA features include:

- **Offline Support**: Service worker with cache-first strategy
- **App Installation**: Native app-like installation experience
- **Push Notifications**: Real-time updates and alerts
- **Background Sync**: Offline operation queueing

## ♿ Accessibility

WCAG 2.1 AA compliant with:

- **Keyboard Navigation**: Full keyboard operability
- **Screen Reader Support**: Comprehensive ARIA implementation
- **High Contrast**: Optional high contrast theme
- **Reduced Motion**: Respects user motion preferences
- **Focus Management**: Visible focus indicators and logical tab order

## 🚀 Performance

### Optimization Features

- **Code Splitting**: Route-based and component-based chunks
- **Tree Shaking**: Unused code elimination
- **Image Optimization**: WebP format with fallbacks
- **Bundle Analysis**: Size monitoring and optimization
- **Lazy Loading**: Progressive component and asset loading

### Performance Targets

- **First Contentful Paint**: <1.5s
- **Largest Contentful Paint**: <2.5s
- **Cumulative Layout Shift**: <0.1
- **First Input Delay**: <100ms

## 🧪 Testing Strategy

### Testing Pyramid

- **Unit Tests**: Component logic and utilities (Vitest)
- **Integration Tests**: Store and service integration
- **E2E Tests**: User workflow validation (Playwright)
- **Accessibility Tests**: Automated a11y validation

### Quality Gates

- **80%+ Test Coverage**: Maintained across all modules
- **Zero TypeScript Errors**: Strict type checking
- **Performance Budget**: Bundle size limits enforced
- **Accessibility Score**: 95%+ Lighthouse accessibility score

## 📦 Deployment

### Build Process

1. **Type Checking**: Ensure TypeScript compliance
2. **Linting**: Code quality validation
3. **Testing**: Full test suite execution
4. **Building**: Production optimization
5. **Analysis**: Bundle size and performance metrics

### Deployment Targets

- **Static Hosting**: Netlify, Vercel, GitHub Pages
- **CDN Integration**: Asset optimization and global distribution
- **Docker**: Containerized deployment option
- **Nginx**: Production server configuration

## 🤝 Contributing

### Development Workflow

1. **Feature Branches**: Create feature branches from `main`
2. **Atomic Commits**: Small, focused commits with clear messages
3. **Code Review**: Pull request review process
4. **Quality Checks**: Automated linting, testing, and type checking

### Code Standards

- **TypeScript Strict**: No `any` types, explicit return types
- **ESLint**: Enforced code style and best practices
- **Prettier**: Consistent code formatting
- **Conventional Commits**: Standardized commit messages

## 📄 License

This project is part of the DevDocAI system. See the main project LICENSE file for details.

## 🔗 Related

- [DevDocAI Backend](../devdocai/) - Python FastAPI backend
- [Design Documentation](../docs/02-design/mockups/) - Complete UI/UX specifications
- [Architecture Guide](../docs/01-specifications/architecture/) - System architecture documentation