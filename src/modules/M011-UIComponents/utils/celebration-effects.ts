/**
 * Celebration Effects - Achievement celebrations and particle systems
 * 
 * Features:
 * - Confetti explosions
 * - Fireworks animations
 * - Achievement notifications
 * - Milestone celebrations
 * - Sound effects (optional)
 * - Custom particle systems
 */

import { keyframes } from '@mui/material';

/**
 * Achievement types and milestones
 */
export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
  unlocked: boolean;
  unlockedAt?: Date;
  progress?: number;
  maxProgress?: number;
}

/**
 * Celebration configuration
 */
export interface CelebrationConfig {
  type: 'confetti' | 'fireworks' | 'stars' | 'hearts' | 'custom';
  duration: number;
  particleCount: number;
  colors?: string[];
  spread?: number;
  startVelocity?: number;
  gravity?: number;
  origin?: { x: number; y: number };
  shapes?: Array<'circle' | 'square' | 'star' | 'heart' | 'triangle'>;
  size?: number;
  sound?: boolean;
}

/**
 * Achievement definitions
 */
export const achievementDefinitions: Record<string, Omit<Achievement, 'unlocked' | 'unlockedAt'>> = {
  // Documentation achievements
  firstDoc: {
    id: 'firstDoc',
    title: 'First Steps',
    description: 'Generated your first documentation',
    icon: '📝',
    rarity: 'common',
  },
  tenDocs: {
    id: 'tenDocs',
    title: 'Documentation Pro',
    description: 'Generated 10 documents',
    icon: '📚',
    rarity: 'rare',
    maxProgress: 10,
  },
  hundredDocs: {
    id: 'hundredDocs',
    title: 'Documentation Master',
    description: 'Generated 100 documents',
    icon: '🏆',
    rarity: 'epic',
    maxProgress: 100,
  },
  
  // Quality achievements
  perfectScore: {
    id: 'perfectScore',
    title: 'Perfectionist',
    description: 'Achieved 100% quality score',
    icon: '💯',
    rarity: 'rare',
  },
  consistentQuality: {
    id: 'consistentQuality',
    title: 'Quality Guardian',
    description: 'Maintained >90% quality for 7 days',
    icon: '🛡️',
    rarity: 'epic',
    maxProgress: 7,
  },
  
  // Speed achievements
  speedDemon: {
    id: 'speedDemon',
    title: 'Speed Demon',
    description: 'Generated a document in <1 second',
    icon: '⚡',
    rarity: 'rare',
  },
  batchMaster: {
    id: 'batchMaster',
    title: 'Batch Master',
    description: 'Processed 10+ documents at once',
    icon: '🚀',
    rarity: 'epic',
  },
  
  // Time-based achievements
  earlyBird: {
    id: 'earlyBird',
    title: 'Early Bird',
    description: 'Started work before 6 AM',
    icon: '🌅',
    rarity: 'common',
  },
  nightOwl: {
    id: 'nightOwl',
    title: 'Night Owl',
    description: 'Working past midnight',
    icon: '🦉',
    rarity: 'common',
  },
  weekendWarrior: {
    id: 'weekendWarrior',
    title: 'Weekend Warrior',
    description: 'Working on the weekend',
    icon: '⚔️',
    rarity: 'rare',
  },
  
  // Streak achievements
  dailyStreak: {
    id: 'dailyStreak',
    title: 'Consistent Creator',
    description: '7-day documentation streak',
    icon: '🔥',
    rarity: 'rare',
    maxProgress: 7,
  },
  monthlyStreak: {
    id: 'monthlyStreak',
    title: 'Documentation Legend',
    description: '30-day documentation streak',
    icon: '🌟',
    rarity: 'legendary',
    maxProgress: 30,
  },
  
  // Fun achievements
  coffeeBreak: {
    id: 'coffeeBreak',
    title: 'Coffee Break',
    description: 'Took a well-deserved break',
    icon: '☕',
    rarity: 'common',
  },
  bugSquasher: {
    id: 'bugSquasher',
    title: 'Bug Squasher',
    description: 'Fixed 10 documentation issues',
    icon: '🐛',
    rarity: 'rare',
    maxProgress: 10,
  },
  explorerSpirit: {
    id: 'explorerSpirit',
    title: 'Explorer Spirit',
    description: 'Tried all documentation templates',
    icon: '🧭',
    rarity: 'epic',
  },
};

