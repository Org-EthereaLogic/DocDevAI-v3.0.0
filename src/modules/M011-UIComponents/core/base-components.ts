/**
 * M011 Base Components - Foundation classes for all UI components
 * 
 * Provides base implementations that ensure consistent behavior across
 * all DevDocAI UI components with privacy-first and accessibility features.
 */

import { 
  IUIComponent, 
  ComponentType, 
  ComponentState, 
  ComponentData,
  AccessibilityConfig,
  UITheme
} from './interfaces';

/**
 * Abstract base class for all UI components
 */
export abstract class BaseUIComponent implements IUIComponent {
  public readonly id: string;
  public readonly type: ComponentType;
  protected _state: ComponentState = ComponentState.INITIALIZING;
  protected _accessibility: AccessibilityConfig;
  protected _theme?: UITheme;
  protected _destroyed = false;

  constructor(
    id: string,
    type: ComponentType,
    accessibility: AccessibilityConfig,
    theme?: UITheme
  ) {
    this.id = id;
    this.type = type;
    this._accessibility = accessibility;
    this._theme = theme;
    
    this.initialize();
  }

  public get state(): ComponentState {
    return this._state;
  }

  public get accessibility(): AccessibilityConfig {
    return { ...this._accessibility };
  }

  public get theme(): UITheme | undefined {
    return this._theme;
  }

  /**
   * Initialize component - called during construction
   */
  protected initialize(): void {
    this.setState(ComponentState.READY);
    this.setupAccessibility();
  }

  /**
   * Set component state and trigger state change events
   */
  protected setState(newState: ComponentState): void {
    if (this._destroyed) return;
    
    const previousState = this._state;
    this._state = newState;
    
    this.onStateChange(previousState, newState);
  }

  /**
   * Handle state changes - override in derived classes
   */
  protected onStateChange(previous: ComponentState, current: ComponentState): void {
    // Base implementation - can be overridden
  }

  /**
   * Setup accessibility features
   */
  protected setupAccessibility(): void {
    if (this._accessibility.keyboardNavigable) {
      this.setupKeyboardHandlers();
    }
    
    if (this._accessibility.screenReaderSupport) {
      this.setupScreenReaderSupport();
    }
    
    if (this._accessibility.highContrastSupport) {
      this.setupHighContrastSupport();
    }
  }

  /**
   * Setup keyboard event handlers
   */
  protected setupKeyboardHandlers(): void {
    // Base implementation - override in derived classes
  }

  /**
   * Setup screen reader support
   */
  protected setupScreenReaderSupport(): void {
    // Base implementation - override in derived classes
  }

  /**
   * Setup high contrast mode support
   */
  protected setupHighContrastSupport(): void {
    // Base implementation - override in derived classes
  }

  /**
   * Validate component data
   */
  protected validateData(data: ComponentData): boolean {
    return data !== null && data !== undefined;
  }

  /**
   * Handle errors consistently
   */
  protected handleError(error: Error): void {
    console.error(`[${this.type}:${this.id}] Error:`, error);
    this.setState(ComponentState.ERROR);
  }

  /**
   * Abstract render method - must be implemented by derived classes
   */
  public abstract render(): Promise<void>;

  /**
   * Update component with new data
   */
  public async update(data: ComponentData): Promise<void> {
    if (this._destroyed) {
      throw new Error('Cannot update destroyed component');
    }

    if (!this.validateData(data)) {
      throw new Error('Invalid component data provided');
    }

    try {
      this.setState(ComponentState.LOADING);
      await this.performUpdate(data);
      this.setState(ComponentState.READY);
    } catch (error) {
      this.handleError(error as Error);
      throw error;
    }
  }

  /**
   * Perform the actual update - override in derived classes
   */
  protected abstract performUpdate(data: ComponentData): Promise<void>;

  /**
   * Destroy component and clean up resources
   */
  public async destroy(): Promise<void> {
    if (this._destroyed) return;

    try {
      await this.cleanup();
      this._destroyed = true;
      this.setState(ComponentState.DESTROYED);
    } catch (error) {
      console.error(`[${this.type}:${this.id}] Error during cleanup:`, error);
    }
  }

  /**
   * Cleanup resources - override in derived classes
   */
  protected async cleanup(): Promise<void> {
    // Base implementation - override in derived classes
  }
}

/**
 * Base React component wrapper for integration
 */
export abstract class BaseReactComponent extends BaseUIComponent {
  protected containerElement?: HTMLElement;

  /**
   * Set the container element for React rendering
   */
  public setContainer(element: HTMLElement): void {
    this.containerElement = element;
  }

