'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { generateDocument, enhanceDocument, analyzeDocument, listTemplates } from '@/lib/api'
import { LoadingSpinner } from '@/components/ui/loading'

interface Template {
  id: string
  name: string
  description: string
}

interface AnalysisResult {
  quality_score: number
  entropy_score: number
  suggestions: string[]
  issues_found: number
}

export default function DocumentStudio() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [context, setContext] = useState('')
  const [generatedContent, setGeneratedContent] = useState('')
  const [enhancedContent, setEnhancedContent] = useState('')
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  
  const [isGenerating, setIsGenerating] = useState(false)
  const [isEnhancing, setIsEnhancing] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  
  const [activeTab, setActiveTab] = useState<'generate' | 'enhance' | 'analyze'>('generate')

  // Load templates on component mount
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const response = await listTemplates()
        setTemplates(response.templates as Template[])
        if (response.templates.length > 0) {
          const firstTemplate = response.templates[0] as Template
          setSelectedTemplate(firstTemplate.id)
        }
      } catch (error) {
        console.error('Failed to load templates:', error)
      }
    }
    loadTemplates()
  }, [])

  const handleGenerate = async () => {
    if (!selectedTemplate || !context.trim()) return
    
    setIsGenerating(true)
    try {
      const contextObj = JSON.parse(context)
      const result = await generateDocument({
        template: selectedTemplate,
        context: contextObj
      })
      setGeneratedContent(result.content)
      setActiveTab('enhance')
    } catch (error) {
      console.error('Generation failed:', error)
      alert('Generation failed. Please check your context JSON format.')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleEnhance = async () => {
    if (!generatedContent.trim()) return
    
    setIsEnhancing(true)
    try {
      const result = await enhanceDocument({
        content: generatedContent,
        strategy: 'MIAIR_ENHANCED'
      })
      setEnhancedContent(result.enhanced_content)
      setActiveTab('analyze')
    } catch (error) {
      console.error('Enhancement failed:', error)
      alert('Enhancement failed. Please try again.')
    } finally {
      setIsEnhancing(false)
    }
  }

  const handleAnalyze = async () => {
    const contentToAnalyze = enhancedContent || generatedContent
    if (!contentToAnalyze.trim()) return
    
    setIsAnalyzing(true)
    try {
      const result = await analyzeDocument({
        content: contentToAnalyze,
        include_suggestions: true
      })
      setAnalysis(result as AnalysisResult)
    } catch (error) {
      console.error('Analysis failed:', error)
      alert('Analysis failed. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AI</span>
              </div>
              <h1 className="text-xl font-bold text-gray-900">Document Studio</h1>
            </div>
            <Link 
              href="/" 
              className="text-gray-600 hover:text-gray-900 font-medium"
            >
              ← Back to Home
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab Navigation */}
        <div className="flex space-x-1 bg-gray-100 rounded-lg p-1 mb-8">
          {(['generate', 'enhance', 'analyze'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2 px-4 rounded-md font-medium text-sm transition-colors ${
                activeTab === tab
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab === 'generate' && '1. Generate'}
              {tab === 'enhance' && '2. Enhance'}
              {tab === 'analyze' && '3. Analyze'}
            </button>
          ))}
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Column - Input */}
          <div className="space-y-6">
            {activeTab === 'generate' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Template
                  </label>
                  <select
                    value={selectedTemplate}
                    onChange={(e) => setSelectedTemplate(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {templates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.name} - {template.description}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Context (JSON)
                  </label>
                  <textarea
                    value={context}
                    onChange={(e) => setContext(e.target.value)}
                    placeholder='{\n  "title": "My Project",\n  "description": "A great project"\n}'
                    className="w-full h-64 border border-gray-300 rounded-lg px-3 py-2 font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={isGenerating || !selectedTemplate || !context.trim()}
                  className="w-full bg-gradient-to-r from-blue-500 to-purple-500 text-white py-3 rounded-lg font-medium hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {isGenerating ? (
                    <>
                      <LoadingSpinner size="sm" />
                      <span className="ml-2">Generating...</span>
                    </>
                  ) : (
                    '🚀 Generate Document'
                  )}
                </button>
              </>
            )}

            {activeTab === 'enhance' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Generated Content
                  </label>
                  <textarea
                    value={generatedContent}
                    onChange={(e) => setGeneratedContent(e.target.value)}
                    className="w-full h-64 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Generate content first, or paste content here to enhance..."
                  />
                </div>

                <button
                  onClick={handleEnhance}
                  disabled={isEnhancing || !generatedContent.trim()}
                  className="w-full bg-gradient-to-r from-green-500 to-teal-500 text-white py-3 rounded-lg font-medium hover:from-green-600 hover:to-teal-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {isEnhancing ? (
                    <>
                      <LoadingSpinner size="sm" />
                      <span className="ml-2">Enhancing with MIAIR...</span>
                    </>
                  ) : (
                    '✨ Enhance with AI'
                  )}
                </button>
              </>
            )}

            {activeTab === 'analyze' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Content to Analyze
                  </label>
                  <textarea
                    value={enhancedContent || generatedContent}
                    onChange={(e) => enhancedContent ? setEnhancedContent(e.target.value) : setGeneratedContent(e.target.value)}
                    className="w-full h-64 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Content will appear here after generation/enhancement..."
                  />
                </div>

                <button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing || !(enhancedContent || generatedContent).trim()}
                  className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white py-3 rounded-lg font-medium hover:from-purple-600 hover:to-pink-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {isAnalyzing ? (
                    <>
                      <LoadingSpinner size="sm" />
                      <span className="ml-2">Analyzing Quality...</span>
                    </>
                  ) : (
                    '🔍 Analyze Quality'
                  )}
                </button>
              </>
            )}
          </div>

          {/* Right Column - Output */}
          <div className="space-y-6">
            {activeTab === 'generate' && generatedContent && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Generated Content</h3>
                <div className="bg-gray-50 rounded p-4 max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm">{generatedContent}</pre>
                </div>
              </div>
            )}

            {activeTab === 'enhance' && enhancedContent && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Enhanced Content</h3>
                <div className="bg-gray-50 rounded p-4 max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm">{enhancedContent}</pre>
                </div>
              </div>
            )}

            {activeTab === 'analyze' && analysis && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Quality Analysis</h3>
                
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-blue-600">
                      {(analysis.quality_score * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-600">Quality Score</div>
                  </div>
                  
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-purple-600">
                      {(analysis.entropy_score * 100).toFixed(1)}%
                    </div>
                    <div className="text-sm text-gray-600">Entropy Score</div>
                  </div>
                </div>

                {analysis.suggestions.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Suggestions for Improvement</h4>
                    <ul className="space-y-2">
                      {analysis.suggestions.map((suggestion: string, index: number) => (
                        <li key={index} className="flex items-start space-x-2">
                          <span className="text-yellow-500 mt-1">💡</span>
                          <span className="text-sm text-gray-600">{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="mt-4 text-sm text-gray-500">
                  {analysis.issues_found} issues found
                </div>
              </div>
            )}

            {/* Workflow Guide */}
            <div className="bg-blue-50 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-blue-900 mb-3">Workflow Guide</h3>
              <div className="space-y-2 text-sm text-blue-800">
                <div className="flex items-center space-x-2">
                  <span className={activeTab === 'generate' ? 'text-blue-600 font-medium' : ''}>
                    1. Generate: Choose template and provide context
                  </span>
                  {generatedContent && <span className="text-green-600">✓</span>}
                </div>
                <div className="flex items-center space-x-2">
                  <span className={activeTab === 'enhance' ? 'text-blue-600 font-medium' : ''}>
                    2. Enhance: Improve quality with MIAIR AI
                  </span>
                  {enhancedContent && <span className="text-green-600">✓</span>}
                </div>
                <div className="flex items-center space-x-2">
                  <span className={activeTab === 'analyze' ? 'text-blue-600 font-medium' : ''}>
                    3. Analyze: Review quality metrics and suggestions
                  </span>
                  {analysis && <span className="text-green-600">✓</span>}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}