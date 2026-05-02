import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Generative Missile Inverse Design",
  description: "Specify target Cd, Cl, Cm, Mach, AoA and generate a physically feasible missile geometry using a conditional GAN.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
