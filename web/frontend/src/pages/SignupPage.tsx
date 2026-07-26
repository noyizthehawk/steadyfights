import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { signup } from "../api";
import { errorMessage } from "../lib/errorMessage";

const inputClass =
  "w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-white " +
  "placeholder-zinc-500 focus:border-red-500 focus:outline-none";

export default function SignupPage(){
     const [email, setEmail] = useState<string>("");
     const [username, setUsername] = useState<string>("");
     const [password, setPassword] = useState<string>("");
     const [error, setError] = useState<string>("");

     const navigate = useNavigate();
    
     const handleSignup = async (e: React.FormEvent) => { // event handler handle signn up
        e.preventDefault(); // stop the browser's default full-page form submit
        setError("");
        // try to signn up
        try {
          await signup(email, username, password); //
          navigate("/login");
        } catch (e: unknown) {
          setError(errorMessage(e));
        }
        
     };
     return (

        <div className="mx-auto flex min-h-[80vh] max-w-sm flex-col justify-center px-4">
          <div className="rounded-2xl bg-zinc-900 p-8 shadow-lg">
            <h2 className="mb-1 text-2xl font-bold text-white">Create your account</h2>
            <p className="mb-6 text-sm text-zinc-400">
              its tiiiiiiiimmmmme!!! signup to start now!
            </p>

            <form onSubmit={handleSignup} className="flex flex-col gap-4">
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
              />
              <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                minLength={3}
                maxLength={20}
                pattern="[A-Za-z0-9_]+"
                title="3–20 characters: letters, numbers, or underscores"
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
                Sign up
              </button>
            </form>

            {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

            <p className="mt-6 text-center text-sm text-zinc-400">
              Already have an account?{" "}
              <Link to="/login" className="text-red-400 hover:underline">
                Log in
              </Link>
            </p>
          </div>
        </div>
     )





}