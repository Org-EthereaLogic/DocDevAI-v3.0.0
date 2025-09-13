import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { projectAPI } from '@/services/api';

export const useProjectStore = defineStore('project', () => {
  // State
  const projects = ref([]);
  const currentProject = ref(null);
  const loading = ref(false);
  const error = ref(null);
  const searchQuery = ref('');
  const filters = ref({
    status: '', // 'active', 'archived', 'draft'
    type: '', // 'web', 'mobile', 'desktop', 'library', 'api'
    framework: '',
    sortBy: 'updated', // 'updated', 'created', 'name', 'documents'
    sortOrder: 'desc'
  });

  // Project types and frameworks
  const projectTypes = ref([
    { id: 'web', name: 'Web Application', icon: '🌐' },
    { id: 'mobile', name: 'Mobile App', icon: '📱' },
    { id: 'desktop', name: 'Desktop Application', icon: '💻' },
    { id: 'library', name: 'Library/Package', icon: '📦' },
    { id: 'api', name: 'API/Service', icon: '🔌' },
    { id: 'cli', name: 'CLI Tool', icon: '⌨️' },
    { id: 'other', name: 'Other', icon: '📂' }
  ]);

  const frameworks = ref([
    { id: 'react', name: 'React', category: 'web' },
    { id: 'vue', name: 'Vue.js', category: 'web' },
    { id: 'angular', name: 'Angular', category: 'web' },
    { id: 'nextjs', name: 'Next.js', category: 'web' },
    { id: 'nuxt', name: 'Nuxt.js', category: 'web' },
    { id: 'svelte', name: 'Svelte', category: 'web' },
    { id: 'react-native', name: 'React Native', category: 'mobile' },
    { id: 'flutter', name: 'Flutter', category: 'mobile' },
    { id: 'ionic', name: 'Ionic', category: 'mobile' },
    { id: 'electron', name: 'Electron', category: 'desktop' },
    { id: 'tauri', name: 'Tauri', category: 'desktop' },
    { id: 'express', name: 'Express.js', category: 'api' },
    { id: 'fastapi', name: 'FastAPI', category: 'api' },
    { id: 'django', name: 'Django', category: 'api' },
    { id: 'rails', name: 'Ruby on Rails', category: 'api' }
  ]);

  // Computed
  const filteredProjects = computed(() => {
    let filtered = projects.value;

    // Apply search filter
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase();
      filtered = filtered.filter(project =>
        project.name.toLowerCase().includes(query) ||
        project.description?.toLowerCase().includes(query) ||
        project.tags?.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Apply status filter
    if (filters.value.status) {
      filtered = filtered.filter(project => project.status === filters.value.status);
    }

    // Apply type filter
    if (filters.value.type) {
      filtered = filtered.filter(project => project.type === filters.value.type);
    }

    // Apply framework filter
    if (filters.value.framework) {
      filtered = filtered.filter(project => project.framework === filters.value.framework);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      const { sortBy, sortOrder } = filters.value;
      let aVal = a[sortBy];
      let bVal = b[sortBy];

      if (sortBy === 'name') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      } else if (sortBy === 'updated' || sortBy === 'created') {
        aVal = new Date(aVal);
        bVal = new Date(bVal);
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return filtered;
  });

  const activeProjects = computed(() =>
    projects.value.filter(p => p.status === 'active')
  );

  const recentProjects = computed(() =>
    projects.value
      .filter(p => p.status === 'active')
      .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
      .slice(0, 5)
  );

  const projectStats = computed(() => {
    const stats = {
      total: projects.value.length,
      active: 0,
      archived: 0,
      draft: 0,
      totalDocuments: 0,
      typeCounts: {}
    };

    projects.value.forEach(project => {
      stats[project.status]++;
      stats.totalDocuments += project.documentCount || 0;

      if (stats.typeCounts[project.type]) {
        stats.typeCounts[project.type]++;
      } else {
        stats.typeCounts[project.type] = 1;
      }
    });

    return stats;
  });

  const hasProjects = computed(() => projects.value.length > 0);
  const hasError = computed(() => !!error.value);

  // Actions
  const fetchProjects = async () => {
    loading.value = true;
    error.value = null;

    try {
      const response = await projectAPI.getProjects();
      projects.value = response.data.data || [];
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to fetch projects';
      console.error('Error fetching projects:', err);
    } finally {
      loading.value = false;
    }
  };

  const createProject = async (projectData) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await projectAPI.createProject(projectData);
      const newProject = response.data;

      projects.value.unshift(newProject);
      currentProject.value = newProject;

      return newProject;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to create project';
      console.error('Error creating project:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const updateProject = async (id, updates) => {
    loading.value = true;
    error.value = null;

    try {
      const response = await projectAPI.updateProject(id, updates);
      const updatedProject = response.data;

      const index = projects.value.findIndex(p => p.id === id);
      if (index !== -1) {
        projects.value[index] = updatedProject;
      }

      if (currentProject.value?.id === id) {
        currentProject.value = updatedProject;
      }

      return updatedProject;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to update project';
      console.error('Error updating project:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const deleteProject = async (id) => {
    loading.value = true;
    error.value = null;

    try {
      await projectAPI.deleteProject(id);

      projects.value = projects.value.filter(p => p.id !== id);

      if (currentProject.value?.id === id) {
        currentProject.value = null;
      }

      return true;
    } catch (err) {
      error.value = err.response?.data?.message || 'Failed to delete project';
      console.error('Error deleting project:', err);
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const setCurrentProject = (project) => {
    currentProject.value = project;

    // Store in session storage for persistence
    if (project) {
      sessionStorage.setItem('currentProject', JSON.stringify(project));
    } else {
      sessionStorage.removeItem('currentProject');
    }
  };

  const loadCurrentProject = () => {
    const stored = sessionStorage.getItem('currentProject');
    if (stored) {
      try {
        currentProject.value = JSON.parse(stored);
      } catch (err) {
        console.error('Error loading current project:', err);
        sessionStorage.removeItem('currentProject');
      }
    }
  };

  const searchProjects = (query) => {
    searchQuery.value = query;
  };

  const applyFilters = (newFilters) => {
    filters.value = { ...filters.value, ...newFilters };
  };

  const resetFilters = () => {
    searchQuery.value = '';
    filters.value = {
      status: '',
      type: '',
      framework: '',
      sortBy: 'updated',
      sortOrder: 'desc'
    };
  };

  const archiveProject = async (id) => {
    return await updateProject(id, { status: 'archived' });
  };

  const restoreProject = async (id) => {
    return await updateProject(id, { status: 'active' });
  };

  const duplicateProject = async (id) => {
    const original = projects.value.find(p => p.id === id);
    if (!original) {
      throw new Error('Project not found');
    }

    const duplicateData = {
      ...original,
      name: `${original.name} (Copy)`,
      id: undefined, // Let the server generate new ID
      createdAt: undefined,
      updatedAt: undefined,
      status: 'draft'
    };

    return await createProject(duplicateData);
  };

  const clearError = () => {
    error.value = null;
  };

  // Project validation
  const validateProject = (projectData) => {
    const errors = [];

    if (!projectData.name || projectData.name.trim().length === 0) {
      errors.push('Project name is required');
    }

    if (projectData.name && projectData.name.length > 100) {
      errors.push('Project name must be less than 100 characters');
    }

    if (!projectData.type) {
      errors.push('Project type is required');
    }

    if (projectData.description && projectData.description.length > 500) {
      errors.push('Project description must be less than 500 characters');
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  };

  // Initialize store
  const initialize = () => {
    loadCurrentProject();
  };

  // Reset store
  const $reset = () => {
    projects.value = [];
    currentProject.value = null;
    loading.value = false;
    error.value = null;
    searchQuery.value = '';
    filters.value = {
      status: '',
      type: '',
      framework: '',
      sortBy: 'updated',
      sortOrder: 'desc'
    };
    sessionStorage.removeItem('currentProject');
  };

  return {
    // State
    projects,
    currentProject,
    loading,
    error,
    searchQuery,
    filters,
    projectTypes,
    frameworks,

    // Computed
    filteredProjects,
    activeProjects,
    recentProjects,
    projectStats,
    hasProjects,
    hasError,

    // Actions
    fetchProjects,
    createProject,
    updateProject,
    deleteProject,
    setCurrentProject,
    loadCurrentProject,
    searchProjects,
    applyFilters,
    resetFilters,
    archiveProject,
    restoreProject,
    duplicateProject,
    clearError,
    validateProject,
    initialize,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'project',
        storage: localStorage,
        paths: ['searchQuery', 'filters']
      }
    ]
  }
});
