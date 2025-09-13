import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { trackingAPI } from '@/services/api';
import { useNotificationStore } from './notification';

export const useTrackingStore = defineStore('tracking', () => {
  // State
  const dependencies = ref(new Map());
  const documents = ref(new Map());
  const relationships = ref([]);
  const impactAnalysis = ref(null);
  const circularReferences = ref([]);
  const isLoading = ref(false);
  const error = ref(null);

  // Tracking matrix configuration
  const config = ref({
    maxDepth: 5,
    includeImplicit: true,
    trackVersions: true,
    autoUpdate: true,
    visualizationMode: 'graph' // 'graph', 'tree', 'table'
  });

  // Relationship types based on M005 backend
  const relationshipTypes = ref([
    {
      id: 'DEPENDS_ON',
      name: 'Depends On',
      color: '#3B82F6',
      icon: '→',
      description: 'Document A depends on Document B'
    },
    {
      id: 'REFERENCES',
      name: 'References',
      color: '#10B981',
      icon: '↗',
      description: 'Document A references Document B'
    },
    {
      id: 'IMPLEMENTS',
      name: 'Implements',
      color: '#8B5CF6',
      icon: '⚡',
      description: 'Document A implements specifications from Document B'
    },
    {
      id: 'EXTENDS',
      name: 'Extends',
      color: '#F59E0B',
      icon: '⬆',
      description: 'Document A extends functionality described in Document B'
    },
    {
      id: 'CONFLICTS',
      name: 'Conflicts',
      color: '#EF4444',
      icon: '⚠',
      description: 'Document A conflicts with Document B'
    },
    {
      id: 'SUPERSEDES',
      name: 'Supersedes',
      color: '#6B7280',
      icon: '↑',
      description: 'Document A supersedes Document B'
    },
    {
      id: 'DUPLICATES',
      name: 'Duplicates',
      color: '#F97316',
      icon: '⚊',
      description: 'Document A duplicates content from Document B'
    }
  ]);

  // Analysis metrics
  const analysisMetrics = ref({
    totalNodes: 0,
    totalEdges: 0,
    averageConnections: 0,
    isolatedDocuments: 0,
    criticalPaths: 0,
    complexityScore: 0,
    healthScore: 0
  });

  // Impact analysis results
  const impactResults = ref({
    directImpacts: [],
    indirectImpacts: [],
    riskLevel: 'low',
    affectedDocuments: 0,
    recommendedActions: []
  });

  // Computed
  const dependencyGraph = computed(() => {
    const nodes = [];
    const edges = [];

    // Convert documents to nodes
    documents.value.forEach((doc, id) => {
      nodes.push({
        id,
        label: doc.name,
        type: doc.type,
        status: doc.status,
        healthScore: doc.healthScore || 0,
        lastModified: doc.lastModified
      });
    });

    // Convert relationships to edges
    relationships.value.forEach(rel => {
      edges.push({
        id: `${rel.source}-${rel.target}`,
        source: rel.source,
        target: rel.target,
        type: rel.type,
        strength: rel.strength || 1,
        bidirectional: rel.bidirectional || false
      });
    });

    return { nodes, edges };
  });

  const orphanedDocuments = computed(() => {
    const connectedDocs = new Set();
    relationships.value.forEach(rel => {
      connectedDocs.add(rel.source);
      connectedDocs.add(rel.target);
    });

    return Array.from(documents.value.values()).filter(
      doc => !connectedDocs.has(doc.id)
    );
  });

  const criticalDocuments = computed(() => {
    // Documents with many dependencies (high fan-in/fan-out)
    const dependencyCounts = new Map();

    relationships.value.forEach(rel => {
      dependencyCounts.set(rel.source, (dependencyCounts.get(rel.source) || 0) + 1);
      dependencyCounts.set(rel.target, (dependencyCounts.get(rel.target) || 0) + 1);
    });

    return Array.from(documents.value.values())
      .filter(doc => (dependencyCounts.get(doc.id) || 0) >= 3)
      .sort((a, b) => (dependencyCounts.get(b.id) || 0) - (dependencyCounts.get(a.id) || 0));
  });

  const inconsistentDocuments = computed(() => {
    // Documents with conflicting relationships or circular dependencies
    const inconsistent = [];

    circularReferences.value.forEach(cycle => {
      cycle.forEach(docId => {
        const doc = documents.value.get(docId);
        if (doc && !inconsistent.find(d => d.id === docId)) {
          inconsistent.push(doc);
        }
      });
    });

    return inconsistent;
  });

  const relationshipsByType = computed(() => {
    const grouped = {};
    relationshipTypes.value.forEach(type => {
      grouped[type.id] = relationships.value.filter(rel => rel.type === type.id);
    });
    return grouped;
  });

  const matrixComplexity = computed(() => {
    const nodeCount = documents.value.size;
    const edgeCount = relationships.value.length;
    const avgConnections = nodeCount > 0 ? edgeCount / nodeCount : 0;

    // Complexity scoring based on graph theory metrics
    let score = 0;

    if (avgConnections > 5) score += 30; // High connectivity
    else if (avgConnections > 3) score += 20;
    else if (avgConnections > 1) score += 10;

    if (circularReferences.value.length > 0) score += 25; // Circular dependencies
    if (orphanedDocuments.value.length > nodeCount * 0.2) score += 15; // Too many orphans
    if (criticalDocuments.value.length > nodeCount * 0.3) score += 20; // Too many critical nodes

    return Math.min(100, score);
  });

  // Actions
  const fetchTrackingMatrix = async (projectId) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await trackingAPI.getMatrix(projectId);

      // Clear existing data
      documents.value.clear();
      dependencies.value.clear();
      relationships.value = [];

      // Load documents
      response.documents?.forEach(doc => {
        documents.value.set(doc.id, doc);
      });

      // Load relationships
      relationships.value = response.relationships || [];

      // Load circular references
      circularReferences.value = response.circularReferences || [];

      // Update metrics
      updateAnalysisMetrics();

      return response;
    } catch (err) {
      const errorMessage = err.response?.data?.message || 'Failed to fetch tracking matrix';
      error.value = errorMessage;

      const notificationStore = useNotificationStore();
      notificationStore.addError('Tracking Matrix Error', errorMessage);

      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const addDocument = (document) => {
    documents.value.set(document.id, document);
    updateAnalysisMetrics();
  };

  const removeDocument = (documentId) => {
    documents.value.delete(documentId);

    // Remove related relationships
    relationships.value = relationships.value.filter(
      rel => rel.source !== documentId && rel.target !== documentId
    );

    updateAnalysisMetrics();
  };

  const addRelationship = async (sourceId, targetId, type, metadata = {}) => {
    try {
      const relationship = {
        id: `${sourceId}-${targetId}-${type}`,
        source: sourceId,
        target: targetId,
        type,
        strength: metadata.strength || 1,
        bidirectional: metadata.bidirectional || false,
        createdAt: new Date().toISOString(),
        metadata
      };

      relationships.value.push(relationship);

      // Check for new circular references
      await detectCircularReferences();

      updateAnalysisMetrics();

      return relationship;
    } catch (err) {
      error.value = err.message;
      throw err;
    }
  };

  const removeRelationship = (relationshipId) => {
    relationships.value = relationships.value.filter(rel => rel.id !== relationshipId);
    updateAnalysisMetrics();
  };

  const analyzeImpact = async (documentId, changeType = 'modify') => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await trackingAPI.analyzeImpact(documentId, {
        changeType,
        maxDepth: config.value.maxDepth,
        includeImplicit: config.value.includeImplicit
      });

      impactAnalysis.value = response;
      impactResults.value = {
        directImpacts: response.directImpacts || [],
        indirectImpacts: response.indirectImpacts || [],
        riskLevel: response.riskLevel || 'low',
        affectedDocuments: response.affectedDocuments || 0,
        recommendedActions: response.recommendedActions || []
      };

      return response;
    } catch (err) {
      error.value = err.message;
      const notificationStore = useNotificationStore();
      notificationStore.addError('Impact Analysis Failed', err.message);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const detectCircularReferences = async () => {
    try {
      // Use Tarjan's algorithm on the frontend for immediate feedback
      const visited = new Set();
      const recursionStack = new Set();
      const cycles = [];

      const dfs = (nodeId, path = []) => {
        if (recursionStack.has(nodeId)) {
          // Found a cycle
          const cycleStart = path.indexOf(nodeId);
          if (cycleStart !== -1) {
            cycles.push(path.slice(cycleStart).concat([nodeId]));
          }
          return;
        }

        if (visited.has(nodeId)) return;

        visited.add(nodeId);
        recursionStack.add(nodeId);

        // Get outgoing relationships
        const outgoing = relationships.value.filter(rel => rel.source === nodeId);
        outgoing.forEach(rel => {
          dfs(rel.target, [...path, nodeId]);
        });

        recursionStack.delete(nodeId);
      };

      // Start DFS from each unvisited node
      documents.value.forEach((_, docId) => {
        if (!visited.has(docId)) {
          dfs(docId);
        }
      });

      circularReferences.value = cycles;
      return cycles;
    } catch (err) {
      console.error('Error detecting circular references:', err);
      return [];
    }
  };

  const findDependencyPath = (sourceId, targetId) => {
    // BFS to find shortest path
    const queue = [[sourceId]];
    const visited = new Set([sourceId]);

    while (queue.length > 0) {
      const path = queue.shift();
      const currentNode = path[path.length - 1];

      if (currentNode === targetId) {
        return path;
      }

      // Get outgoing relationships
      const outgoing = relationships.value.filter(rel => rel.source === currentNode);

      for (const rel of outgoing) {
        if (!visited.has(rel.target)) {
          visited.add(rel.target);
          queue.push([...path, rel.target]);
        }
      }
    }

    return null; // No path found
  };

  const updateAnalysisMetrics = () => {
    const nodeCount = documents.value.size;
    const edgeCount = relationships.value.length;

    analysisMetrics.value = {
      totalNodes: nodeCount,
      totalEdges: edgeCount,
      averageConnections: nodeCount > 0 ? edgeCount / nodeCount : 0,
      isolatedDocuments: orphanedDocuments.value.length,
      criticalPaths: criticalDocuments.value.length,
      complexityScore: matrixComplexity.value,
      healthScore: calculateHealthScore()
    };
  };

  const calculateHealthScore = () => {
    const nodeCount = documents.value.size;
    if (nodeCount === 0) return 100;

    let score = 100;

    // Penalize for complexity
    score -= matrixComplexity.value * 0.3;

    // Penalize for circular references
    score -= circularReferences.value.length * 10;

    // Penalize for too many orphaned documents
    const orphanRatio = orphanedDocuments.value.length / nodeCount;
    if (orphanRatio > 0.2) score -= (orphanRatio - 0.2) * 100;

    // Reward good connectivity (not too sparse, not too dense)
    const avgConnections = relationships.value.length / nodeCount;
    if (avgConnections >= 1 && avgConnections <= 3) {
      score += 10;
    }

    return Math.max(0, Math.round(score));
  };

  const exportMatrix = (format = 'json') => {
    const data = {
      documents: Array.from(documents.value.values()),
      relationships: relationships.value,
      circularReferences: circularReferences.value,
      metrics: analysisMetrics.value,
      exportDate: new Date().toISOString()
    };

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json'
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tracking-matrix-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else if (format === 'graphml') {
      // Export as GraphML for visualization tools
      let graphml = '<?xml version="1.0" encoding="UTF-8"?>\n';
      graphml += '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n';
      graphml += '  <graph id="dependency-graph" edgedefault="directed">\n';

      // Add nodes
      documents.value.forEach(doc => {
        graphml += `    <node id="${doc.id}">\n`;
        graphml += `      <data key="name">${doc.name}</data>\n`;
        graphml += `      <data key="type">${doc.type}</data>\n`;
        graphml += `    </node>\n`;
      });

      // Add edges
      relationships.value.forEach(rel => {
        graphml += `    <edge source="${rel.source}" target="${rel.target}">\n`;
        graphml += `      <data key="type">${rel.type}</data>\n`;
        graphml += `    </edge>\n`;
      });

      graphml += '  </graph>\n</graphml>';

      const blob = new Blob([graphml], { type: 'application/xml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tracking-matrix-${Date.now()}.graphml`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const updateConfiguration = (newConfig) => {
    config.value = { ...config.value, ...newConfig };
  };

  const clearError = () => {
    error.value = null;
  };

  // Reset store
  const $reset = () => {
    dependencies.value.clear();
    documents.value.clear();
    relationships.value = [];
    impactAnalysis.value = null;
    circularReferences.value = [];
    isLoading.value = false;
    error.value = null;
    analysisMetrics.value = {
      totalNodes: 0,
      totalEdges: 0,
      averageConnections: 0,
      isolatedDocuments: 0,
      criticalPaths: 0,
      complexityScore: 0,
      healthScore: 0
    };
    impactResults.value = {
      directImpacts: [],
      indirectImpacts: [],
      riskLevel: 'low',
      affectedDocuments: 0,
      recommendedActions: []
    };
  };

  return {
    // State
    dependencies,
    documents,
    relationships,
    impactAnalysis,
    circularReferences,
    isLoading,
    error,
    config,
    relationshipTypes,
    analysisMetrics,
    impactResults,

    // Computed
    dependencyGraph,
    orphanedDocuments,
    criticalDocuments,
    inconsistentDocuments,
    relationshipsByType,
    matrixComplexity,

    // Actions
    fetchTrackingMatrix,
    addDocument,
    removeDocument,
    addRelationship,
    removeRelationship,
    analyzeImpact,
    detectCircularReferences,
    findDependencyPath,
    updateAnalysisMetrics,
    calculateHealthScore,
    exportMatrix,
    updateConfiguration,
    clearError,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'tracking',
        storage: localStorage,
        paths: [
          'config',
          'analysisMetrics'
        ]
      }
    ]
  }
});
