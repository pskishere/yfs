import React from 'react';

export interface SuggestionItem {
  label: string;
  value: string;
}

export type BusinessComponent = React.ComponentType<any>;

export interface ModuleMetadata {
  title?: string;
  icon?: React.ReactNode;
}

export interface ModuleDefinition {
  init: () => void;
}
