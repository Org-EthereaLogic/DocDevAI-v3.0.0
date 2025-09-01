/**
 * DevDocAI v3.0.0 - Template Manager Component
 * 
 * Interface for M006 Template Registry module
 * Provides template management, editing, and customization capabilities.
 */

import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Grid,
  Chip,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
} from '@mui/material';
import {
  Add as AddIcon,
  Article as TemplateIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Preview as PreviewIcon,
  Download as DownloadIcon,
  Upload as UploadIcon,
  Copy as CopyIcon,
  Folder as CategoryIcon,
} from '@mui/icons-material';

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  content: string;
  variables: string[];
  isCustom: boolean;
  createdAt: Date;
  lastModified: Date;
  usage: number;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel = ({ children, value, index, ...other }: TabPanelProps) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`template-tabpanel-${index}`}
      aria-labelledby={`template-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
};

const TemplateManager: React.FC = () => {
  const [templates, setTemplates] = useState<Template[]>([
    {
      id: '1',
      name: 'API Documentation',
      description: 'REST API documentation with endpoints and examples',
      category: 'API',
      content: '# {{title}}\n\n## Overview\n{{overview}}\n\n## Endpoints\n{{endpoints}}',
      variables: ['title', 'overview', 'endpoints'],
      isCustom: false,
      createdAt: new Date('2024-01-01'),
      lastModified: new Date('2024-01-15'),
      usage: 45,
    },
    {
      id: '2',
      name: 'README Generator',
      description: 'Standard project README with setup instructions',
      category: 'General',
      content: '# {{project_name}}\n\n{{description}}\n\n## Installation\n{{installation}}',
      variables: ['project_name', 'description', 'installation'],
      isCustom: false,
      createdAt: new Date('2024-01-01'),
      lastModified: new Date('2024-01-10'),
      usage: 78,
    },
    {
      id: '3',
      name: 'Custom User Guide',
      description: 'Custom template for user documentation',
      category: 'User Docs',
      content: '# User Guide: {{guide_name}}\n\n{{content}}',
      variables: ['guide_name', 'content'],
      isCustom: true,
      createdAt: new Date('2024-02-01'),
      lastModified: new Date('2024-02-05'),
      usage: 12,
    },
  ]);
  
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchTerm, setSearchTerm] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [showCustomOnly, setShowCustomOnly] = useState(false);

  // Template form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    content: '',
  });

  const categories = ['All', 'API', 'General', 'User Docs', 'Technical', 'Code'];

  const filteredTemplates = templates.filter(template => {
    const matchesSearch = template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         template.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'All' || template.category === selectedCategory;
    const matchesCustomFilter = !showCustomOnly || template.isCustom;
    
    return matchesSearch && matchesCategory && matchesCustomFilter;
  });

  const handleCreateTemplate = () => {
    setSelectedTemplate(null);
    setFormData({ name: '', description: '', category: '', content: '' });
    setDialogOpen(true);
  };

  const handleEditTemplate = (template: Template) => {
    setSelectedTemplate(template);
    setFormData({
      name: template.name,
      description: template.description,
      category: template.category,
      content: template.content,
    });
    setDialogOpen(true);
  };

  const handleSaveTemplate = () => {
    if (selectedTemplate) {
      // Edit existing template
      setTemplates(prev => prev.map(t => 
        t.id === selectedTemplate.id 
          ? { ...t, ...formData, lastModified: new Date() }
          : t
      ));
    } else {
      // Create new template
      const newTemplate: Template = {
        id: Date.now().toString(),
        ...formData,
        variables: extractVariables(formData.content),
        isCustom: true,
        createdAt: new Date(),
        lastModified: new Date(),
        usage: 0,
      };
      setTemplates(prev => [...prev, newTemplate]);
    }
    setDialogOpen(false);
  };

  const handleDeleteTemplate = (templateId: string) => {
    setTemplates(prev => prev.filter(t => t.id !== templateId));
  };

  const extractVariables = (content: string): string[] => {
    const matches = content.match(/\{\{(\w+)\}\}/g);
    return matches ? [...new Set(matches.map(match => match.slice(2, -2)))] : [];
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Template Manager
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Manage, edit, and customize documentation templates for consistent generation.
      </Typography>

      {/* Controls */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={4}>
              <TextField
                label="Search Templates"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                fullWidth
                size="small"
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Category</InputLabel>
                <Select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  label="Category"
                >
                  {categories.map((category) => (
                    <MenuItem key={category} value={category}>
                      {category}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={3}>
              <FormControlLabel
                control={
                  <Switch
                    checked={showCustomOnly}
                    onChange={(e) => setShowCustomOnly(e.target.checked)}
                  />
                }
                label="Custom Only"
              />
            </Grid>
            <Grid item xs={12} sm={2}>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={handleCreateTemplate}
                fullWidth
              >
                New Template
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Template Grid */}
      <Grid container spacing={3}>
        {filteredTemplates.map((template) => (
          <Grid item xs={12} sm={6} md={4} key={template.id}>
            <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              <CardContent sx={{ flexGrow: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    {template.name}
                  </Typography>
                  {template.isCustom && (
                    <Chip label="Custom" size="small" color="secondary" />
                  )}
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {template.description}
                </Typography>

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                  <CategoryIcon fontSize="small" color="action" />
                  <Typography variant="caption">{template.category}</Typography>
                </Box>

                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    Variables: {template.variables.length}
                  </Typography>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                    {template.variables.slice(0, 3).map((variable) => (
                      <Chip
                        key={variable}
                        label={`{{${variable}}}`}
                        size="small"
                        variant="outlined"
                      />
                    ))}
                    {template.variables.length > 3 && (
                      <Chip
                        label={`+${template.variables.length - 3} more`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Box>

                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Used {template.usage} times
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Modified: {template.lastModified.toLocaleDateString()}
                  </Typography>
                </Box>
              </CardContent>

              <CardContent sx={{ pt: 0 }}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <IconButton size="small" title="Preview">
                    <PreviewIcon />
                  </IconButton>
                  <IconButton size="small" title="Edit" onClick={() => handleEditTemplate(template)}>
                    <EditIcon />
                  </IconButton>
                  <IconButton size="small" title="Copy">
                    <CopyIcon />
                  </IconButton>
                  <IconButton size="small" title="Download">
                    <DownloadIcon />
                  </IconButton>
                  {template.isCustom && (
                    <IconButton 
                      size="small" 
                      title="Delete" 
                      color="error"
                      onClick={() => handleDeleteTemplate(template.id)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {filteredTemplates.length === 0 && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Alert severity="info">
              No templates found matching your criteria. Try adjusting your search or filters, or create a new template.
            </Alert>
          </CardContent>
        </Card>
      )}

      {/* Template Editor Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedTemplate ? 'Edit Template' : 'Create New Template'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs value={currentTab} onChange={handleTabChange}>
              <Tab label="Basic Info" />
              <Tab label="Content" />
              <Tab label="Preview" />
            </Tabs>
          </Box>

          <TabPanel value={currentTab} index={0}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Template Name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                fullWidth
                required
              />
              <TextField
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                fullWidth
                multiline
                rows={2}
                required
              />
              <FormControl fullWidth required>
                <InputLabel>Category</InputLabel>
                <Select
                  value={formData.category}
                  onChange={(e) => setFormData(prev => ({ ...prev, category: e.target.value }))}
                  label="Category"
                >
                  {categories.slice(1).map((category) => (
                    <MenuItem key={category} value={category}>
                      {category}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </TabPanel>

          <TabPanel value={currentTab} index={1}>
            <TextField
              label="Template Content"
              value={formData.content}
              onChange={(e) => setFormData(prev => ({ ...prev, content: e.target.value }))}
              fullWidth
              multiline
              rows={10}
              placeholder="Use {{variable_name}} for template variables"
              helperText={`Variables detected: ${extractVariables(formData.content).join(', ')}`}
            />
          </TabPanel>

          <TabPanel value={currentTab} index={2}>
            <Paper sx={{ p: 2, backgroundColor: 'grey.50', minHeight: 200 }}>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {formData.content || 'Template content will appear here...'}
              </Typography>
            </Paper>
          </TabPanel>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleSaveTemplate}
            variant="contained"
            disabled={!formData.name || !formData.description || !formData.category}
          >
            {selectedTemplate ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default TemplateManager;