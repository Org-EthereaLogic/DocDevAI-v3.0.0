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
}

const DocumentGenerator: React.FC = () => {
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [projectPath, setProjectPath] = useState('');
  const [outputFormat, setOutputFormat] = useState('markdown');
  const [customPrompt, setCustomPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [jobs, setJobs] = useState<GenerationJob[]>([]);

  const templates = [
    { id: 'api-docs', name: 'API Documentation', description: 'REST API documentation with examples' },
    { id: 'readme', name: 'README Generator', description: 'Project README with setup instructions' },
    { id: 'code-docs', name: 'Code Documentation', description: 'Inline code documentation' },
    { id: 'user-guide', name: 'User Guide', description: 'End-user documentation' },
    { id: 'changelog', name: 'Changelog', description: 'Version history and changes' },
    { id: 'technical-spec', name: 'Technical Specification', description: 'Detailed technical documentation' },
  ];

  const handleGenerate = async () => {
    if (!selectedTemplate || !projectPath) return;

    const newJob: GenerationJob = {
      id: Date.now().toString(),
      title: `Documentation for ${projectPath}`,
      template: selectedTemplate,
      status: 'generating',
      progress: 0,
      createdAt: new Date(),
    };

    setJobs(prev => [newJob, ...prev]);
    setIsGenerating(true);

    // Simulate document generation process
    try {
      const progressInterval = setInterval(() => {
        setJobs(prev => prev.map(job => 
          job.id === newJob.id 
            ? { ...job, progress: Math.min(job.progress + Math.random() * 20, 95) }
            : job
        ));
      }, 500);

      // Simulate generation completion
      setTimeout(() => {
        clearInterval(progressInterval);
        setJobs(prev => prev.map(job => 
          job.id === newJob.id 
            ? { ...job, status: 'complete', progress: 100 }
            : job
        ));
        setIsGenerating(false);
      }, 3000);
    } catch (error) {
      setJobs(prev => prev.map(job => 
        job.id === newJob.id 
          ? { ...job, status: 'error', progress: 0 }
          : job
      ));
      setIsGenerating(false);
    }
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

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <TextField
                  label="Project Path"
                  value={projectPath}
                  onChange={(e) => setProjectPath(e.target.value)}
                  placeholder="/path/to/your/project"
                  fullWidth
                  required
                />

                <FormControl fullWidth required>
                  <InputLabel>Template</InputLabel>
                  <Select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    label="Template"
                  >
                    {templates.map((template) => (
                      <MenuItem key={template.id} value={template.id}>
                        <Box>
                          <Typography variant="body2">{template.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
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
                    onChange={(e) => setOutputFormat(e.target.value)}
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
                  onChange={(e) => setCustomPrompt(e.target.value)}
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
                    onClick={() => setSelectedTemplate(template.id)}
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
                                <IconButton size="small">
                                  <PreviewIcon />
                                </IconButton>
                                <IconButton size="small">
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
                            <Box>
                              <Typography variant="caption" display="block">
                                Template: {templates.find(t => t.id === job.template)?.name}
                              </Typography>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                                <Chip 
                                  label={job.status} 
                                  size="small" 
                                  color={getStatusColor(job.status)}
                                />
                                {job.status === 'generating' && (
                                  <Box sx={{ flexGrow: 1, ml: 1 }}>
                                    <LinearProgress 
                                      variant="determinate" 
                                      value={job.progress}
                                      sx={{ height: 4, borderRadius: 2 }}
                                    />
                                  </Box>
                                )}
                              </Box>
                            </Box>
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