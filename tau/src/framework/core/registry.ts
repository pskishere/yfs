import { BusinessComponent, SuggestionItem, ModuleMetadata } from './types';

interface ComponentEntry {
  component: BusinessComponent;
  metadata?: ModuleMetadata;
}

class AppRegistry {
  private components = new Map<string, ComponentEntry>();
  private suggestions: SuggestionItem[] = [];

  /**
   * Register a business component by key
   * @param key The unique key for the component (case-insensitive)
   * @param component The React component
   * @param metadata Optional metadata (title, icon)
   */
  registerComponent(key: string, component: BusinessComponent, metadata?: ModuleMetadata) {
    this.components.set(key.toLowerCase(), { component, metadata });
  }

  /**
   * Get a registered component by key
   * @param key The key to look up
   */
  getComponent(key: string): BusinessComponent | undefined {
    return this.components.get(key.toLowerCase())?.component;
  }

  /**
   * Get metadata for a component
   * @param key The key to look up
   */
  getMetadata(key: string): ModuleMetadata | undefined {
    return this.components.get(key.toLowerCase())?.metadata;
  }

  /**
   * Register a suggestion item for the chat interface
   * @param suggestion The suggestion item
   */
  registerSuggestion(suggestion: SuggestionItem) {
    // Avoid duplicates
    if (!this.suggestions.some(s => s.value === suggestion.value)) {
      this.suggestions.push(suggestion);
    }
  }

  /**
   * Get all registered suggestions
   */
  getSuggestions(): SuggestionItem[] {
    return [...this.suggestions];
  }
}

export const registry = new AppRegistry();
