import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 静的エクスポートを有効化
  output: 'export',
  
  // 画像最適化を無効化（static exportでは利用不可）
  images: {
    unoptimized: true
  },
  
  // ベースパスの設定（必要に応じて）
  // basePath: '',
  
  // 末尾スラッシュの設定
  trailingSlash: true,
  
  // 開発時の設定
  ...(process.env.NODE_ENV === 'development' && {
    // 開発時のAPI URLを環境変数で設定可能に
    env: {
      NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
    }
  })
};

export default nextConfig;
