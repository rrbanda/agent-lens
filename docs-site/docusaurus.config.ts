import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Agent Lens',
  tagline: 'Qualify AI agents you didn\'t build — conversationally, on MLflow.',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://rrbanda.github.io',
  baseUrl: '/agent-lens/',

  organizationName: 'rrbanda',
  projectName: 'agent-lens',

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/rrbanda/agent-lens/tree/main/docs-site/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/agent-lens-social.png',
    colorMode: {
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'Agent Lens',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docsSidebar',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/docs/skills',
          label: 'Skills',
          position: 'left',
        },
        {
          to: '/docs/architecture',
          label: 'Architecture',
          position: 'left',
        },
        {
          href: 'https://github.com/rrbanda/agent-lens',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {label: 'Getting Started', to: '/docs/getting-started'},
            {label: 'Skills Reference', to: '/docs/skills'},
            {label: 'Architecture', to: '/docs/architecture'},
          ],
        },
        {
          title: 'Project',
          items: [
            {label: 'GitHub', href: 'https://github.com/rrbanda/agent-lens'},
            {label: 'Issues', href: 'https://github.com/rrbanda/agent-lens/issues'},
            {label: 'Roadmap', to: '/docs/roadmap'},
          ],
        },
        {
          title: 'Built With',
          items: [
            {label: 'MLflow', href: 'https://mlflow.org/'},
            {label: 'MLflow MCP', href: 'https://mlflow.org/docs/latest/genai/mcp/'},
            {label: 'Hermes Agent', href: 'https://github.com/hermes-ai/hermes-agent'},
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Agent Lens Contributors. Apache 2.0 License.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'yaml', 'python'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
