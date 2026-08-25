# ===== WMS 前端（Vue 3）=====
# 阶段一：Node 构建 dist
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
# 修复 Docker overlayfs 下 esbuild postinstall ETXTBSY：改用 optional 平台包二进制
ENV ESBUILD_BINARY_PATH=/app/node_modules/@esbuild/linux-x64/bin/esbuild
# 网络容错：加大超时/重试，使用备用 npm 镜像（npmmirror + 腾讯云镜像二选一）
RUN npm config set registry https://mirrors.cloud.tencent.com/npm/ \
 && npm config set fetch-retries 10 \
 && npm config set fetch-retry-mintimeout 20000 \
 && npm config set fetch-timeout 120000 \
 # npm ci 严格匹配 lockfile，失败时自动 fallback 到 npm install（网络不稳时更鲁棒）
 && (npm ci --no-audit --no-fund || npm install --no-audit --no-fund --legacy-peer-deps)
COPY . .
RUN npm run build

# 阶段二：nginx 托管静态文件
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
