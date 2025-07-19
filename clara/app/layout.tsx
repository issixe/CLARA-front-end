import type { Metadata } from "next";
import "./globals.css";
import { Agbalumo } from "next/font/google";

const agbalumo = Agbalumo({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-agbalumo",
});

export const metadata: Metadata = {
  title: "CLARA",
  description:
    "An at-home nursing companion that keeps track of all your health needs.",
  icons: {
    icon: "/clara_logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={agbalumo.variable}>
      <body>{children}</body>
    </html>
  );
}