/**
 * Particle animations
 */
export const particleAnimations = {
  confettiFall: keyframes`
    0% {
      transform: translateY(-100vh) rotate(0deg);
      opacity: 1;
    }
    100% {
      transform: translateY(100vh) rotate(720deg);
      opacity: 0;
    }
  `,
  
  fireworkExplode: keyframes`
    0% {
      transform: translate(0, 0) scale(0);
      opacity: 1;
    }
    10% {
      transform: translate(var(--x), var(--y)) scale(0.5);
      opacity: 1;
    }
    100% {
      transform: translate(calc(var(--x) * 5), calc(var(--y) * 5)) scale(0);
      opacity: 0;
    }
  `,
  
  starTwinkle: keyframes`
    0%, 100% {
      transform: scale(0) rotate(0deg);
      opacity: 0;
    }
    50% {
      transform: scale(1) rotate(180deg);
      opacity: 1;
    }
  `,
  
  heartFloat: keyframes`
    0% {
      transform: translateY(0) scale(0);
      opacity: 0;
    }
    15% {
      transform: translateY(-20px) scale(1);
      opacity: 1;
    }
    100% {
      transform: translateY(-100vh) scale(0.5);
      opacity: 0;
    }
  `,
  
  spiralRise: keyframes`
    0% {
      transform: rotate(0deg) translateX(0) translateY(0) scale(0);
      opacity: 0;
    }
    10% {
      opacity: 1;
      transform: rotate(36deg) translateX(10px) translateY(-10px) scale(0.5);
    }
    100% {
      transform: rotate(720deg) translateX(100px) translateY(-100vh) scale(0);
      opacity: 0;
    }
  `,
};

/**
 * Celebration presets
 */
export const celebrationPresets: Record<string, CelebrationConfig> = {
  achievementUnlock: {
    type: 'confetti',
    duration: 3000,
    particleCount: 100,
    colors: ['#ffd700', '#ffed4e', '#fff', '#ffa500'],
    spread: 70,
    startVelocity: 30,
    gravity: 0.5,
    origin: { x: 0.5, y: 0.6 },
    sound: true,
  },
  
  documentComplete: {
    type: 'stars',
    duration: 2000,
    particleCount: 30,
    colors: ['#4caf50', '#8bc34a', '#cddc39'],
    spread: 60,
    shapes: ['star'],
    size: 1.2,
  },
  
  qualityPerfect: {
    type: 'fireworks',
    duration: 4000,
    particleCount: 50,
    colors: ['#ff0080', '#ff8c00', '#40e0d0', '#ff0080'],
    spread: 360,
    startVelocity: 45,
    gravity: 0.3,
    origin: { x: 0.5, y: 0.5 },
    sound: true,
  },
  
  milestoneReached: {
    type: 'confetti',
    duration: 5000,
    particleCount: 150,
    colors: ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3'],
    spread: 90,
    startVelocity: 35,
    gravity: 0.4,
    shapes: ['circle', 'square', 'star'],
  },
  
  dailyGoal: {
    type: 'hearts',
    duration: 2500,
    particleCount: 20,
    colors: ['#e91e63', '#f06292', '#f8bbd0'],
    spread: 50,
    shapes: ['heart'],
    size: 1.5,
  },
};

/**
 * Create particle element
 */
