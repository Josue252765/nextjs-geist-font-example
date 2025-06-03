"use client";

import React, { ReactNode } from "react";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen bg-white text-black">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="h-16 flex items-center justify-center text-xl font-bold border-b border-gray-700">
          TRADER-X AI
        </div>
        <nav className="flex-1 px-4 py-6 space-y-4">
          <a href="/dashboard" className="block px-3 py-2 rounded hover:bg-gray-700">
            Dashboard
          </a>
          <a href="/bot-operando" className="block px-3 py-2 rounded hover:bg-gray-700">
            Bot Operando
          </a>
          <a href="/grafico-analisis" className="block px-3 py-2 rounded hover:bg-gray-700">
            Gráfico Análisis
          </a>
          <a href="/scalping-lab" className="block px-3 py-2 rounded hover:bg-gray-700">
            Scalping Lab
          </a>
          <a href="/educacion" className="block px-3 py-2 rounded hover:bg-gray-700">
            Educación
          </a>
          <a href="/noticias" className="block px-3 py-2 rounded hover:bg-gray-700">
            Noticias
          </a>
          <a href="/estrategias" className="block px-3 py-2 rounded hover:bg-gray-700">
            Estrategias
          </a>
          <a href="/historial" className="block px-3 py-2 rounded hover:bg-gray-700">
            Historial
          </a>
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="h-16 bg-gray-100 border-b border-gray-300 flex items-center px-6 font-semibold">
          TRADER-X AI Platform
        </header>

        {/* Content area */}
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
