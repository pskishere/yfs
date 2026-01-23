import { registry } from '../../framework/core/registry';
import { ExampleView } from './components/ExampleView';
import { SmileOutlined } from '@ant-design/icons';

export const ExampleModule = {
  init: () => {
    // Register the main view
    registry.registerComponent('example', ExampleView, {
      title: 'Example',
      icon: <SmileOutlined />
    });

    // Register suggestions
    const suggestions = [
      { label: 'Generate Random Number', value: 'Generate a random number between 1 and 100' },
      { label: 'Check System Status', value: 'Check current system status' },
    ];

    suggestions.forEach(s => registry.registerSuggestion(s));
  }
};
