/**
 * DocumentGeneratorPanel - VS Code document generation interface
 * 
 * Provides document generation within VS Code:
 * - Template selection and preview
 * - File context analysis
 * - Generation options configuration
 * - Real-time generation progress
 * - Output preview and insertion
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Card,
  CardContent,
  CardActions,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondary,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress
} from '@mui/material';
import {
  Description,
  Code,
  Preview,
  Settings,
  CheckCircle,
  ExpandMore,
  InsertDriveFile,
  Folder,
  Edit,
  Save,
  PlayArrow
} from '@mui/icons-material';

import WebviewPanel from './WebviewPanel';
import { useGlobalState } from '../../core/state-management';
import { eventManager, UIEventType } from '../../core/event-system';
import { LoadingSpinner, EmptyState, SkeletonLoader } from '../common';

/**
 * Generation step interface
 */
interface GenerationStep {
  id: string;
  label: string;
  description: string;
  completed: boolean;
  active: boolean;
  error?: string;
}

/**
 * File context interface
 */
interface FileContext {
  path: string;
  name: string;
  type: 'file' | 'directory';
  language?: string;
  size: number;
  lastModified: Date;
  selected: boolean;
}

/**
 * Template option interface
 */
interface TemplateOption {
  id: string;
  name: string;
  description: string;
  category: string;
  preview: string;
  variables: string[];
}

/**
 * Generation configuration interface
 */
interface GenerationConfig {
  templateId: string;
  outputPath: string;
  variables: Record<string, string>;
  includeFiles: string[];
  options: {
    includeComments: boolean;
    includeExamples: boolean;
    generateTests: boolean;
    updateExisting: boolean;
  };
}

/**
 * DocumentGeneratorPanel component
 */
