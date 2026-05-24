import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ViralCraft",
  description:
    "AI-powered short video structure transfer engine. Learn reusable structure from example videos and apply it to new topics.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
