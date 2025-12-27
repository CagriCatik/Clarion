# GUI - Tauri + React + TypeScript

This directory contains the frontend and desktop configuration for the application.

## Project Structure

- `src/`: React components, hooks, and application logic.
- `src-tauri/`: Rust backend logic, crate configuration, and Tauri settings.
- `public/`: Static assets for the web frontend.

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) (LTS recommended)
- [Rust](https://www.rust-lang.org/)
- [Tauri Prerequisites](https://tauri.app/v1/guides/getting-started/prerequisites)

### Development

To start the development server with hot-reloading:

```bash
npm install
npm run tauri dev
```

### Build

To package the application for production:

```bash
npm run tauri build
```

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/)
- [Tauri Extension](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode)
- [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