const DocumentGeneratorPanel: React.FC = () => {
  const globalState = useGlobalState();
  const state = globalState.getState();

  // Component state
  const [activeStep, setActiveStep] = useState(0);
  const [fileContext, setFileContext] = useState<FileContext[]>([]);
  const [templates, setTemplates] = useState<TemplateOption[]>([]);
  const [config, setConfig] = useState<GenerationConfig>({
    templateId: '',
    outputPath: '',
    variables: {},
    includeFiles: [],
    options: {
      includeComments: true,
      includeExamples: false,
      generateTests: false,
      updateExisting: false
    }
  });
  const [generationSteps, setGenerationSteps] = useState<GenerationStep[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState<string>('');
  const [loading, setLoading] = useState(true);

  // Load initial data
  useEffect(() => {
    loadFileContext();
    loadTemplates();
  }, []);

  // Step definitions
  const steps = [
    {
      label: 'Select Context',
      description: 'Choose files and directories to analyze'
    },
    {
      label: 'Choose Template',
      description: 'Select documentation template'
    },
    {
      label: 'Configure Options',
      description: 'Set generation parameters'
    },
    {
      label: 'Generate',
      description: 'Create documentation'
    },
    {
      label: 'Review & Save',
      description: 'Review and insert generated content'
    }
  ];

  const loadFileContext = async () => {
    try {
      // In VS Code, this would get the current workspace files
      const mockContext: FileContext[] = [
        {
          path: '/src/components/Button.tsx',
          name: 'Button.tsx',
          type: 'file',
          language: 'typescript',
          size: 2048,
          lastModified: new Date(),
          selected: false
        },
        {
          path: '/src/utils/helpers.ts',
          name: 'helpers.ts',
          type: 'file',
          language: 'typescript',
          size: 1024,
          lastModified: new Date(),
          selected: false
        },
        {
          path: '/src/components',
          name: 'components',
          type: 'directory',
          size: 10240,
          lastModified: new Date(),
          selected: false
        }
      ];
      
      setFileContext(mockContext);
    } catch (error) {
      console.error('Failed to load file context:', error);
    }
  };

  const loadTemplates = async () => {
    try {
      // Mock templates - would come from M006 Template Registry
      const mockTemplates: TemplateOption[] = [
        {
          id: 'api-docs',
          name: 'API Documentation',
          description: 'Generate comprehensive API documentation',
          category: 'API',
          preview: '# API Reference\n\n## Endpoints\n\n### GET /api/users',
          variables: ['title', 'version', 'baseUrl']
        },
        {
          id: 'component-docs',
          name: 'Component Documentation',
          description: 'Document React/Vue components',
          category: 'Frontend',
          preview: '# Component Name\n\n## Props\n\n## Usage',
          variables: ['componentName', 'author']
        },
        {
          id: 'readme',
          name: 'README Generator',
          description: 'Generate project README files',
          category: 'General',
          preview: '# Project Name\n\n## Installation\n\n## Usage',
          variables: ['projectName', 'description', 'author']
        }
      ];
      
      setTemplates(mockTemplates);
      setLoading(false);
    } catch (error) {
      console.error('Failed to load templates:', error);
      setLoading(false);
    }
  };

  const handleFileSelection = (filePath: string, selected: boolean) => {
    setFileContext(prev => 
      prev.map(file => 
        file.path === filePath ? { ...file, selected } : file
      )
    );

    if (selected) {
      setConfig(prev => ({
        ...prev,
        includeFiles: [...prev.includeFiles, filePath]
      }));
    } else {
      setConfig(prev => ({
        ...prev,
        includeFiles: prev.includeFiles.filter(path => path !== filePath)
      }));
    }
  };

  const handleTemplateSelect = (templateId: string) => {
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setConfig(prev => ({
        ...prev,
        templateId,
        variables: template.variables.reduce((acc, variable) => ({
          ...acc,
          [variable]: prev.variables[variable] || ''
        }), {})
      }));
    }
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    
    const steps: GenerationStep[] = [
      { id: 'analyze', label: 'Analyzing Context', description: 'Reading selected files', completed: false, active: true },
      { id: 'template', label: 'Processing Template', description: 'Applying template logic', completed: false, active: false },
      { id: 'generate', label: 'Generating Content', description: 'Creating documentation', completed: false, active: false },
      { id: 'review', label: 'Review Ready', description: 'Content ready for review', completed: false, active: false }
    ];
    
    setGenerationSteps(steps);

    try {
      // Simulate generation process
      for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        setGenerationSteps(prev => prev.map((step, index) => ({
          ...step,
          completed: index <= i,
          active: index === i + 1
        })));
      }

      // Mock generated content
      const mockContent = `# ${config.variables.componentName || 'Generated Documentation'}

This documentation was automatically generated by DevDocAI.

## Overview

Based on the analysis of the selected files, this component provides the following functionality:

## API Reference

### Props

| Prop | Type | Description |
|------|------|-------------|
| children | ReactNode | Content to render |
| variant | string | Visual variant |

## Usage Example

\`\`\`typescript
import { ${config.variables.componentName || 'Component'} } from './component';

function App() {
  return (
    <${config.variables.componentName || 'Component'} variant="primary">
      Hello World
    </${config.variables.componentName || 'Component'}>
  );
}
\`\`\`

## Generated: ${new Date().toLocaleString()}`;

      setGeneratedContent(mockContent);
      setActiveStep(4); // Move to review step
      
    } catch (error) {
      console.error('Generation failed:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSave = () => {
    // Send generated content back to VS Code
    eventManager.emitSimple(UIEventType.DOCUMENT_GENERATED, 'vscode', {
      content: generatedContent,
      path: config.outputPath,
      template: config.templateId
    });

    // Show success notification
    globalState.addNotification({
      type: 'success',
      title: 'Documentation Generated',
      message: 'Successfully created documentation file'
    });
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              Select files and directories to include in documentation generation:
            </Typography>
            
            {loading ? (
              <SkeletonLoader variant="list" count={3} />
            ) : fileContext.length === 0 ? (
              <EmptyState
                variant="no-documents"
                compact
                title="No Files Found"
                description="Open a workspace to see available files"
              />
            ) : (
              <List dense>
                {fileContext.map((file) => (
                  <ListItem
                    key={file.path}
                    button
                    onClick={() => handleFileSelection(file.path, !file.selected)}
                    sx={{
                      border: `1px solid ${file.selected ? 'primary.main' : 'divider'}`,
                      borderRadius: 1,
                      mb: 1
                    }}
                  >
                    <ListItemIcon>
                      {file.type === 'file' ? <InsertDriveFile /> : <Folder />}
                    </ListItemIcon>
                    <ListItemText
                      primary={file.name}
                      secondary={`${file.path} • ${file.size} bytes`}
                    />
                    {file.selected && <CheckCircle color="primary" />}
                  </ListItem>
                ))}
              </List>
            )}
          </Box>
        );

      case 1:
        return (
          <Box sx={{ mt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Template</InputLabel>
              <Select
                value={config.templateId}
                onChange={(e) => handleTemplateSelect(e.target.value as string)}
                label="Template"
              >
                {templates.map((template) => (
                  <MenuItem key={template.id} value={template.id}>
                    {template.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {config.templateId && (
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Template Preview
                  </Typography>
                  <Typography
                    component="pre"
                    variant="body2"
                    sx={{
                      backgroundColor: 'grey.100',
                      p: 1,
                      borderRadius: 1,
                      fontSize: '0.8rem',
                      overflow: 'auto',
                      fontFamily: 'monospace'
                    }}
                  >
                    {templates.find(t => t.id === config.templateId)?.preview}
                  </Typography>
                </CardContent>
              </Card>
            )}
          </Box>
        );

      case 2:
        const selectedTemplate = templates.find(t => t.id === config.templateId);
        return (
          <Box sx={{ mt: 2 }}>
            {selectedTemplate?.variables.map((variable) => (
              <TextField
                key={variable}
                fullWidth
                label={variable.charAt(0).toUpperCase() + variable.slice(1)}
                value={config.variables[variable] || ''}
                onChange={(e) => setConfig(prev => ({
                  ...prev,
                  variables: { ...prev.variables, [variable]: e.target.value }
                }))}
                sx={{ mb: 2 }}
              />
            ))}

            <TextField
              fullWidth
              label="Output Path"
              value={config.outputPath}
              onChange={(e) => setConfig(prev => ({ ...prev, outputPath: e.target.value }))}
              placeholder="docs/README.md"
              sx={{ mb: 2 }}
            />

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography>Advanced Options</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {Object.entries(config.options).map(([key, value]) => (
                    <Chip
                      key={key}
                      label={key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                      variant={value ? 'filled' : 'outlined'}
                      onClick={() => setConfig(prev => ({
                        ...prev,
                        options: { ...prev.options, [key]: !prev.options[key as keyof typeof prev.options] }
                      }))}
                      color={value ? 'primary' : 'default'}
                    />
                  ))}
                </Box>
              </AccordionDetails>
            </Accordion>
          </Box>
        );

      case 3:
        return (
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            {isGenerating ? (
              <>
                <LinearProgress sx={{ mb: 3 }} />
                <Typography variant="h6" gutterBottom>
                  Generating Documentation...
                </Typography>
                <List>
                  {generationSteps.map((step) => (
                    <ListItem key={step.id}>
                      <ListItemIcon>
                        {step.completed ? (
                          <CheckCircle color="success" />
                        ) : step.active ? (
                          <LoadingSpinner size="small" />
                        ) : (
                          <Description color="disabled" />
                        )}
                      </ListItemIcon>
                      <ListItemText
                        primary={step.label}
                        secondary={step.description}
                      />
                    </ListItem>
                  ))}
                </List>
              </>
            ) : (
              <>
                <Typography variant="h6" gutterBottom>
                  Ready to Generate
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Click generate to create documentation based on your selections
                </Typography>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<PlayArrow />}
                  onClick={handleGenerate}
                  disabled={!config.templateId || config.includeFiles.length === 0}
                >
                  Generate Documentation
                </Button>
              </>
            )}
          </Box>
        );

      case 4:
        return (
          <Box sx={{ mt: 2 }}>
            <Typography variant="h6" gutterBottom>
              Generated Documentation
            </Typography>
            
            <Card variant="outlined" sx={{ mb: 2 }}>
              <CardContent>
                <Typography
                  component="pre"
                  variant="body2"
                  sx={{
                    backgroundColor: 'grey.50',
                    p: 2,
                    borderRadius: 1,
                    fontSize: '0.8rem',
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    maxHeight: 400
                  }}
                >
                  {generatedContent}
                </Typography>
              </CardContent>
              <CardActions>
                <Button startIcon={<Edit />} size="small">
                  Edit
                </Button>
                <Button startIcon={<Preview />} size="small">
                  Preview
                </Button>
                <Button 
                  startIcon={<Save />} 
                  size="small" 
                  variant="contained"
                  onClick={handleSave}
                >
                  Save to File
                </Button>
              </CardActions>
            </Card>
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <WebviewPanel
      panelType="document-generator"
      title="Document Generator"
      showRefresh={true}
      showSettings={true}
    >
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* Stepper */}
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Stepper activeStep={activeStep} orientation="horizontal" nonLinear>
            {steps.map((step, index) => (
              <Step key={step.label}>
                <StepLabel
                  optional={
                    <Typography variant="caption">{step.description}</Typography>
                  }
                  onClick={() => setActiveStep(index)}
                  sx={{ cursor: 'pointer' }}
                >
                  {step.label}
                </StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>

        {/* Step Content */}
        <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2 }}>
          {renderStepContent(activeStep)}
        </Box>

        {/* Navigation */}
        <Box sx={{ 
          p: 2, 
          borderTop: 1, 
          borderColor: 'divider',
          display: 'flex',
          justifyContent: 'space-between'
        }}>
          <Button
            disabled={activeStep === 0}
            onClick={() => setActiveStep(prev => prev - 1)}
          >
            Back
          </Button>
          <Button
            variant="contained"
            onClick={() => setActiveStep(prev => prev + 1)}
            disabled={activeStep === steps.length - 1}
          >
            Next
          </Button>
        </Box>
      </Box>
    </WebviewPanel>
  );
};

export default DocumentGeneratorPanel;