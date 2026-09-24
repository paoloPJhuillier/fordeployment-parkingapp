# Technology Stack Reference
**Project:** Cebuana Lhuillier Parking Reservation System  
**Version:** 2.1  
**Date:** March 2026

---

## 1. Overview

This document provides the complete technology stack with exact versions used in the Parking Reservation System.

---

## 2. Frontend Technologies

### 2.1 Core Framework

| Technology | Version | Purpose |
|------------|---------|---------|
| React | `19.0.0` | SPA framework |
| React DOM | `19.0.0` | DOM rendering |
| React Scripts | `5.0.1` | Create React App |
| @craco/craco | `7.1.0` | CRA configuration override |
| Node.js | `20.20.0` | JavaScript runtime |
| Yarn | `1.22.22` | Package manager |

### 2.2 UI Components (shadcn/ui + Radix)

| Component | Version | Purpose |
|-----------|---------|---------|
| @radix-ui/react-accordion | `1.2.8` | Accordions |
| @radix-ui/react-alert-dialog | `1.1.11` | Alert dialogs |
| @radix-ui/react-aspect-ratio | `1.1.4` | Aspect ratio containers |
| @radix-ui/react-avatar | `1.1.7` | User avatars |
| @radix-ui/react-checkbox | `1.2.3` | Checkbox inputs |
| @radix-ui/react-collapsible | `1.1.8` | Collapsible sections |
| @radix-ui/react-context-menu | `2.2.12` | Context menus |
| @radix-ui/react-dialog | `1.1.11` | Modal dialogs |
| @radix-ui/react-dropdown-menu | `2.1.12` | Dropdown menus |
| @radix-ui/react-hover-card | `1.1.11` | Hover cards |
| @radix-ui/react-label | `2.1.4` | Form labels |
| @radix-ui/react-menubar | `1.1.12` | Menu bars |
| @radix-ui/react-navigation-menu | `1.2.10` | Navigation menus |
| @radix-ui/react-popover | `1.1.11` | Popovers |
| @radix-ui/react-progress | `1.1.4` | Progress bars |
| @radix-ui/react-radio-group | `1.3.4` | Radio buttons |
| @radix-ui/react-scroll-area | `1.2.6` | Scrollable areas |
| @radix-ui/react-select | `2.2.2` | Select inputs |
| @radix-ui/react-separator | `1.1.4` | Visual separators |
| @radix-ui/react-slider | `1.3.2` | Range sliders |
| @radix-ui/react-slot | `1.2.0` | Slot composition |
| @radix-ui/react-switch | `1.2.2` | Toggle switches |
| @radix-ui/react-tabs | `1.1.9` | Tab navigation |
| @radix-ui/react-toast | `1.2.11` | Toast notifications |
| @radix-ui/react-toggle | `1.1.6` | Toggle buttons |
| @radix-ui/react-toggle-group | `1.1.7` | Toggle groups |
| @radix-ui/react-tooltip | `1.2.4` | Tooltips |

### 2.3 Styling

| Technology | Version | Purpose |
|------------|---------|---------|
| TailwindCSS | `3.4.17` | Utility-first CSS |
| tailwind-merge | `3.2.0` | Class merging |
| tailwindcss-animate | `1.0.7` | CSS animations |
| class-variance-authority | `0.7.1` | Variant styling |
| clsx | `2.1.1` | Class composition |
| PostCSS | `8.4.49` | CSS processing |
| Autoprefixer | `10.4.20` | CSS vendor prefixes |

### 2.4 Routing & Navigation

| Technology | Version | Purpose |
|------------|---------|---------|
| React Router DOM | `7.5.1` | Client-side routing |

### 2.5 Data & HTTP

| Technology | Version | Purpose |
|------------|---------|---------|
| Axios | `1.8.4` | HTTP client |
| date-fns | `4.1.0` | Date manipulation |
| react-day-picker | `8.10.1` | Date picker component |

### 2.6 Forms & Validation

| Technology | Version | Purpose |
|------------|---------|---------|
| react-hook-form | `7.56.2` | Form state management |
| @hookform/resolvers | `5.0.1` | Validation resolvers |
| Zod | `3.24.4` | Schema validation |

### 2.7 Charts & Visualization

| Technology | Version | Purpose |
|------------|---------|---------|
| Recharts | `3.6.0` | Dashboard charts |

### 2.8 Additional UI Libraries

| Technology | Version | Purpose |
|------------|---------|---------|
| lucide-react | `0.507.0` | Icon library |
| Sonner | `2.0.3` | Toast notifications |
| cmdk | `1.1.1` | Command palette |
| embla-carousel-react | `8.6.0` | Carousel component |
| vaul | `1.1.2` | Drawer component |
| react-resizable-panels | `3.0.1` | Resizable panels |
| input-otp | `1.4.2` | OTP input fields |
| next-themes | `0.4.6` | Theme management |
| react-markdown | `10.1.0` | Markdown rendering |
| html5-qrcode | `2.3.8` | Camera QR scanning |

