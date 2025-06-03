"use client";

import React from "react";
import Layout from "../../components/Layout";

export default function Dashboard() {
  return (
    <Layout>
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-100 p-4 rounded shadow">
          <h2 className="text-xl font-semibold mb-2">Métricas Rápidas</h2>
          <p>Resumen de operaciones, ganancias y estado del bot.</p>
        </div>
        <div className="bg-gray-100 p-4 rounded shadow">
          <h2 className="text-xl font-semibold mb-2">Estado del Bot</h2>
          <p>Información en tiempo real del bot operando.</p>
        </div>
        <div className="bg-gray-100 p-4 rounded shadow">
          <h2 className="text-xl font-semibold mb-2">Alertas y Notificaciones</h2>
          <p>Últimas alertas y mensajes importantes.</p>
        </div>
      </div>
    </Layout>
  );
}