export const createParticle = (
  config: CelebrationConfig,
  index: number
): HTMLDivElement => {
  const particle = document.createElement('div');
  particle.className = 'celebration-particle';
  
  // Random position within spread
  const angle = (Math.random() - 0.5) * (config.spread || 70) * (Math.PI / 180);
  const velocity = config.startVelocity || 30;
  const vx = Math.cos(angle) * velocity;
  const vy = Math.sin(angle) * velocity;
  
  // Random color
  const colors = config.colors || ['#ffd700', '#ff0080', '#00ff00', '#00ffff'];
  const color = colors[Math.floor(Math.random() * colors.length)];
  
  // Random shape
  const shapes = config.shapes || ['circle'];
  const shape = shapes[Math.floor(Math.random() * shapes.length)];
  
  // Random size
  const size = (config.size || 1) * (0.5 + Math.random() * 0.5) * 10;
  
  // Random delay
  const delay = Math.random() * 0.3;
  
  // Apply styles
  particle.style.cssText = `
    position: fixed;
    pointer-events: none;
    z-index: 9999;
    width: ${size}px;
    height: ${size}px;
    background-color: ${color};
    left: ${(config.origin?.x || 0.5) * window.innerWidth}px;
    top: ${(config.origin?.y || 0.5) * window.innerHeight}px;
    --x: ${vx}px;
    --y: ${vy}px;
    animation-delay: ${delay}s;
    animation-duration: ${config.duration / 1000}s;
    animation-fill-mode: forwards;
  `;
  
  // Apply shape
  switch (shape) {
    case 'circle':
      particle.style.borderRadius = '50%';
      break;
    case 'star':
      particle.style.clipPath = 'polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)';
      break;
    case 'heart':
      particle.style.clipPath = 'path("M12,21.35l-1.45-1.32C5.4,15.36,2,12.28,2,8.5 C2,5.42,4.42,3,7.5,3c1.74,0,3.41,0.81,4.5,2.09C13.09,3.81,14.76,3,16.5,3 C19.58,3,22,5.42,22,8.5c0,3.78-3.4,6.86-8.55,11.54L12,21.35z")';
      break;
    case 'triangle':
      particle.style.clipPath = 'polygon(50% 0%, 0% 100%, 100% 100%)';
      break;
    case 'square':
    default:
      // Square is default, no special styling needed
      break;
  }
  
  // Apply animation based on type
  switch (config.type) {
    case 'confetti':
      particle.style.animation = `confettiFall ${config.duration / 1000}s ease-out forwards`;
      particle.style.animationDelay = `${delay}s`;
      break;
    case 'fireworks':
      particle.style.animation = `fireworkExplode ${config.duration / 1000}s ease-out forwards`;
      particle.style.animationDelay = `${delay}s`;
      break;
    case 'stars':
      particle.style.animation = `starTwinkle ${config.duration / 1000}s ease-in-out forwards`;
      particle.style.animationDelay = `${delay}s`;
      break;
    case 'hearts':
      particle.style.animation = `heartFloat ${config.duration / 1000}s ease-out forwards`;
      particle.style.animationDelay = `${delay}s`;
      break;
  }
  
  return particle;
};

/**
 * Trigger celebration effect
 */
