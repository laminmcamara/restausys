import React from "react";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold mb-4">
        Welcome {user}
      </h2>

      <p className="text-gray-600">
        This is your Smart POS dashboard overview.
      </p>
    </div>
  );
}