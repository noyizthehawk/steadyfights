import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../api";
import { errorMessage } from "../lib/errorMessage";

const inputClass =
  "w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-white " +
  "placeholder-zinc-500 focus:border-red-500 focus:outline-none";

export default function LoginPage() {
  // Users log in with their username
  const [username, setUsername] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [error, setError] = useState<string>("");

  
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault(); // stop the browser's default full-page form submit
    setError("");
    try {
      await login(username, password); // success sets the http cookie in the backend
      navigate("/"); // ...then send them to the predictor page
    } catch (e: unknown) {
      setError(errorMessage(e));
    }
  };

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-sm flex-col justify-center px-4">
      <div className="rounded-2xl bg-zinc-900 p-8 shadow-lg">
        <h2 className="mb-1 text-2xl font-bold text-white">Welcome back</h2>
        <p className="mb-6 text-sm text-zinc-400">Log in to make your picks.</p>

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className={inputClass}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
          />
          <button
            type="submit"
            className="mt-2 w-full rounded-lg bg-red-600 py-2.5 font-semibold text-white transition hover:bg-red-500"
          >
            Login
          </button>
        </form>

        {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

        <p className="mt-6 text-center text-sm text-zinc-400">
          Don't have an account?{" "}
          <Link to="/signup" className="text-red-400 hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}


