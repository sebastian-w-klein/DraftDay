import "./globals.css";
import type { ReactNode } from "react";
import { AppNav } from "@/components/app-nav";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main className="mx-auto max-w-6xl p-6">
          <AppNav />
          {children}
        </main>
      </body>
    </html>
  );
}
