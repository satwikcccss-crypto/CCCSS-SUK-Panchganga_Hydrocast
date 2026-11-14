// frontend/app/layout.tsx
import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HydroCast — Shivaji University Kolhapur | Real-Time Flood Forecasting",
  description: "Panchganga Basin real-time flood forecasting and early warning system. A research initiative of the Centre for Climate Change and Sustainability Studies (CCCSS), Shivaji University, Kolhapur.",
  manifest: "/manifest.json",
  icons: { icon: "/favicon.ico", apple: "/icons/icon-192.png" },
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "HydroCast" },
};

export const viewport: Viewport = {
  themeColor: "#0ea5e9",
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />
      </head>
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen">
        {children}
        <script
          dangerouslySetInnerHTML={{
            __html: `if('serviceWorker' in navigator){window.addEventListener('load',()=>{navigator.serviceWorker.register('/sw.js')})}`,
          }}
        />
      </body>
    </html>
  );
}
