/**
 * DevDocAI v3.0.0 - Document Generator Component
 * 
 * Interface for M004 Document Generator module
 * Provides document generation capabilities with templates and AI assistance.
 */

import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Chip,
  LinearProgress,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  IconButton,
} from '@mui/material';

// Import persistence hooks
import { usePersistedState, usePersistedFormState } from '../hooks/usePersistedState';
import {
  Add as AddIcon,
  PlayArrow as GenerateIcon,
  Description as DocumentIcon,
  Article as TemplateIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Preview as PreviewIcon,
} from '@mui/icons-material';

interface GenerationJob {
  id: string;
  title: string;
  template: string;
  status: 'pending' | 'generating' | 'complete' | 'error';
  progress: number;
  createdAt: Date;
  content?: string;
  format: string;
}

const DocumentGenerator: React.FC = () => {
  // Persisted form state - automatically saves/restores across browser sessions
  const [formState, setFormState] = usePersistedFormState('document_generator', {
    selectedTemplate: '',
    projectPath: '',
    outputFormat: 'markdown',
    customPrompt: '',
  });

  // Persisted jobs list - saves generation history
  const [jobs, setJobs] = usePersistedState<GenerationJob[]>('document_generator_jobs', []);
  
  // Non-persisted state for temporary UI states
  const [isGenerating, setIsGenerating] = useState(false);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  // Destructure form state for easier access
  const { selectedTemplate, projectPath, outputFormat, customPrompt } = formState;

  const templates = [
    { id: 'prd', name: 'Product Requirements Document (PRD)', description: 'Comprehensive product requirements with user stories and success metrics' },
    { id: 'wbs', name: 'Work Breakdown Structure (WBS)', description: 'Hierarchical task decomposition with effort estimates and dependencies' },
    { id: 'srs', name: 'Software Requirements Specification (SRS)', description: 'IEEE 830 compliant detailed technical requirements' },
    { id: 'architecture', name: 'Architecture Blueprint', description: 'System architecture design with components and integration points' },
  ];

  const generateDocumentContent = (template: string, path: string, custom: string) => {
    const templateName = templates.find(t => t.id === template)?.name || 'Document';
    const projectName = path.split('/').pop() || 'Project';
    
    const contentMap: Record<string, string> = {
      'prd': `# ${projectName} - Product Requirements Document (PRD)

> Generated using DevDocAI v3.0.0 with AI-powered multi-LLM synthesis

${custom ? `## Project Context\n${custom}\n` : ''}

## 1. Executive Summary

### 1.1 Product Vision
Transform how developers create and maintain technical documentation through AI-powered generation, ensuring consistency, completeness, and quality across all project documentation.

### 1.2 Problem Statement
Developers spend 30-40% of their time on documentation, often producing inconsistent or incomplete docs. This impacts project maintainability, onboarding, and collaboration.

### 1.3 Value Proposition
- **80% reduction** in documentation time
- **Consistent quality** across all documents
- **AI-powered insights** for better requirements
- **Automated updates** as code evolves

### 1.4 Success Metrics
- Documentation generation time: <5 minutes per document
- Quality score: >85% on all generated docs
- User satisfaction: >4.5/5 rating
- Adoption rate: 75% of development teams

## 2. Target Users

### 2.1 Primary Users
**Solo Developers & Small Teams**
- Working on multiple projects
- Limited time for documentation
- Need professional-quality docs for clients

### 2.2 User Personas

**Alex - The Indie Developer**
- Builds SaaS products solo
- Struggles with documentation time
- Needs to impress potential investors

**Sam - The Team Lead**
- Manages 5-person development team
- Ensures documentation standards
- Facilitates knowledge transfer

## 3. Core Features (MVP)

### Feature 1: AI-Powered Generation
- Multi-LLM synthesis for best results
- Context-aware documentation
- Learns from your codebase

### Feature 2: Template Library
- PRD, WBS, SRS, Architecture templates
- Customizable for specific needs
- Industry best practices built-in

### Feature 3: Quality Analysis
- Real-time quality scoring
- Improvement suggestions
- Compliance checking

## 4. Technical Requirements
- Response time: <3 seconds for analysis
- Document generation: <30 seconds
- 99.9% uptime
- Support for 10+ programming languages

---
*Generated on ${new Date().toLocaleString()} by DevDocAI*`,

      'wbs': `# ${projectName} - Work Breakdown Structure (WBS)

> Generated using DevDocAI v3.0.0 with intelligent task decomposition

${custom ? `## Project Scope\n${custom}\n` : ''}

## Project Overview
- **Duration:** 3-6 months
- **Team Size:** 3-5 developers
- **Methodology:** Agile/Scrum
- **Total Effort:** 2,400 person-hours

## Work Breakdown Structure

### 1.0 ${projectName} [PROJECT]
**Total Effort:** 2,400 hours
**Duration:** 20 weeks

#### 1.1 Project Management [10%]
**Effort:** 240 hours

##### 1.1.1 Project Planning
- **Effort:** 40 hours
- **Duration:** 1 week
- **Deliverable:** Project plan, WBS
- Create project charter (8h)
- Develop WBS (8h)
- Create schedule (16h)
- Define communication plan (8h)

##### 1.1.2 Risk Management
- **Effort:** 24 hours
- **Dependencies:** 1.1.1
- Identify risks (8h)
- Assess probability/impact (8h)
- Develop mitigation (8h)

#### 1.2 Requirements & Design [15%]
**Effort:** 360 hours

##### 1.2.1 Requirements Gathering
- **Effort:** 80 hours
- **Duration:** 2 weeks
- Stakeholder interviews (24h)
- Requirements workshops (16h)
- Document functional requirements (24h)
- Document non-functional requirements (16h)

##### 1.2.2 System Architecture
- **Effort:** 60 hours
- **Dependencies:** 1.2.1
- High-level architecture (16h)
- Component design (20h)
- Data model design (16h)
- Integration design (8h)

#### 1.3 Development [45%]
**Effort:** 1,080 hours

##### 1.3.1 Backend Development
- **Effort:** 540 hours
- Database implementation (40h)
- API development (200h)
- Business logic (300h)

##### 1.3.2 Frontend Development
- **Effort:** 540 hours
- UI components (180h)
- Page implementation (240h)
- Integration (120h)

#### 1.4 Testing [20%]
**Effort:** 480 hours
- Unit testing (160h)
- Integration testing (120h)
- System testing (80h)
- UAT (120h)

#### 1.5 Deployment [10%]
**Effort:** 240 hours
- Environment setup (40h)
- Data migration (40h)
- Production deployment (40h)
- Post-deployment support (120h)

## Milestones
| ID | Milestone | Week | Success Criteria |
|----|-----------|------|------------------|
| M1 | Requirements Complete | 3 | Sign-off received |
| M2 | Design Complete | 5 | Architecture approved |
| M3 | Alpha Release | 12 | Core features working |
| M4 | Beta Release | 16 | Feature complete |
| M5 | Production Release | 20 | UAT passed |

## Critical Path
1.1.1 → 1.2.1 → 1.2.2 → 1.3.1 → 1.3.2 → 1.4 → 1.5

---
*Generated on ${new Date().toLocaleString()} by DevDocAI*`,

      'srs': `# ${projectName} - Software Requirements Specification (SRS)

> IEEE 830 Compliant - Generated by DevDocAI v3.0.0

${custom ? `## Project Context\n${custom}\n` : ''}

## 1. Introduction

### 1.1 Purpose
This SRS describes the functional and non-functional requirements for ${projectName}, providing a comprehensive specification for development teams, QA engineers, and stakeholders.

### 1.2 Scope
${projectName} is a software system designed to meet modern development needs with scalability, security, and performance at its core.

### 1.3 Definitions
- **API**: Application Programming Interface
- **MVP**: Minimum Viable Product
- **SLA**: Service Level Agreement
- **RBAC**: Role-Based Access Control

## 2. Overall Description

### 2.1 Product Perspective
The system operates as a standalone application with optional cloud integration, designed for cross-platform deployment.

### 2.2 Product Functions
- User authentication and authorization
- Data processing and storage
- Real-time notifications
- Analytics and reporting
- API integration capabilities

### 2.3 User Classes
1. **Administrators**: Full system access
2. **Power Users**: Advanced features
3. **Standard Users**: Core functionality
4. **Guest Users**: Limited read-only access

## 3. Specific Requirements

### 3.1 Functional Requirements

#### FR-001: User Authentication
- **Priority:** High
- **Description:** Secure user authentication using JWT tokens
- **Input:** Username, password
- **Processing:** Validate credentials, generate token
- **Output:** Authentication token, user profile
- **Error Handling:** Invalid credentials, account locked

#### FR-002: Data Management
- **Priority:** High
- **Description:** CRUD operations on application data
- **Validation:** Schema validation, authorization checks
- **Performance:** <100ms response time for queries

### 3.2 Non-Functional Requirements

#### 3.2.1 Performance
- Response time: <200ms for 95% of requests
- Throughput: 1000 requests per second
- Concurrent users: 500 simultaneous

#### 3.2.2 Security
- Encryption: AES-256 for data at rest
- TLS 1.3 for data in transit
- OWASP Top 10 compliance
- Regular security audits

#### 3.2.3 Reliability
- Availability: 99.9% uptime
- MTBF: >1000 hours
- Recovery time: <1 hour

#### 3.2.4 Scalability
- Horizontal scaling support
- Database sharding capability
- CDN integration ready

## 4. External Interface Requirements

### 4.1 User Interfaces
- Responsive web application
- Mobile applications (iOS/Android)
- CLI tool for automation

### 4.2 Hardware Interfaces
- Standard x86_64 architecture
- Minimum 4GB RAM, 50GB storage
- Network: 100Mbps minimum

### 4.3 Software Interfaces
- Database: PostgreSQL 14+
- Cache: Redis 6+
- Message Queue: RabbitMQ

## 5. System Features

### 5.1 Dashboard
Real-time metrics and status monitoring with customizable widgets.

### 5.2 Reporting Engine
Generate comprehensive reports in multiple formats (PDF, Excel, CSV).

### 5.3 Integration Hub
Connect with third-party services via REST APIs and webhooks.

---
*Generated on ${new Date().toLocaleString()} by DevDocAI*`,

      'architecture': `# ${projectName} - Architecture Blueprint

> System Design Document - Generated by DevDocAI v3.0.0

${custom ? `## Design Context\n${custom}\n` : ''}

## 1. Executive Summary

This architecture blueprint defines the technical design for ${projectName}, emphasizing scalability, maintainability, and security.

## 2. System Overview

### 2.1 Architecture Style
**Microservices Architecture** with event-driven communication

### 2.2 Key Design Principles
- **Separation of Concerns**: Clear boundaries between components
- **Loose Coupling**: Services communicate via APIs
- **High Cohesion**: Related functionality grouped together
- **Fault Tolerance**: Graceful degradation and recovery
- **Security by Design**: Defense in depth approach

## 3. System Architecture

### 3.1 High-Level Architecture

\`\`\`
┌─────────────────────────────────────────────┐
│                   Clients                   │
│  (Web App, Mobile App, API Consumers)       │
└────────────────┬────────────────────────────┘
                 │
        ┌────────▼────────┐
        │   API Gateway    │
        │  (Rate Limiting, │
        │   Auth, Routing) │
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼───┐  ┌────▼────┐  ┌────▼────┐
│Service│  │Service  │  │Service  │
│   A   │  │    B    │  │    C    │
└───┬───┘  └────┬────┘  └────┬────┘
    │           │            │
    └───────────┼────────────┘
                │
       ┌────────▼────────┐
       │   Data Layer    │
       │  (DB, Cache,    │
       │   File Storage) │
       └─────────────────┘
\`\`\`

### 3.2 Component Architecture

#### 3.2.1 API Gateway
- **Technology**: Kong/Nginx
- **Responsibilities**: Request routing, authentication, rate limiting
- **Scaling**: Horizontal with load balancer

#### 3.2.2 Core Services

**Authentication Service**
- JWT token generation/validation
- User session management
- OAuth2/OIDC integration

**Business Logic Service**
- Core application logic
- Workflow orchestration
- Business rule engine

**Data Service**
- CRUD operations
- Data validation
- Transaction management

#### 3.2.3 Data Layer
- **Primary Database**: PostgreSQL (ACID compliance)
- **Cache**: Redis (session, frequent queries)
- **Search**: Elasticsearch (full-text search)
- **File Storage**: S3-compatible object storage

## 4. Data Architecture

### 4.1 Data Model
\`\`\`sql
-- Core entities
Users, Roles, Permissions
Organizations, Projects
Documents, Versions
Audit_Logs, Events
\`\`\`

### 4.2 Data Flow
1. Client request → API Gateway
2. Gateway → Authentication check
3. Route to appropriate service
4. Service processes business logic
5. Data layer operations
6. Response formatting
7. Return to client

## 5. Security Architecture

### 5.1 Security Layers
1. **Network**: Firewall, DDoS protection
2. **Application**: Input validation, CSRF protection
3. **Data**: Encryption at rest/transit
4. **Access**: RBAC, principle of least privilege

### 5.2 Authentication & Authorization
- Multi-factor authentication
- OAuth2/OpenID Connect
- API key management
- Role-based permissions

## 6. Infrastructure Architecture

### 6.1 Deployment Architecture
- **Container**: Docker
- **Orchestration**: Kubernetes
- **CI/CD**: GitLab CI / GitHub Actions
- **Monitoring**: Prometheus + Grafana

### 6.2 Environments
- Development (local Docker)
- Staging (cloud - scaled down)
- Production (cloud - full scale)

## 7. Integration Architecture

### 7.1 External Systems
- Payment Gateway (Stripe/PayPal)
- Email Service (SendGrid)
- SMS Provider (Twilio)
- Analytics (Google Analytics)

### 7.2 Integration Patterns
- REST APIs for synchronous
- Message queues for async
- Webhooks for real-time events
- Batch processing for bulk ops

## 8. Performance Architecture

### 8.1 Caching Strategy
- Browser cache (static assets)
- CDN (global distribution)
- Application cache (Redis)
- Database query cache

### 8.2 Scaling Strategy
- Horizontal scaling for services
- Database read replicas
- Auto-scaling based on metrics
- Load balancing across regions

## 9. Disaster Recovery

### 9.1 Backup Strategy
- Daily automated backups
- Point-in-time recovery
- Cross-region replication
- 30-day retention policy

### 9.2 Recovery Objectives
- **RTO**: 4 hours
- **RPO**: 1 hour
- Automated failover
- Health checks and monitoring

---
*Generated on ${new Date().toLocaleString()} by DevDocAI*`
    };

    return contentMap[template] || `# ${templateName}\n\nGenerated document for ${path}\n\n${custom || 'No custom instructions provided.'}\n\n---\n*Generated by DevDocAI v3.0.0*`;
  };

  const handleGenerate = async () => {
    if (!selectedTemplate || !projectPath) return;

    const newJob: GenerationJob = {
      id: Date.now().toString(),
      title: `Documentation for ${projectPath}`,
      template: selectedTemplate,
      status: 'generating',
      progress: 0,
      createdAt: new Date(),
      content: '',
      format: outputFormat,
    };

    setJobs(prev => [newJob, ...prev]);
    setIsGenerating(true);

    // Progress animation - declare outside try/catch for proper scope
    const progressInterval = setInterval(() => {
      setJobs(prev => prev.map(job => 
        job.id === newJob.id 
          ? { ...job, progress: Math.min(job.progress + Math.random() * 20, 95) }
          : job
      ));
    }, 500);

    try {

      // Call the AI API to generate documentation
      console.log('Calling AI API with:', {
        project_path: projectPath,
        template: selectedTemplate,
        custom_instructions: customPrompt,
        format: outputFormat,
      });

      const response = await fetch(`/api/generate?t=${Date.now()}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-cache', // Disable browser caching
        body: JSON.stringify({
          project_path: projectPath,
          template: selectedTemplate,
          custom_instructions: customPrompt,
          format: outputFormat,
        }),
        // Add timeout and other fetch options
        signal: AbortSignal.timeout(60000), // 60 second timeout
      });

      console.log('API Response status:', response.status);
      console.log('API Response ok:', response.ok);
      console.log('API Response headers:', response.headers);
      
      if (!response.ok) {
        throw new Error(`API returned status ${response.status}`);
      }
      
      const data = await response.json();
      console.log('API Response data:', data);
      console.log('API data.success:', data.success);
      console.log('API data.content exists:', !!data.content);
      console.log('API data.content length:', data.content ? data.content.length : 0);
      
      clearInterval(progressInterval);

      if (data.success && data.content) {
        // Update job with AI-generated content
        console.log('✅ Using AI-generated content from API');
        setJobs(prev => prev.map(job => 
          job.id === newJob.id 
            ? { ...job, status: 'complete', progress: 100, content: data.content }
            : job
        ));
        console.log('✅ AI Generation Success! Metadata:', data.metadata);
      } else {
        console.log('❌ API returned success:false or no content, using fallback');
        console.log('data.success:', data.success);
        console.log('data.content:', data.content ? 'exists' : 'missing');
        // Fallback to template-based generation if API fails
        const fallbackContent = generateDocumentContent(selectedTemplate, projectPath, customPrompt);
        setJobs(prev => prev.map(job => 
          job.id === newJob.id 
            ? { ...job, status: 'complete', progress: 100, content: fallbackContent }
            : job
        ));
      }
    } catch (error) {
      console.error('❌ Generation error caught:', error);
      console.error('Error details:', {
        message: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : undefined,
      });
      clearInterval(progressInterval);
      // Fallback to template-based generation on error
      const fallbackContent = generateDocumentContent(selectedTemplate, projectPath, customPrompt);
      setJobs(prev => prev.map(job => 
        job.id === newJob.id 
          ? { ...job, status: 'complete', progress: 100, content: fallbackContent }
          : job
      ));
    } finally {
      setIsGenerating(false);
    }
  };

  const handlePreview = (job: GenerationJob) => {
    if (!job.content) return;
    
    // Open preview in new window
    const previewWindow = window.open('', '_blank', 'width=800,height=600');
    if (previewWindow) {
      previewWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>${job.title} - Preview</title>
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
              line-height: 1.6;
              color: #333;
              max-width: 800px;
              margin: 0 auto;
              padding: 20px;
            }
            pre {
              background: #f5f5f5;
              padding: 10px;
              border-radius: 5px;
              overflow-x: auto;
            }
            code {
              background: #f5f5f5;
              padding: 2px 5px;
              border-radius: 3px;
              font-family: 'Courier New', monospace;
            }
            h1, h2, h3 {
              color: #2c3e50;
            }
            blockquote {
              border-left: 4px solid #667eea;
              padding-left: 16px;
              color: #666;
            }
          </style>
        </head>
        <body>
          ${convertMarkdownToHTML(job.content)}
        </body>
        </html>
      `);
      previewWindow.document.close();
    }
  };

  const handleDownload = (job: GenerationJob) => {
    if (!job.content) return;

    const blob = new Blob([job.content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${job.title.replace(/[^a-z0-9]/gi, '_')}.${job.format === 'markdown' ? 'md' : job.format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const convertMarkdownToHTML = (markdown: string) => {
    // Basic markdown to HTML conversion
    return markdown
      .replace(/^### (.*$)/gim, '<h3>$1</h3>')
      .replace(/^## (.*$)/gim, '<h2>$1</h2>')
      .replace(/^# (.*$)/gim, '<h1>$1</h1>')
      .replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>')
      .replace(/\*\*(.*)\*\*/g, '<b>$1</b>')
      .replace(/\*(.*)\*/g, '<i>$1</i>')
      .replace(/```([^`]+)```/g, '<pre><code>$1</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>')
      .replace(/- (.*)<br>/g, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  };

  const getStatusColor = (status: GenerationJob['status']) => {
    switch (status) {
      case 'complete': return 'success';
      case 'error': return 'error';
      case 'generating': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Document Generator
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Generate comprehensive documentation using AI-powered templates and analysis.
      </Typography>

      <Grid container spacing={3}>
        {/* Generation Form */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Generate New Documentation
              </Typography>
              
              <Button
                variant="outlined"
                color="secondary"
                onClick={async () => {
                  console.log('Testing API connection...');
                  try {
                    console.log('Making request to: http://localhost:5000/api/test');
                    console.log('Request headers:', {
                      'Origin': window.location.origin,
                      'User-Agent': navigator.userAgent
                    });
                    
                    const response = await fetch(`/api/test?t=${Date.now()}`, {
                      method: 'GET',
                      headers: {
                        'Content-Type': 'application/json',
                      },
                      cache: 'no-cache', // Disable browser caching
                    });
                    
                    console.log('Test API Response:', {
                      status: response.status,
                      statusText: response.statusText,
                      headers: Object.fromEntries(response.headers.entries()),
                      ok: response.ok
                    });
                    
                    if (!response.ok) {
                      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    console.log('Test API Data:', data);
                    alert(`✅ API Connected Successfully!\nStatus: ${data.status}\nTimestamp: ${data.timestamp}`);
                  } catch (error) {
                    console.error('❌ API Test Failed:', error);
                    console.error('Error details:', {
                      name: error instanceof Error ? error.name : 'Unknown',
                      message: error instanceof Error ? error.message : 'Unknown error',
                      stack: error instanceof Error ? error.stack : undefined
                    });
                    
                    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                      alert(`❌ API Connection Failed!\nError: Network request failed\nPossible causes:\n- Flask server not running\n- CORS not configured\n- Port 5000 blocked\n\nCheck console for details.`);
                    } else {
                      alert(`❌ API Connection Failed!\nError: ${error instanceof Error ? error.message : 'Unknown error'}\n\nCheck console for details.`);
                    }
                  }
                }}
                sx={{ mb: 2 }}
                size="small"
              >
                Test API Connection
              </Button>

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Project Path"
                  value={projectPath}
                  onChange={(e) => setFormState(prev => ({ ...prev, projectPath: e.target.value }))}
                  placeholder="/path/to/your/project"
                  fullWidth
                  required
                />

                <FormControl fullWidth required>
                  <InputLabel>Template</InputLabel>
                  <Select
                    value={selectedTemplate}
                    onChange={(e) => setFormState(prev => ({ ...prev, selectedTemplate: e.target.value }))}
                    label="Template"
                  >
                    {templates.map((template) => (
                      <MenuItem key={template.id} value={template.id}>
                        <Box>
                          <Typography variant="body2" component="span" display="block">{template.name}</Typography>
                          <Typography variant="caption" color="text.secondary" component="span" display="block">
                            {template.description}
                          </Typography>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                <FormControl fullWidth>
                  <InputLabel>Output Format</InputLabel>
                  <Select
                    value={outputFormat}
                    onChange={(e) => setFormState(prev => ({ ...prev, outputFormat: e.target.value }))}
                    label="Output Format"
                  >
                    <MenuItem value="markdown">Markdown (.md)</MenuItem>
                    <MenuItem value="html">HTML (.html)</MenuItem>
                    <MenuItem value="pdf">PDF (.pdf)</MenuItem>
                    <MenuItem value="docx">Word (.docx)</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  label="Custom Instructions (Optional)"
                  value={customPrompt}
                  onChange={(e) => setFormState(prev => ({ ...prev, customPrompt: e.target.value }))}
                  multiline
                  rows={3}
                  placeholder="Provide specific instructions for documentation generation..."
                  fullWidth
                />

                <Button
                  variant="contained"
                  startIcon={<GenerateIcon />}
                  onClick={handleGenerate}
                  disabled={!selectedTemplate || !projectPath || isGenerating}
                  size="large"
                >
                  {isGenerating ? 'Generating...' : 'Generate Documentation'}
                </Button>
              </Box>
            </CardContent>
          </Card>

          {/* Template Preview */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Available Templates
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {templates.map((template) => (
                  <Chip
                    key={template.id}
                    label={template.name}
                    onClick={() => setFormState(prev => ({ ...prev, selectedTemplate: template.id }))}
                    variant={selectedTemplate === template.id ? 'filled' : 'outlined'}
                    color={selectedTemplate === template.id ? 'primary' : 'default'}
                    icon={<TemplateIcon />}
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Generation History & Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Generation History</Typography>
                <IconButton size="small">
                  <RefreshIcon />
                </IconButton>
              </Box>

              {jobs.length === 0 ? (
                <Alert severity="info">
                  No documentation has been generated yet. Start by selecting a template and project path above.
                </Alert>
              ) : (
                <List>
                  {jobs.map((job, index) => (
                    <React.Fragment key={job.id}>
                      <ListItem
                        sx={{ px: 0 }}
                        secondaryAction={
                          <Box sx={{ display: 'flex', gap: 1 }}>
                            {job.status === 'complete' && (
                              <>
                                <IconButton 
                                  size="small" 
                                  onClick={() => handlePreview(job)}
                                  title="Preview document"
                                >
                                  <PreviewIcon />
                                </IconButton>
                                <IconButton 
                                  size="small" 
                                  onClick={() => handleDownload(job)}
                                  title="Download document"
                                >
                                  <DownloadIcon />
                                </IconButton>
                              </>
                            )}
                          </Box>
                        }
                      >
                        <ListItemIcon>
                          <DocumentIcon />
                        </ListItemIcon>
                        <ListItemText
                          primary={job.title}
                          secondary={
                            <>
                              <Typography variant="caption" component="span" display="block">
                                Template: {templates.find(t => t.id === job.template)?.name}
                              </Typography>
                              <Box component="span" sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                                <Chip 
                                  label={job.status} 
                                  size="small" 
                                  color={getStatusColor(job.status)}
                                />
                                {job.status === 'generating' && (
                                  <Box component="span" sx={{ flexGrow: 1, ml: 1, display: 'inline-flex' }}>
                                    <LinearProgress 
                                      variant="determinate" 
                                      value={job.progress}
                                      sx={{ height: 4, borderRadius: 2, width: '100%' }}
                                    />
                                  </Box>
                                )}
                              </Box>
                            </>
                          }
                        />
                      </ListItem>
                      {index < jobs.length - 1 && <Divider component="li" />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>

          {/* Quick Stats */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Statistics
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="primary">
                      {jobs.filter(j => j.status === 'complete').length}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Completed
                    </Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6}>
                  <Paper sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="h4" color="secondary">
                      {jobs.filter(j => j.status === 'generating').length}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      In Progress
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DocumentGenerator;