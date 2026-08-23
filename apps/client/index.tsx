import React from 'react';
import { registerRootComponent } from 'expo';
import App from './src/App';
import { ProjectCompatibilityGate } from './src/components/ProjectCompatibilityGate';

function Root() {
  return (
    <ProjectCompatibilityGate>
      <App />
    </ProjectCompatibilityGate>
  );
}

registerRootComponent(Root);
