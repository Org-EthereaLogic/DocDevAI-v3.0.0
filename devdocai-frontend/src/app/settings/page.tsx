'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

interface ApiConfig {
  openai_api_key?: string
  anthropic_api_key?: string
  google_api_key?: string
  privacy_mode?: string
  telemetry_enabled?: boolean
}

export default function Settings() {
  const [config, setConfig] = useState<ApiConfig>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [showKeys, setShowKeys] = useState({
    openai: false,
    anthropic: false,
    google: false
  })

  // Load current configuration
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/config')
        if (response.ok) {
          const data = await response.json()
          setConfig(data)
        }
      } catch (error) {
        console.error('Failed to load config:', error)
      } finally {
        setLoading(false)
      }
    }
    loadConfig()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    
    try {
      const response = await fetch('http://localhost:8000/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      })
      
      if (response.ok) {
        setMessage('✅ Settings saved successfully! API integration is now active.')
      } else {
        setMessage('❌ Failed to save settings. Please try again.')
      }
    } catch (error) {
      setMessage('❌ Error saving settings. Please check your connection.')
    } finally {
      setSaving(false)
    }
  }

  const handleInputChange = (field: keyof ApiConfig, value: string | boolean) => {
    setConfig(prev => ({ ...prev, [field]: value }))
  }

  const toggleKeyVisibility = (provider: 'openai' | 'anthropic' | 'google') => {
    setShowKeys(prev => ({ ...prev, [provider]: !prev[provider] }))
  }

  const maskKey = (key: string | undefined, visible: boolean) => {
    if (!key || key === 'your_key_here') return ''
    if (visible) return key
    return key.length > 8 ? `${key.substring(0, 4)}${'*'.repeat(key.length - 8)}${key.substring(key.length - 4)}` : '*'.repeat(key.length)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="text-gray-600">Loading settings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <img 
                src="/devdocai-logo.png" 
                alt="DevDocAI" 
                className="h-12 w-auto"
              />
              <h1 className="text-xl font-bold text-gray-900">Settings</h1>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/studio"
                className="text-gray-600 hover:text-gray-900 font-medium"
              >
                Document Studio
              </Link>
              <Link
                href="/"
                className="text-gray-600 hover:text-gray-900 font-medium"
              >
                Home
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-2xl font-bold text-gray-900">AI Provider Configuration</h2>
            <p className="mt-2 text-gray-600">
              Configure your AI provider API keys to enable real AI-powered documentation generation.
              Without these keys, DevDocAI will run in demo mode with sample content.
            </p>
          </div>

          <div className="p-6 space-y-6">
            {/* OpenAI Configuration */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    OpenAI API Key
                  </label>
                  <p className="text-xs text-gray-500 mt-1">
                    Used for GPT-4 and ChatGPT integration. Get your key from{' '}
                    <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" 
                       className="text-blue-600 hover:text-blue-500">
                      OpenAI Platform
                    </a>
                  </p>
                </div>
                <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                  Primary (40%)
                </span>
              </div>
              <div className="flex space-x-2">
                <input
                  type={showKeys.openai ? 'text' : 'password'}
                  value={config.openai_api_key || ''}
                  onChange={(e) => handleInputChange('openai_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button
                  type="button"
                  onClick={() => toggleKeyVisibility('openai')}
                  className="px-3 py-2 border border-gray-300 rounded-md text-gray-600 hover:text-gray-800"
                >
                  {showKeys.openai ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            {/* Anthropic Configuration */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Anthropic API Key
                  </label>
                  <p className="text-xs text-gray-500 mt-1">
                    Used for Claude integration. Get your key from{' '}
                    <a href="https://console.anthropic.com/" target="_blank" rel="noopener noreferrer"
                       className="text-blue-600 hover:text-blue-500">
                      Anthropic Console
                    </a>
                  </p>
                </div>
                <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                  Secondary (35%)
                </span>
              </div>
              <div className="flex space-x-2">
                <input
                  type={showKeys.anthropic ? 'text' : 'password'}
                  value={config.anthropic_api_key || ''}
                  onChange={(e) => handleInputChange('anthropic_api_key', e.target.value)}
                  placeholder="sk-ant-..."
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
                />
                <button
                  type="button"
                  onClick={() => toggleKeyVisibility('anthropic')}
                  className="px-3 py-2 border border-gray-300 rounded-md text-gray-600 hover:text-gray-800"
                >
                  {showKeys.anthropic ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            {/* Google Configuration */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Google AI API Key
                  </label>
                  <p className="text-xs text-gray-500 mt-1">
                    Used for Gemini integration. Get your key from{' '}
                    <a href="https://makersuite.google.com/app/apikey" target="_blank" rel="noopener noreferrer"
                       className="text-blue-600 hover:text-blue-500">
                      Google AI Studio
                    </a>
                  </p>
                </div>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                  Fallback (25%)
                </span>
              </div>
              <div className="flex space-x-2">
                <input
                  type={showKeys.google ? 'text' : 'password'}
                  value={config.google_api_key || ''}
                  onChange={(e) => handleInputChange('google_api_key', e.target.value)}
                  placeholder="AIza..."
                  className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
                <button
                  type="button"
                  onClick={() => toggleKeyVisibility('google')}
                  className="px-3 py-2 border border-gray-300 rounded-md text-gray-600 hover:text-gray-800"
                >
                  {showKeys.google ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            {/* Privacy Settings */}
            <div className="pt-6 border-t border-gray-200">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Privacy & Security</h3>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Privacy Mode
                    </label>
                    <p className="text-xs text-gray-500 mt-1">
                      Controls data handling and processing location
                    </p>
                  </div>
                  <select
                    value={config.privacy_mode || 'LOCAL_ONLY'}
                    onChange={(e) => handleInputChange('privacy_mode', e.target.value)}
                    className="border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="LOCAL_ONLY">Local Only</option>
                    <option value="HYBRID">Hybrid</option>
                    <option value="CLOUD_OPTIMIZED">Cloud Optimized</option>
                  </select>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Telemetry
                    </label>
                    <p className="text-xs text-gray-500 mt-1">
                      Help improve DevDocAI by sharing anonymous usage data
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={config.telemetry_enabled || false}
                      onChange={(e) => handleInputChange('telemetry_enabled', e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="pt-6 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-500">
                  <p>🔒 API keys are stored securely using AES-256-GCM encryption</p>
                  <p>🏠 All data processing happens locally on your machine</p>
                </div>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-6 py-2 rounded-lg font-medium hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {saving ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Saving...
                    </>
                  ) : (
                    <>
                      💾 Save Settings
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Status Message */}
            {message && (
              <div className={`p-4 rounded-lg ${
                message.includes('✅') 
                  ? 'bg-green-50 border border-green-200' 
                  : 'bg-red-50 border border-red-200'
              }`}>
                <p className={`text-sm ${
                  message.includes('✅') ? 'text-green-700' : 'text-red-700'
                }`}>
                  {message}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Start Guide */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-medium text-blue-900 mb-3">🚀 Quick Start Guide</h3>
          <div className="space-y-2 text-sm text-blue-800">
            <p>1. <strong>Get API Keys:</strong> Visit the provider links above to create free accounts and generate API keys</p>
            <p>2. <strong>Add Keys:</strong> Paste your API keys in the fields above (at least one provider required)</p>
            <p>3. <strong>Save Settings:</strong> Click "Save Settings" to activate AI-powered generation</p>
            <p>4. <strong>Generate Docs:</strong> Go to <Link href="/studio" className="underline hover:text-blue-600">Document Studio</Link> and start creating amazing documentation!</p>
          </div>
        </div>
      </div>
    </div>
  )
}