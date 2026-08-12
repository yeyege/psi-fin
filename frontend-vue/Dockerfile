# ===== WMS 前端（Vue 3）=====
# 阶段一：Node 构建 dist
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
# 修复 Docker overlayfs 下 esbuild postinstall ETXTBSY：改用 optional 平台包二进制
# （官方 ESBUILD_BINARY_PATH 机制跳过 install.js 的「写入后立即执行」校验）
ENV ESBUILD_BINARY_PATH=/app/node_modules/@esbuild/linux-x64/bin/esbuild
# 国内网络使用 npm 镜像（容器内网络不走 Docker daemon 代理）
RUN npm config set registry https://registry.npmmirror.com
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# 阶段二：nginx 托管静态文件
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