  /**
   * Get container element or throw if not set
   */
  protected getContainer(): HTMLElement {
    if (!this.containerElement) {
      throw new Error('Container element not set for React component');
    }
    return this.containerElement;
  }

  protected async cleanup(): Promise<void> {
    if (this.containerElement) {
      // Clean up React component if mounted
      const reactRoot = (this.containerElement as any)._reactInternalFiber;
      if (reactRoot) {
        // Note: This would require React root cleanup in actual implementation
      }
    }
    
    await super.cleanup();
  }
}

/**
 * Base VS Code webview component
 */
export abstract class BaseVSCodeComponent extends BaseUIComponent {
  protected webviewPanel?: any; // VS Code webview panel

  /**
   * Set the VS Code webview panel
   */
  public setWebviewPanel(panel: any): void {
    this.webviewPanel = panel;
    this.setupWebviewHandlers();
  }

  /**
   * Setup webview message handlers
   */
  protected setupWebviewHandlers(): void {
    if (!this.webviewPanel) return;

    this.webviewPanel.webview.onDidReceiveMessage(
      (message: any) => this.handleWebviewMessage(message)
    );
  }

  /**
   * Handle messages from webview
   */
  protected abstract handleWebviewMessage(message: any): Promise<void>;

  /**
   * Send message to webview
   */
  protected sendToWebview(message: any): void {
    if (this.webviewPanel) {
      this.webviewPanel.webview.postMessage(message);
    }
  }

  protected async cleanup(): Promise<void> {
    if (this.webviewPanel) {
      this.webviewPanel.dispose();
      this.webviewPanel = undefined;
    }
    
    await super.cleanup();
  }
}

/**
 * Factory for creating UI components
 */
export class ComponentFactory {
  private static componentRegistry = new Map<string, any>();

  /**
   * Register a component class
   */
  static registerComponent(type: ComponentType, componentClass: any): void {
    this.componentRegistry.set(type, componentClass);
  }

  /**
   * Create a component instance
   */
  static createComponent<T extends IUIComponent>(
    type: ComponentType,
    id: string,
    accessibility: AccessibilityConfig,
    theme?: UITheme
  ): T {
    const ComponentClass = this.componentRegistry.get(type);
    
    if (!ComponentClass) {
      throw new Error(`Component type '${type}' not registered`);
    }

    return new ComponentClass(id, type, accessibility, theme) as T;
  }

  /**
   * Get all registered component types
   */
  static getRegisteredTypes(): ComponentType[] {
    return Array.from(this.componentRegistry.keys()) as ComponentType[];
  }
}

/**
 * Component lifecycle manager
 */
export class ComponentLifecycleManager {
  private components = new Map<string, IUIComponent>();

  /**
   * Register a component with the lifecycle manager
   */
  registerComponent(component: IUIComponent): void {
    this.components.set(component.id, component);
  }

  /**
   * Get a component by ID
   */
  getComponent(id: string): IUIComponent | undefined {
    return this.components.get(id);
  }

  /**
   * Get all components of a specific type
   */
  getComponentsByType(type: ComponentType): IUIComponent[] {
    return Array.from(this.components.values())
      .filter(component => component.type === type);
  }

  /**
   * Update multiple components with the same data
   */
  async updateComponents(ids: string[], data: ComponentData): Promise<void> {
    const updatePromises = ids
      .map(id => this.components.get(id))
      .filter(component => component !== undefined)
      .map(component => component!.update(data));

    await Promise.allSettled(updatePromises);
  }

  /**
   * Destroy a component
   */
  async destroyComponent(id: string): Promise<void> {
    const component = this.components.get(id);
    if (component) {
      await component.destroy();
      this.components.delete(id);
    }
  }

  /**
   * Destroy all components
   */
  async destroyAll(): Promise<void> {
    const destroyPromises = Array.from(this.components.values())
      .map(component => component.destroy());

    await Promise.allSettled(destroyPromises);
    this.components.clear();
  }

  /**
   * Get component health status
   */
  getHealthStatus(): { healthy: number; error: number; total: number } {
    const components = Array.from(this.components.values());
    const healthy = components.filter(c => c.state === ComponentState.READY).length;
    const error = components.filter(c => c.state === ComponentState.ERROR).length;
    
    return {
      healthy,
      error,
      total: components.length
    };
  }
}

/**
 * Default accessibility configuration
 */
export const DEFAULT_ACCESSIBILITY_CONFIG: AccessibilityConfig = {
  keyboardNavigable: true,
  screenReaderSupport: true,
  highContrastSupport: true,
  focusManagement: {
    focusable: true,
    tabIndex: 0
  }
};