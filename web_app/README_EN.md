# IntelliMate

A Long-term AI Companion Application for Young People

## 📋 Project Overview

IntelliMate is a long-term AI companion application designed specifically for young people, featuring **intimate role-playing** as its core functionality. Users can engage in deep interactions with AI characters and create their own personalized IntelliMate—an AI companion that understands you, accompanies you, and grows with you.

### 🎯 Core Features

- 🤖 **AI Role-Playing** - Engage in intimate interactions with diverse AI characters
- 💬 **Intelligent Conversations** - Natural and fluent dialogue experience with deep emotional understanding
- 🎭 **Personalization** - Create and nurture your own unique IntelliMate
- 📱 **Cross-Platform Support** - Stay connected with your AI companion anytime, anywhere
- 🔒 **Privacy Protection** - Encrypted user data with comprehensive privacy safeguards

### ✨ Features

- 🚀 **React 19** - Latest version of React
- 💎 **TypeScript** - Complete type support
- 📦 **UmiJS 4** - Extensible enterprise-grade frontend application framework
- 🔧 **Biome** - Fast code linting and formatting tool
- 🎯 **Standardization** - Unified code standards and Git commit conventions
- 📱 **Responsive** - Supports both mobile and desktop

---

## 🚀 Quick Start

### Environment Requirements

- Node.js >= 20.0.0
- yarn (The project uses yarn as the package manager)

### Install Dependencies

```bash
yarn
```

### Start Development Server

```bash
npm run dev
# or
npm start
```

Visit [http://localhost:8000](http://localhost:8000) to view the application.

### Build Production Version

```bash
npm run build
```

The build artifacts will be generated in the `dist` directory.

### Code Quality Checks

```bash
# Run lint checks
npm run lint

# TypeScript type checking
npm run tsc
```

---

## 📁 Project Structure

```
intellimate/
├── src/
│   ├── components/      # Shared components
│   ├── pages/          # Page components
│   ├── layouts/        # Layout components
│   ├── constants/      # Constant definitions
│   ├── types/          # TypeScript type definitions
│   ├── utils/          # Utility functions
│   ├── styles/         # Global styles
│   ├── hooks/          # Custom Hooks
│   ├── services/       # API services
│   ├── models/         # Data models (useModel)
│   └── locales/        # Internationalization files
├── config/             # UmiJS configuration (routes, proxy, etc.)
├── docs/              # Project documentation
└── public/            # Static assets
```

---

## 🛠️ Tech Stack

- **Framework**: React 19 + UmiJS 4
- **Language**: TypeScript 5.6+
- **UI Implementation**: Native HTML + Less (No UI component library)
- **Icon Library**: lucide-react
- **Styling**: Less
- **State Management**: UmiJS useModel
- **SDK**: Inty TypeScript SDK (Custom AI chat SDK)
- **Code Quality**: Biome
- **Git Hooks**: Husky + Commitlint
- **Package Manager**: Yarn

---

## 📖 Development Guide

### Code Standards

The project follows unified code standards.

**Core Standards:**
- All interface names start with capital `I` (e.g., `IUserInfo`)
- Prohibited use of `any` type
- Use `@/` alias for importing project modules
- Constants are managed uniformly in `src/constants/`
- Style variables are defined uniformly in `src/styles/variables.less`

### Git Commit Standards

The project uses [Conventional Commits](https://www.conventionalcommits.org/) standard:

```bash
# New feature
git commit -m "feat: add user login functionality"

# Bug fix
git commit -m "fix: resolve navigation bar styling issue"

# Documentation update
git commit -m "docs: update README documentation"

# Refactoring
git commit -m "refactor: restructure user module code"
```

### Styling Development

The project has unified style management using Less variables:

```less
// Import variables in component style files
@import '@/styles/variables.less';

.my-component {
  color: @primary-color;        // Use theme color
  padding: @spacing-lg;         // Use spacing variable
  font-size: @font-size-base;   // Use font size variable
}
```

Available style variables can be found in `src/styles/variables.less`.

---

## 📚 Documentation

- [Inty SDK Documentation](./docs/README.md) - Inty TypeScript SDK usage guide
- [API Documentation](./docs/api/) - API interface documentation


## 📄 License

[MIT](./LICENSE)

---

## 🙏 Acknowledgments

- [UmiJS](https://umijs.org/)
- [React](https://react.dev/)

---

**Start your development journey!** 🎉