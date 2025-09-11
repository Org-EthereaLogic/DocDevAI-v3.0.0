/**
 * Loading Components for DevDocAI Frontend
 */

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  color?: string
}

export function LoadingSpinner({ size = 'md', color = 'blue-500' }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  }

  return (
    <div className={`animate-spin rounded-full border-2 border-gray-200 border-t-${color} ${sizeClasses[size]}`} />
  )
}

interface LoadingDotsProps {
  text?: string
}

export function LoadingDots({ text = 'Loading' }: LoadingDotsProps) {
  return (
    <div className="flex items-center space-x-1">
      <span className="text-gray-600">{text}</span>
      <div className="flex space-x-1">
        <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse"></div>
        <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
        <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
      </div>
    </div>
  )
}

interface LoadingSkeletonProps {
  lines?: number
  className?: string
}

export function LoadingSkeleton({ lines = 3, className = '' }: LoadingSkeletonProps) {
  return (
    <div className={`animate-pulse ${className}`}>
      {Array.from({ length: lines }, (_, i) => (
        <div key={i} className="h-4 bg-gray-200 rounded mb-2 last:mb-0"
             style={{ width: `${Math.random() * 40 + 60}%` }} />
      ))}
    </div>
  )
}

interface FullPageLoadingProps {
  message?: string
}

export function FullPageLoading({ message = 'Loading DevDocAI...' }: FullPageLoadingProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center mb-4 mx-auto">
          <span className="text-white font-bold text-xl">AI</span>
        </div>
        <LoadingSpinner size="lg" />
        <p className="text-gray-600 mt-4">{message}</p>
      </div>
    </div>
  )
}
