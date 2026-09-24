# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Frontend Dockerfile — React (CRA/craco) built with yarn, served by nginx.
#
# Build-time arg:
#   REACT_APP_BACKEND_URL  — baked into the JS bundle. Leave empty ("") when
#                            the frontend container fronts same-origin via the
#                            bundled nginx reverse proxy (recommended).
# ---------------------------------------------------------------------------

# ----- Stage 1: build static assets ---------------------------------------
FROM node:20.20.2-alpine AS build

WORKDIR /app

# Install deps first for layer caching
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

COPY . .

# Default to empty so the axios client uses relative /api on the same origin.
# Override at build time with:  --build-arg REACT_APP_BACKEND_URL=https://api.example.com
ARG REACT_APP_BACKEND_URL=""
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}
ENV GENERATE_SOURCEMAP=false

RUN yarn build


# ----- Stage 2: nginx runtime ---------------------------------------------
FROM nginx:1.27.5-alpine AS runtime

# Replace the default server with our SPA + /api reverse-proxy config
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O - http://localhost/healthz >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