export const triggerCelebration = (config: CelebrationConfig | string): void => {
  const celebrationConfig = typeof config === 'string' 
    ? celebrationPresets[config] 
    : config;
  
  if (!celebrationConfig) return;
  
  // Create container for particles
  const container = document.createElement('div');
  container.className = 'celebration-container';
  container.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 9999;
  `;
  
  // Create particles
  for (let i = 0; i < celebrationConfig.particleCount; i++) {
    const particle = createParticle(celebrationConfig, i);
    container.appendChild(particle);
  }
  
  // Add to document
  document.body.appendChild(container);
  
  // Play sound if enabled
  if (celebrationConfig.sound && 'Audio' in window) {
    // Implementation would play celebration sound
    // const audio = new Audio('/sounds/celebration.mp3');
    // audio.play().catch(() => {});
  }
  
  // Clean up after animation
  setTimeout(() => {
    container.remove();
  }, celebrationConfig.duration + 500);
};

/**
 * Achievement manager
 */
export class AchievementManager {
  private achievements: Map<string, Achievement> = new Map();
  private listeners: Array<(achievement: Achievement) => void> = [];
  
  constructor() {
    this.loadAchievements();
  }
  
  /**
   * Load achievements from storage
   */
  private loadAchievements(): void {
    const stored = localStorage.getItem('devdocai_achievements');
    if (stored) {
      const data = JSON.parse(stored);
      Object.entries(data).forEach(([id, achievement]) => {
        this.achievements.set(id, achievement as Achievement);
      });
    } else {
      // Initialize with definitions
      Object.entries(achievementDefinitions).forEach(([id, definition]) => {
        this.achievements.set(id, {
          ...definition,
          unlocked: false,
          progress: 0,
        });
      });
    }
  }
  
  /**
   * Save achievements to storage
   */
  private saveAchievements(): void {
    const data: Record<string, Achievement> = {};
    this.achievements.forEach((achievement, id) => {
      data[id] = achievement;
    });
    localStorage.setItem('devdocai_achievements', JSON.stringify(data));
  }
  
  /**
   * Unlock an achievement
   */
  unlock(achievementId: string): void {
    const achievement = this.achievements.get(achievementId);
    if (!achievement || achievement.unlocked) return;
    
    achievement.unlocked = true;
    achievement.unlockedAt = new Date();
    
    this.saveAchievements();
    this.notifyListeners(achievement);
    
    // Trigger celebration based on rarity
    const celebrationMap = {
      common: 'documentComplete',
      rare: 'achievementUnlock',
      epic: 'milestoneReached',
      legendary: 'qualityPerfect',
    };
    
    triggerCelebration(celebrationMap[achievement.rarity]);
  }
  
  /**
   * Update achievement progress
   */
  updateProgress(achievementId: string, progress: number): void {
    const achievement = this.achievements.get(achievementId);
    if (!achievement || achievement.unlocked) return;
    
    achievement.progress = progress;
    
    if (achievement.maxProgress && progress >= achievement.maxProgress) {
      this.unlock(achievementId);
    } else {
      this.saveAchievements();
    }
  }
  
  /**
   * Increment achievement progress
   */
  incrementProgress(achievementId: string, amount: number = 1): void {
    const achievement = this.achievements.get(achievementId);
    if (!achievement || achievement.unlocked) return;
    
    const currentProgress = achievement.progress || 0;
    this.updateProgress(achievementId, currentProgress + amount);
  }
  
  /**
   * Get all achievements
   */
  getAchievements(): Achievement[] {
    return Array.from(this.achievements.values());
  }
  
  /**
   * Get achievement by ID
   */
  getAchievement(id: string): Achievement | undefined {
    return this.achievements.get(id);
  }
  
  /**
   * Add listener for achievement unlocks
   */
  onUnlock(listener: (achievement: Achievement) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }
  
  /**
   * Notify listeners of unlock
   */
  private notifyListeners(achievement: Achievement): void {
    this.listeners.forEach(listener => listener(achievement));
  }
  
  /**
   * Check time-based achievements
   */
  checkTimeBasedAchievements(): void {
    const hour = new Date().getHours();
    const day = new Date().getDay();
    
    if (hour >= 5 && hour <= 6) {
      this.unlock('earlyBird');
    } else if (hour >= 0 && hour <= 4) {
      this.unlock('nightOwl');
    }
    
    if (day === 0 || day === 6) {
      this.unlock('weekendWarrior');
    }
  }
  
  /**
   * Reset all achievements (for testing)
   */
  resetAll(): void {
    this.achievements.clear();
    Object.entries(achievementDefinitions).forEach(([id, definition]) => {
      this.achievements.set(id, {
        ...definition,
        unlocked: false,
        progress: 0,
      });
    });
    this.saveAchievements();
  }
}

// Export singleton instance
export const achievementManager = new AchievementManager();

export default {
  achievementDefinitions,
  celebrationPresets,
  particleAnimations,
  triggerCelebration,
  achievementManager,
};