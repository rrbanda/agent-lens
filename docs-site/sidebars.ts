import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  docsSidebar: [
    'intro',
    'getting-started',
    'skills',
    'architecture',
    'roadmap',
    {
      type: 'category',
      label: 'ADRs',
      items: ['adr/loggedmodel-gap'],
    },
  ],
};

export default sidebars;