### 2.9 Development Tools

| Technology | Version | Purpose |
|------------|---------|---------|
| ESLint | `9.23.0` | Code linting |
| eslint-plugin-react | `7.37.4` | React linting rules |
| eslint-plugin-react-hooks | `5.2.0` | Hooks linting rules |
| eslint-plugin-jsx-a11y | `6.10.2` | Accessibility linting |
| eslint-plugin-import | `2.31.0` | Import linting |
| @babel/plugin-proposal-private-property-in-object | `7.21.11` | Babel plugin |

---

## 3. Backend Technologies

### 3.1 Core Framework

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | `3.11.14` | Runtime |
| FastAPI | `0.110.1` | Async API framework |
| Uvicorn | `0.25.0` | ASGI server |
| Starlette | `0.37.2` | ASGI toolkit |

### 3.2 Database

| Technology | Version | Purpose |
|------------|---------|---------|
| MongoDB | `7.0.30` | Document database |
| Motor | `3.3.1` | Async MongoDB driver |
| PyMongo | `4.5.0` | MongoDB client |

### 3.3 Authentication & Security

| Technology | Version | Purpose |
|------------|---------|---------|
| PyJWT | `2.11.0` | JWT token handling |
| bcrypt | `4.1.3` | Password hashing |
| python-jose | `3.5.0` | JOSE implementation |
| passlib | `1.7.4` | Password utilities |
| cryptography | `46.0.4` | Cryptographic operations |

### 3.4 Validation & Serialization

| Technology | Version | Purpose |
|------------|---------|---------|
| Pydantic | `2.12.5` | Data validation |
| pydantic_core | `2.41.5` | Pydantic core engine |
| email-validator | `2.3.0` | Email validation |

### 3.5 AI & LLM Integration

| Technology | Version | Purpose |
|------------|---------|---------|
| emergentintegrations | `0.1.0` | Emergent LLM SDK |
| openai | `1.99.9` | OpenAI API client |
| google-generativeai | `0.8.6` | Google AI client |
| litellm | `1.80.0` | LLM abstraction layer |
| tiktoken | `0.12.0` | Token counting |

### 3.6 HTTP & Networking

| Technology | Version | Purpose |
|------------|---------|---------|
| httpx | `0.28.1` | Async HTTP client |
| requests | `2.32.5` | HTTP library |
| aiohttp | `3.13.3` | Async HTTP |
| urllib3 | `2.6.3` | HTTP utilities |

### 3.7 File Handling

| Technology | Version | Purpose |
|------------|---------|---------|
| aiofiles | `25.1.0` | Async file I/O |
| python-multipart | `0.0.22` | Multipart form data |
| Pillow | `12.1.0` | Image processing |
| qrcode | `8.2` | QR code generation |

### 3.8 Data Processing

| Technology | Version | Purpose |
|------------|---------|---------|
| pandas | `3.0.0` | Data manipulation |
| numpy | `2.4.2` | Numerical computing |
| openpyxl | `3.1.5` | Excel file handling |

### 3.9 API Features

| Technology | Version | Purpose |
|------------|---------|---------|
| slowapi | `0.1.9` | Rate limiting |
| python-dotenv | `1.2.1` | Environment variables |

### 3.10 Cloud & External Services

| Technology | Version | Purpose |
|------------|---------|---------|
| boto3 | `1.42.42` | AWS SDK |
| stripe | `14.3.0` | Payment processing |

### 3.11 Development & Testing

| Technology | Version | Purpose |
|------------|---------|---------|
| pytest | `9.0.2` | Testing framework |
| black | `26.1.0` | Code formatter |
| flake8 | `7.3.0` | Code linting |
| mypy | `1.19.1` | Static type checking |
| isort | `7.0.0` | Import sorting |

### 3.12 Utilities

| Technology | Version | Purpose |
|------------|---------|---------|
| Jinja2 | `3.1.6` | Template engine |
| typer | `0.21.1` | CLI framework |
| rich | `14.3.2` | Terminal formatting |
| PyYAML | `6.0.3` | YAML parsing |
| python-dateutil | `2.9.0.post0` | Date utilities |

---

## 4. Summary Table

| Layer | Primary Technology | Version |
|-------|-------------------|---------|
| Frontend Framework | React | `19.0.0` |
| UI Components | Radix UI | `1.1.4` - `2.2.12` |
| Styling | TailwindCSS | `3.4.17` |
| Charts | Recharts | `3.6.0` |
| Routing | React Router DOM | `7.5.1` |
| HTTP Client | Axios | `1.8.4` |
| Backend Framework | FastAPI | `0.110.1` |
| Database Driver | Motor | `3.3.1` |
| Authentication | PyJWT + bcrypt | `2.11.0` + `4.1.3` |
| Database | MongoDB | `7.0.30` |
| AI Integration | Emergent LLM SDK | `0.1.0` |
| QR Generation | qrcode + Pillow | `8.2` + `12.1.0` |

---

*Document generated: March 2026*
