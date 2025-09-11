'use client'

import { useState, useEffect } from 'react'
import { generateDocument } from '@/lib/api'

export default function Home() {
  const [generatedDoc, setGeneratedDoc] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [hoveredFeature, setHoveredFeature] = useState<number | null>(null)

  const handleGenerate = async () => {
    setIsGenerating(true)
    try {
      const result = await generateDocument({
        template: 'readme',
        context: {
          title: 'Sample Project',
          description: 'A demonstration of DevDocAI capabilities'
        }
      })
      setGeneratedDoc(result.content)
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 3000)
    } catch (error) {
      console.error('Generation failed:', error)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="w-full min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-sm border-b animate-slideInUp">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <img
                src="/devdocai-logo.png"
                alt="DevDocAI"
                className="h-16 w-auto hover-scale transition-transform duration-300"
              />
              <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-medium rounded-full animate-pulse">
                v3.0.0
              </span>
            </div>
            <nav className="hidden md:flex space-x-6">
              <a href="#features" className="text-gray-600 hover:text-gray-900 transition-colors duration-200 hover:scale-105 inline-block">Features</a>
              <a href="/studio" className="text-gray-600 hover:text-gray-900 transition-colors duration-200 hover:scale-105 inline-block">Studio</a>
              <a href="/settings" className="text-gray-600 hover:text-gray-900 transition-colors duration-200 hover:scale-105 inline-block">Settings</a>
              <a href="#docs" className="text-gray-600 hover:text-gray-900 transition-colors duration-200 hover:scale-105 inline-block">Documentation</a>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 animate-fadeIn">
        <div className="text-center">
          <h2 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">
            AI-Powered
            <span className="bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent gradient-animated"> Documentation</span>
          </h2>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Generate professional documentation in seconds with our advanced AI engine.
            Perfect for solo developers who want enterprise-quality docs without the complexity.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-8 py-3 rounded-lg font-medium text-lg hover:from-blue-600 hover:to-purple-600 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 button-press hover-lift relative overflow-hidden group"
            >
              <span className="absolute inset-0 bg-white opacity-0 group-hover:opacity-20 transition-opacity duration-300"></span>
              <span className="relative z-10">{isGenerating ? (
                <span className="flex items-center justify-center">
                  <span className="animate-bounce mr-2">✨</span>
                  <span>Generating<span className="loading-dots"></span></span>
                </span>
              ) : (
                <span className="flex items-center justify-center group">
                  <span className="group-hover:animate-wiggle mr-2">🚀</span>
                  <span>Try Demo</span>
                </span>
              )}</span>
            </button>
            <a
              href="/studio"
              className="border border-blue-500 text-blue-600 px-8 py-3 rounded-lg font-medium text-lg hover:bg-blue-50 transition-all duration-200 hover-scale button-press group relative overflow-hidden"
            >
              <span className="absolute inset-0 bg-blue-500 opacity-0 group-hover:opacity-5 transition-opacity duration-300"></span>
              <span className="relative z-10 flex items-center justify-center">
                Document Studio <span className="ml-2 group-hover:translate-x-1 transition-transform duration-200">→</span>
              </span>
            </a>
          </div>

          {/* Demo Output */}
          {generatedDoc && (
            <div className={`max-w-4xl mx-auto bg-white rounded-lg shadow-lg p-6 text-left animate-fadeInScale ${showSuccess ? 'success-animation' : ''}`}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Generated Documentation</h3>
                <span className="text-sm text-gray-500 flex items-center">
                  <span className="inline-block w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                  Generated in seconds
                </span>
              </div>
              <pre className="bg-gray-50 p-4 rounded text-sm overflow-x-auto whitespace-pre-wrap">
                {generatedDoc}
              </pre>
            </div>
          )}
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h3 className="text-3xl font-bold text-gray-900 mb-4">Enterprise Features, Solo Developer Simplicity</h3>
          <p className="text-gray-600 max-w-2xl mx-auto">
            DevDocAI combines cutting-edge AI with thoughtful design to deliver professional results without complexity.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8 stagger-animation">
          <div 
            className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-300 card-hover group"
            onMouseEnter={() => setHoveredFeature(0)}
            onMouseLeave={() => setHoveredFeature(null)}
          >
            <div className={`w-12 h-12 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mb-4 transition-transform duration-300 ${hoveredFeature === 0 ? 'animate-bounce' : ''}`}>
              ⚡
            </div>
            <h4 className="text-xl font-semibold text-gray-900 mb-2">MIAIR Engine</h4>
            <p className="text-gray-600">
              Advanced Shannon entropy optimization for 60-75% quality improvement. Process 412K docs/minute.
            </p>
          </div>

          <div 
            className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-300 card-hover group"
            onMouseEnter={() => setHoveredFeature(1)}
            onMouseLeave={() => setHoveredFeature(null)}
          >
            <div className={`w-12 h-12 bg-purple-100 text-purple-600 rounded-lg flex items-center justify-center mb-4 transition-transform duration-300 ${hoveredFeature === 1 ? 'animate-bounce' : ''}`}>
              🤖
            </div>
            <h4 className="text-xl font-semibold text-gray-900 mb-2">Multi-LLM Support</h4>
            <p className="text-gray-600">
              OpenAI, Anthropic, Google, and local models. Smart routing with cost management.
            </p>
          </div>

          <div 
            className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-300 card-hover group"
            onMouseEnter={() => setHoveredFeature(2)}
            onMouseLeave={() => setHoveredFeature(null)}
          >
            <div className={`w-12 h-12 bg-green-100 text-green-600 rounded-lg flex items-center justify-center mb-4 transition-transform duration-300 ${hoveredFeature === 2 ? 'animate-bounce' : ''}`}>
              🛡️
            </div>
            <h4 className="text-xl font-semibold text-gray-900 mb-2">Privacy First</h4>
            <p className="text-gray-600">
              Local-only processing, encrypted storage, no telemetry by default. Your data stays yours.
            </p>
          </div>

          <div 
            className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-300 card-hover group"
            onMouseEnter={() => setHoveredFeature(3)}
            onMouseLeave={() => setHoveredFeature(null)}
          >
            <div className={`w-12 h-12 bg-yellow-100 text-yellow-600 rounded-lg flex items-center justify-center mb-4 transition-transform duration-300 ${hoveredFeature === 3 ? 'animate-bounce' : ''}`}>
              📦
            </div>
            <h4 className="text-xl font-semibold text-gray-900 mb-2">Template Marketplace</h4>
            <p className="text-gray-600">
              Community-driven templates with Ed25519 signatures. 15-20x performance improvements.
            </p>
          </div>

          <div 
            className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-300 card-hover group"
            onMouseEnter={() => setHoveredFeature(4)}
            onMouseLeave={() => setHoveredFeature(null)}
          >
            <div className={`w-12 h-12 bg-red-100 text-red-600 rounded-lg flex items-center justify-center mb-4 transition-transform duration-300 ${hoveredFeature === 4 ? 'animate-bounce' : ''}`}>
              📊
            </div>
            <h4 className="text-xl font-semibold text-gray-900 mb-2">Batch Operations</h4>
            <p className="text-gray-600">
              Process 11,995 docs/second with 9.75x performance improvement. Enterprise-scale efficiency.
            </p>
          </div>

          <div 
            className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-all duration-300 card-hover group"
            onMouseEnter={() => setHoveredFeature(5)}
            onMouseLeave={() => setHoveredFeature(null)}
          >
            <div className={`w-12 h-12 bg-indigo-100 text-indigo-600 rounded-lg flex items-center justify-center mb-4 transition-transform duration-300 ${hoveredFeature === 5 ? 'animate-bounce' : ''}`}>
              🔧
            </div>
            <h4 className="text-xl font-semibold text-gray-900 mb-2">Version Control</h4>
            <p className="text-gray-600">
              Git integration with impact analysis. Track changes across your entire documentation suite.
            </p>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="bg-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h3 className="text-3xl font-bold text-gray-900 mb-4">Performance That Scales</h3>
          </div>

          <div className="grid md:grid-cols-4 gap-8 text-center stagger-animation">
            <div className="group hover:scale-105 transition-transform duration-300">
              <div className="text-4xl font-bold text-blue-600 mb-2 hover-scale">412K</div>
              <div className="text-gray-600">Docs/minute processed</div>
            </div>
            <div className="group hover:scale-105 transition-transform duration-300">
              <div className="text-4xl font-bold text-purple-600 mb-2 hover-scale">95%</div>
              <div className="text-gray-600">Security coverage</div>
            </div>
            <div className="group hover:scale-105 transition-transform duration-300">
              <div className="text-4xl font-bold text-green-600 mb-2 hover-scale">13</div>
              <div className="text-gray-600">AI modules complete</div>
            </div>
            <div className="group hover:scale-105 transition-transform duration-300">
              <div className="text-4xl font-bold text-yellow-600 mb-2 hover-scale">100%</div>
              <div className="text-gray-600">Production ready</div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gradient-to-r from-blue-500 to-purple-500 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h3 className="text-3xl font-bold text-white mb-4">Ready to Transform Your Documentation?</h3>
          <p className="text-blue-100 text-xl mb-8 max-w-2xl mx-auto">
            Install DevDocAI in seconds and start generating professional documentation powered by AI.
          </p>

          <div className="bg-gray-900 text-green-400 p-4 rounded-lg inline-block font-mono text-left mb-8 hover:shadow-2xl transition-shadow duration-300 group">
            <div className="group-hover:text-green-300 transition-colors">$ pip install devdocai</div>
            <div className="group-hover:text-green-300 transition-colors">$ devdocai --help</div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0"
              className="bg-white text-blue-600 px-8 py-3 rounded-lg font-medium text-lg hover:bg-gray-50 transition-all duration-200 hover-lift button-press"
            >
              View on GitHub
            </a>
            <a
              href="/docs"
              className="border border-white text-white px-8 py-3 rounded-lg font-medium text-lg hover:bg-white hover:text-blue-600 transition-all duration-200 hover-lift button-press"
            >
              Documentation
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-300 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <img
                  src="/devdocai-logo.png"
                  alt="DevDocAI"
                  className="h-12 w-auto hover-scale transition-transform duration-300"
                />
              </div>
              <p className="text-sm">
                AI-powered documentation generation for modern developers.
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-3">Product</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#features" className="hover:text-white transition-colors duration-200">Features</a></li>
                <li><a href="#templates" className="hover:text-white transition-colors duration-200">Templates</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors duration-200">Pricing</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-3">Developers</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/docs" className="hover:text-white transition-colors duration-200">Documentation</a></li>
                <li><a href="/api" className="hover:text-white transition-colors duration-200">API Reference</a></li>
                <li><a href="https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0" className="hover:text-white transition-colors duration-200">GitHub</a></li>
              </ul>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-3">Company</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="/about" className="hover:text-white transition-colors duration-200">About</a></li>
                <li><a href="/contact" className="hover:text-white transition-colors duration-200">Contact</a></li>
                <li><a href="/privacy" className="hover:text-white transition-colors duration-200">Privacy</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm">
            <p>&copy; 2025 DevDocAI. All rights reserved. Built with <span className="animate-pulse">❤️</span> for developers.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
