import type { NextConfig } from 'next';
// @ts-ignore
const withSentryConfig = (config: any, options: any) => config;

let nextConfig: NextConfig = {
  output: (process.env.NEXT_OUTPUT as 'standalone') || undefined,
  webpack: (config) => {
    // Suppress critical dependency warnings
    config.ignoreWarnings = [
      { module: /require-in-the-middle/ },
      { message: /Critical dependency/ },
    ];

    // This rule prevents issues with pdf.js and canvas
    config.externals = [...(config.externals || []), { canvas: 'canvas' }];

    // Ensure node native modules are ignored
    config.resolve.fallback = {
      ...config.resolve.fallback,
      canvas: false,
    };

    return config;
  },
};

/** Removing Sentry for now */
if (false && process.env.NEXT_PUBLIC_VERCEL_ENV === 'production') {
  nextConfig = withSentryConfig(nextConfig, {
    org: 'kortix-ai',
    project: 'suna-nextjs',
    silent: !process.env.CI,
    widenClientFileUpload: true,
    tunnelRoute: '/monitoring',
    disableLogger: true,
    automaticVercelMonitors: true,
  });
}

export default nextConfig;
