import React from "react";
import { useAuth } from "../hooks/useAuth";

export default function Dashboard() {
  const { user } = useAuth();

  if (!user) {
    return <div className="p-8">Loading...</div>;
  }

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold mb-4">Welcome {user.username}</h2>

      <p className="text-gray-600">
        This is your BEEPOS dashboard overview.
      </p>
    </div>
  );
}
