import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "easyES — AI-Native Company",
  description:
    "Human + AI organization execution platform for roles, agents, workflows, evaluations, and live delivery loops.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" data-theme="dark" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `try{document.documentElement.dataset.theme=localStorage.getItem('easyes.theme')==='light'?'light':'dark'}catch(e){}`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
