import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CareerOS",
  description: "The foundation for your professional operating system.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
